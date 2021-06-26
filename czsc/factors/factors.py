import os
import webbrowser
from typing import Set, List, Tuple
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from ..analyze import CZSC
from ..utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from ..objects import RawBar
from .bi123 import future_bi123_f15, share_bi123_f15
from .bi_end import future_bi_end_f30, share_bi_end_f30
from .third_buy import future_third_buy_f5, share_third_buy_f15


factors_func = {
    future_bi123_f15, share_bi123_f15,

    future_bi_end_f30, share_bi_end_f30,

    future_third_buy_f5, share_third_buy_f15
}

factors_all = {f.__doc__: f for f in factors_func}

class CzscFactors:
    """缠中说禅技术分析理论之多级别联立因子"""
    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min], factors: [Set, List, Tuple] = None):
        """

        :param kg: 基于tick或1分钟的K线合成器
        """
        self.name = "CzscFactors"
        self.kg = kg
        self.freqs = kg.freqs
        self.factors = factors

        klines = self.kg.get_klines({k: 3000 for k in self.freqs})
        self.kas = {k: CZSC(klines[k], freq=k, max_bi_count=50) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._cal_signals()
        self.calculate_factors()
        self.cache = OrderedDict()

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

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

        for freq in self.freqs:
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if k.startswith("{}_".format(freq))])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, "{}信号表".format(freq))

        t2 = Table()
        ths_ = [["同花顺F10",  "http://basic.10jqka.com.cn/{}".format(self.symbol[:6])]]
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k] + ths_)
        t2.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅因子表", subtitle=""))
        tab.add(t2, "因子表")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        home_path = os.path.expanduser("~")
        file_html = os.path.join(home_path, "temp_czsc_factors.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def _cal_signals(self):
        """计算信号"""
        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update({"{}_{}".format(ks.freq, k) if k not in ['symbol', 'dt', 'close'] else k: v
                      for k, v in ks.signals.items()})

        s.update(self.kas['1分钟'].bars_raw[-1].__dict__)
        return s

    def calculate_factors(self):
        """在这里定义因子计算的顺序，同时也可以根据需要，仅计算自己感兴趣的因子"""
        self.s.update({"级别列表": self.kg.freqs})
        if self.factors:
            for func in self.factors:
                self.s.update({func.__doc__: func(self.s)})

    def update_factors(self, k: RawBar):
        """更新多级别联立因子"""
        self.kg.update(k)
        klines_one = self.kg.get_klines({freq: 1 for freq in self.freqs})

        for freq, klines_ in klines_one.items():
            self.kas[freq].update(klines_[-1])

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._cal_signals()
        self.calculate_factors()
