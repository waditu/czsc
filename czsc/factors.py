# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from typing import List
from .analyze import CZSC, get_sub_bis, get_sub_span, check_seven_fd, check_nine_fd, check_five_fd, check_fx
from .utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from .objects import RawBar
from .enum import Factors, Signals, Direction


class CzscFactors:
    """缠中说禅技术分析理论之多级别联立因子"""
    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min]):
        """

        :param kg: 基于tick或1分钟的K线合成器
        """
        self.kg = kg
        self.freqs = kg.freqs
        klines = self.kg.get_klines({k: 3000 for k in self.freqs})
        self.kas = {k: CZSC(klines[k], freq=k, max_bi_count=20) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._calculate_signals()
        self.s = self._calculate_factors_d()
        self.s = self._calculate_factors_f30()
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
        t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" in k and "~" in str(v)])
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

    def _calculate_factors_d(self):
        """计算因子"""
        s = self.s
        s.update({"日线笔因子": Factors.Other.value})
        c1: CZSC = self.kas['1分钟']
        c2: CZSC = self.kas['5分钟']
        c3: CZSC = self.kas['15分钟']
        c4: CZSC = self.kas['30分钟']
        c5: CZSC = self.kas['60分钟']
        c6: CZSC = self.kas['日线']

        if not c6.bi_list:
            print("{} 日线笔数量为 0".format(self.symbol))
            return s

        # 日线向下笔转折右侧 DLA
        if c6.bi_list[-1].direction == Direction.Down:
            if c6.bi_list[-1].fx_b.power == "强" and s['5分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                s['日线笔因子'] = Factors.DLA1.value

            bis_d_f30 = get_sub_bis(c4.bi_list[-15:], c6.bi_list[-1])

            if 5 <= len(bis_d_f30) <= 11:
                f30_h9 = max([x.high for x in c4.bi_list[-9:]])
                # f30_l9 = min([x.low for x in c4.bi_list[-9:]])

                if s['30分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                    s['日线笔因子'] = Factors.DLA2.value
                    if f30_h9 == c4.bi_list[-1].high:
                        s['日线笔因子'] = Factors.DLA2a.value

            elif len(bis_d_f30) > 11:
                bis_d_f60 = get_sub_bis(c5.bi_list[-15:], c6.bi_list[-1])
                f60_h9 = max([x.high for x in c5.bi_list[-9:]])
                # f60_l9 = min([x.low for x in c5.bi_list[-9:]])

                if 11 >= len(bis_d_f60) >= 5:
                    if s['60分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                        s['日线笔因子'] = Factors.DLA5.value
                        if f60_h9 == c5.bi_list[-1].high:
                            s['日线笔因子'] = Factors.DLA5a.value

            elif len(bis_d_f30) < 5:
                bis_d_f15 = get_sub_bis(c3.bi_list[-15:], c6.bi_list[-1])
                f15_h9 = max([x.high for x in c3.bi_list[-9:]])
                # f15_l9 = min([x.low for x in c3.bi_list[-9:]])

                if 11 >= len(bis_d_f15) >= 5:
                    if s['15分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                        s['日线笔因子'] = Factors.DLA3.value
                        if f15_h9 == c3.bi_list[-1].high:
                            s['日线笔因子'] = Factors.DLA5a.value

                    if s['15分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                        s['日线笔因子'] = Factors.DLA4.value

        # 日线向下笔转折左侧因子 DLB
        if c6.bi_list[-1].direction == Direction.Up and len(c6.bars_ubi) > 7:
            bis_d_f30 = get_sub_span(c4.bi_list[-15:], start_dt=c6.bars_ubi[1].dt,
                                     end_dt=c6.bars_ubi[-1].dt, direction=Direction.Down)
            if 11 >= len(bis_d_f30) >= 5:
                if "底背弛" in s['30分钟_倒1的五笔形态']:
                    s['日线笔因子'] = Factors.DLB1.value

                if "底背弛" in s['30分钟_倒1的七笔形态']:
                    s['日线笔因子'] = Factors.DLB2.value

                if "底背弛" in s['30分钟_倒1的九笔形态']:
                    s['日线笔因子'] = Factors.DLB3.value
                    if s['30分钟_倒1的九笔形态'] == Signals.X9LA0.value:
                        s['日线笔因子'] = Factors.DLB3a.value

            elif len(bis_d_f30) > 11:
                bis_d_f60 = get_sub_span(c5.bi_list[-15:], start_dt=c6.bars_ubi[1].dt,
                                         end_dt=c6.bars_ubi[-1].dt, direction=Direction.Down)
                if 11 >= len(bis_d_f60) >= 5:
                    if "底背弛" in s['60分钟_倒1的五笔形态']:
                        s['日线笔因子'] = Factors.DLB4.value

                    if "底背弛" in s['60分钟_倒1的七笔形态']:
                        s['日线笔因子'] = Factors.DLB5.value

                    if "底背弛" in s['60分钟_倒1的九笔形态']:
                        s['日线笔因子'] = Factors.DLB6.value
                        if s['60分钟_倒1的九笔形态'] == Signals.X9LA0.value:
                            s['日线笔因子'] = Factors.DLB6a.value

            elif len(bis_d_f30) < 5:
                bis_d_f15 = get_sub_span(c3.bi_list[-15:], start_dt=c6.bars_ubi[1].dt,
                                         end_dt=c6.bars_ubi[-1].dt, direction=Direction.Down)
                if 11 >= len(bis_d_f15) >= 5:
                    if "底背弛" in s['15分钟_倒1的五笔形态']:
                        s['日线笔因子'] = Factors.DLB7.value

                    if "底背弛" in s['15分钟_倒1的七笔形态']:
                        s['日线笔因子'] = Factors.DLB8.value

                    if "底背弛" in s['15分钟_倒1的九笔形态']:
                        s['日线笔因子'] = Factors.DLB9.value
                        if s['15分钟_倒1的九笔形态'] == Signals.X9LA0.value:
                            s['日线笔因子'] = Factors.DLB9a.value

        if c6.bi_list[-1].direction == Direction.Up and len(c6.bars_ubi) <= 7 \
                and c6.bars_ubi[-1].low > c6.bi_list[-1].low:
            # 日线向上笔中继右侧 DLC
            if s['5分钟_倒1的五笔形态'] in [Signals.X5LF0.value, Signals.X5LB0.value]:
                if s['5分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                    s['日线笔因子'] = Factors.DLC1.value

            # 日线向上笔中继左侧 DLD
            else:
                if "底背弛" in s['30分钟_倒1的五笔形态']:
                    s['日线笔因子'] = Factors.DLD1.value

        # 日线向上笔转折右侧因子 DSA
        if c6.bi_list[-1].direction == Direction.Up:
            bis_d_f30 = get_sub_bis(c4.bi_list[-15:], c6.bi_list[-1])
            if len(bis_d_f30) <= 9 and s['30分钟_倒1的五笔形态'] == Signals.X5SB0.value:
                s['日线笔因子'] = Factors.DSA1.value

        # 日线向上笔转折左侧因子 DSB
        if c6.bi_list[-1].direction == Direction.Down and len(c6.bars_ubi) > 7:
            if "顶背驰" in s['30分钟_倒1的七笔形态']:
                s['日线笔因子'] = Factors.DSB1.value

        if c6.bi_list[-1].direction == Direction.Down and len(c6.bars_ubi) <= 7 \
                and c6.bars_ubi[-1].high < c6.bi_list[-1].high:
            # 日线向下笔中继右侧因子 DSC
            if s['5分钟_倒1的五笔形态'] in [Signals.X5SF0.value, Signals.X5SB0.value]:
                if s['30分钟_倒1的五笔形态'] == Signals.X5SF0.value:
                    s['日线笔因子'] = Factors.DSC1.value

            # 日线向下笔中继左侧因子 DSD
            else:
                if "顶背弛" in s['30分钟_倒1的五笔形态']:
                    s['日线笔因子'] = Factors.DSD1.value
        return s

    def _calculate_factors_f30(self):
        """计算因子"""
        s = self.s
        s.update({"30分钟笔因子": Factors.Other.value})
        c1: CZSC = self.kas['1分钟']
        c2: CZSC = self.kas['5分钟']
        c3: CZSC = self.kas['15分钟']
        c4: CZSC = self.kas['30分钟']

        if not c4.bi_list:
            print("{} 30分钟笔数量为 0".format(self.symbol))
            return s

        # 30分钟向下笔转折右侧因子
        if c4.bi_list[-1].direction == Direction.Down:
            bis_f30_f5 = get_sub_bis(c2.bi_list, c4.bi_list[-1])

            if 9 >= len(bis_f30_f5) >= 5:
                if s['5分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                    s['30分钟笔因子'] = Factors.F30LA1.value

                if s['5分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                    s['30分钟笔因子'] = Factors.F30LA4.value

            elif len(bis_f30_f5) > 9:
                bis_f30_f15 = get_sub_bis(c3.bi_list, c4.bi_list[-1])
                if 5 <= len(bis_f30_f15) <= 9:
                    if s['15分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                        s['30分钟笔因子'] = Factors.F30LA2.value

                    if s['15分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                        s['30分钟笔因子'] = Factors.F30LA5.value

            elif len(bis_f30_f5) < 5:
                bis_f30_f1 = get_sub_bis(c1.bi_list, c4.bi_list[-1])
                if 5 <= len(bis_f30_f1) <= 9:
                    if s['1分钟_倒1的七笔形态'] == Signals.X7LE0.value:
                        s['30分钟笔因子'] = Factors.F30LA3.value

                    if s['1分钟_倒1的五笔形态'] == Signals.X5LB0.value:
                        s['30分钟笔因子'] = Factors.F30LA6.value

        # 30分钟向下笔转折左侧因子
        if c4.bi_list[-1].direction == Direction.Up and len(c4.bars_ubi) > 7:
            bis_f5_f1 = get_sub_bis(c1.bi_list, c2.bi_list[-1])
            if "底背弛" in s['5分钟_倒1的七笔形态'] and 9 >= len(bis_f5_f1) >= 3:
                s['30分钟笔因子'] = Factors.F30LB1.value

        # 30分钟向上笔中继
        if c4.bi_list[-1].direction == Direction.Up and len(c4.bars_ubi) <= 7:
            pass

        # 30分钟向上笔转折右侧
        if c4.bi_list[-1].direction == Direction.Up:
            pass

        # 30分钟向上笔转折左侧
        if c4.bi_list[-1].direction == Direction.Down and len(c4.bars_ubi) > 7:
            pass

        # 30分钟向下笔中继
        if c4.bi_list[-1].direction == Direction.Up and len(c4.bars_ubi) > 7:
            pass

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
        self.s = self._calculate_signals()
        self.s = self._calculate_factors_d()
        self.s = self._calculate_factors_f30()

