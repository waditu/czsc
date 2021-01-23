# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from typing import List
from .analyze import CZSC
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
        t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" in k])
        t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
        tab.add(t1, "信号表")

        t2 = Table()
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k])
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
            "日线右侧多头因子": Factors.Other.value,
            "日线左侧多头因子": Factors.Other.value,

            "日线右侧空头因子": Factors.Other.value,
            "日线左侧空头因子": Factors.Other.value,

            "30分钟右侧多头因子": Factors.Other.value,
            "30分钟左侧多头因子": Factors.Other.value,

            "30分钟右侧空头因子": Factors.Other.value,
            "30分钟左侧空头因子": Factors.Other.value,

            "5分钟右侧多头因子": Factors.Other.value,
            "5分钟左侧多头因子": Factors.Other.value,

            "5分钟右侧空头因子": Factors.Other.value,
            "5分钟左侧空头因子": Factors.Other.value,
        })

        if "日线" in self.freqs and "30分钟" in self.freqs and "5分钟" in self.freqs:
            if s['日线_第N笔方向'] == Direction.Down.value and s['30分钟_第N笔的七笔形态'] == FdSeven.L3B1.value:
                s['日线右侧多头因子'] = Factors.DLA1.value

            if s['日线_第N笔方向'] == Direction.Down.value and s['日线_第N笔结束标记的分型强弱'] == "强" \
                    and s['5分钟_第N笔的七笔形态'] == FdSeven.L3A1.value:
                s['日线右侧多头因子'] = Factors.DLA2.value

            if "底背弛" in s['日线_第N笔的五笔形态'] and s['5分钟_第N笔的七笔形态'] == FdSeven.L3B1.value:
                s['日线右侧多头因子'] = Factors.DLA3.value

            if "底背弛" in s['日线_第N笔的七笔形态'] and s['5分钟_第N笔的七笔形态'] == FdSeven.L3B1.value:
                s['日线右侧多头因子'] = Factors.DLA4.value

            if s['日线_第N笔方向'] == Direction.Down.value and "底背弛" in s['30分钟_第N笔的五笔形态']:
                s['日线左侧空头因子'] = Factors.DSB1.value

            if s['日线_第N笔方向'] == Direction.Down.value and "底背弛" in s['30分钟_第N笔的七笔形态']:
                s['日线左侧空头因子'] = Factors.DSB2.value

        if "日线" in self.freqs and "5分钟" in self.freqs and "1分钟" in self.freqs:
            if s['1分钟_第N笔的七笔形态'] == FdSeven.L3B1.value and s['日线_第N笔方向'] == Direction.Down.value:
                if s['5分钟_第N笔方向'] == Direction.Down.value:
                    s['5分钟右侧多头因子'] = Factors.F5LA1.value
                if "底背弛" in s['5分钟_第N笔的五笔形态']:
                    s['5分钟右侧多头因子'] = Factors.F5LA2.value
                if "底背弛" in s['5分钟_第N笔的七笔形态']:
                    s['5分钟右侧多头因子'] = Factors.F5LA3.value

            if s['1分钟_第N笔的七笔形态'] == FdSeven.S3B1.value and s['日线_第N笔方向'] == Direction.Up.value:
                if s['5分钟_第N笔方向'] == Direction.Up.value:
                    s['5分钟右侧空头因子'] = Factors.F5SA1.value
                if "顶背弛" in s['5分钟_第N笔的五笔形态']:
                    s['5分钟右侧空头因子'] = Factors.F5SA2.value
                if "顶背弛" in s['5分钟_第N笔的七笔形态']:
                    s['5分钟右侧空头因子'] = Factors.F5SA3.value
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

