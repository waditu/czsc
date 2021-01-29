# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from typing import List
from .analyze import CZSC, get_sub_span, check_seven_fd, check_nine_fd, check_five_fd
from .utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from .objects import RawBar
from .enum import Factors, FdNine, FdFive, FdSeven, FdThree, Direction


class CzscFactors:
    """缠中说禅技术分析理论之多级别联立因子"""
    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min], max_count: int = 1000):
        """

        :param kg: 基于tick或1分钟的K线合成器
        :param max_count: 单个级别最大K线数量
        """
        assert max_count >= 1000, "为了保证因子能够顺利计算，max_count 不允许设置小于1000"
        self.kg = kg
        self.freqs = kg.freqs
        klines = self.kg.get_klines({k: max_count for k in self.freqs})
        self.kas = {k: CZSC(klines[k], freq=k, max_count=max_count) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._calculate_factors()
        self.cache = OrderedDict()

    def take_snapshot(self, file_html=None, width="1400px", height="580px"):
        """获取快照

        :param file_html: str
            交易快照保存的 html 文件名
        :param width: str
            图表宽度
        :param height: str
            图表高度
        :return:
        """
        tab = Tab(page_title="{}@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = self.kas[freq].to_echarts(width, height)
            tab.add(chart, freq)

        t1 = Table()
        t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" in k and v != "其他"])
        t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
        tab.add(t1, "信号表")

        t2 = Table()
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k and v != "其他"])
        t2.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅因子表", subtitle=""))
        tab.add(t2, "因子表")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def _calculate_signals(self):
        """计算信号"""
        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update(ks.get_signals())

        s.update(self.kas['1分钟'].bars_raw[-1].__dict__)
        return s

    def _calculate_factors(self):
        """计算因子"""
        s = self._calculate_signals()

        s.update({
            "5分钟右侧多头因子": Factors.Other.value,
            "5分钟左侧多头因子": Factors.Other.value,

            "5分钟右侧空头因子": Factors.Other.value,
            "5分钟左侧空头因子": Factors.Other.value,

            "30分钟右侧多头因子": Factors.Other.value,
            "30分钟左侧多头因子": Factors.Other.value,

            "30分钟右侧空头因子": Factors.Other.value,
            "30分钟左侧空头因子": Factors.Other.value,

            "日线右侧多头因子": Factors.Other.value,
            "日线左侧多头因子": Factors.Other.value,

            "日线右侧空头因子": Factors.Other.value,
            "日线左侧空头因子": Factors.Other.value,
        })

        five_left_short = [FdFive.S2A1.value, FdFive.S2B1.value, FdFive.S2C1.value, FdFive.S3A1.value]
        five_left_long = [FdFive.L2A1.value, FdFive.L2B1.value, FdFive.L2C1.value, FdFive.L3A1.value]
        five_third_buy = [FdFive.L4A1.value, FdFive.L4A2.value, FdFive.L4B1.value, FdFive.L4B2.value,
                          FdFive.L4C1.value, FdFive.L4C2.value, FdFive.L4D1.value, FdFive.L4D2.value]

        seven_left_short = [FdSeven.S1A1.value, FdSeven.S2A1.value,  FdSeven.S4A1.value]
        seven_left_long = [FdSeven.L1A1.value, FdSeven.L2A1.value,  FdSeven.L4A1.value]

        if "5分钟" in self.freqs and "1分钟" in self.freqs:
            if s['5分钟_第N笔方向'] == Direction.Down.value:
                # 5分钟左侧空头因子
                if s['1分钟_第N笔的七笔形态'] in seven_left_short:
                    s['5分钟左侧空头因子'] = Factors.F5SB1.value

                if s['1分钟_第N笔的五笔形态'] in five_left_short:
                    s['5分钟左侧空头因子'] = Factors.F5SB2.value

                # 5分钟右侧多头因子
                if s['1分钟_第N笔的七笔形态'] == FdSeven.L3B1.value:
                    s['5分钟右侧多头因子'] = Factors.F5LA1.value

            elif s['5分钟_第N笔方向'] == Direction.Up.value:
                # 5分钟左侧多头因子
                if s['1分钟_第N笔的七笔形态'] in seven_left_long:
                    s['5分钟左侧多头因子'] = Factors.F5LB1.value

                if s['1分钟_第N笔的五笔形态'] in five_left_long:
                    s['5分钟左侧多头因子'] = Factors.F5LB2.value

                # 5分钟右侧空头因子
                if s['1分钟_第N笔的七笔形态'] == FdSeven.S3B1.value:
                    s['5分钟右侧空头因子'] = Factors.F5SA1.value

        # ==============================================================================================================
        if "日线" in self.freqs and "30分钟" in self.freqs and "5分钟" in self.freqs:
            c1 = self.kas['5分钟']
            c2 = self.kas['30分钟']
            c3 = self.kas['日线']
            if c2.bi_list and c3.bi_list:
                bi1 = c3.bi_list[-1]
                bi2 = c2.bi_list[-1]
                sub1 = get_sub_span(c2.bi_list, bi1.fx_a.dt, bi1.fx_b.dt, bi1.direction)
                sub2 = get_sub_span(c1.bi_list, bi2.fx_a.dt, bi2.fx_b.dt, bi2.direction)
                # print("sub1 len: {}; sub2 len: {}".format(len(sub1), len(sub2)))
            else:
                sub1 = sub2 = []

            if s['日线_第N笔方向'] == Direction.Down.value:

                if s['30分钟_第N笔的七笔形态'] == FdSeven.L3B1.value:
                    s['日线右侧多头因子'] = Factors.DLA1.value

                if c3.bi_list[-1].fx_b.power == "强" and s['5分钟_第N笔的七笔形态'] == FdSeven.L3A1.value:
                    s['日线右侧多头因子'] = Factors.DLA2.value

                if len(sub1) == 7 and check_seven_fd(sub1) in seven_left_long and len(sub2) >= 3:
                    s['日线右侧多头因子'] = Factors.DLA3.value

                if len(sub1) == 5 and check_five_fd(sub1) in five_left_long and len(sub2) >= 3:
                    s['日线右侧多头因子'] = Factors.DLA4.value

                if len(c3.bars_ubi) <= 7 and s['30分钟_第N笔的五笔形态'] in five_third_buy and len(sub2) >= 3 \
                        and c2.bi_list[-1].high == max([x.high for x in c2.bi_list[-9:]]):
                    s['日线右侧多头因子'] = Factors.DLA5.value

            if s['日线_第N笔方向'] == Direction.Down.value:

                if s['30分钟_第N笔的五笔形态'] in five_left_short:
                    s['日线左侧空头因子'] = Factors.DSB1.value

                if s['30分钟_第N笔的七笔形态'] in seven_left_short:
                    s['日线左侧空头因子'] = Factors.DSB2.value

        return s

    def update_factors(self, data: List[RawBar]):
        """更新多级别联立因子"""
        for row in data:
            self.kg.update(row)

        klines_one = self.kg.get_klines({k: 1 for k in self.freqs})

        for freq, klines_ in klines_one.items():
            k = klines_[-1]
            self.kas[freq].update(k)

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._calculate_factors()

