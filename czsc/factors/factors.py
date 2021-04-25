import os
import webbrowser
from typing import Set, List, Tuple
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from ..analyze import CZSC, get_sub_bis
from ..utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from ..objects import RawBar
from ..enum import Factors
from .bi123 import future_bi123_f15, share_bi123_f15
from .bi_end import future_bi_end_f30, share_bi_end_f60
from .third_buy import future_third_buy_f5, share_third_buy_f5, share_third_buy_f15


def share_base(s):
    """股票基准"""
    return Factors.L1A0.value

def future_base(s):
    """期货基准"""
    return Factors.L1A0.value


factors_func = {
    share_base, future_base,

    future_bi123_f15, share_bi123_f15,

    future_bi_end_f30, share_bi_end_f60,

    future_third_buy_f5, share_third_buy_f5, share_third_buy_f15
}

factors_all = {f.__doc__: f for f in factors_func}

def aware_level_pairs(c6: CZSC, c5: CZSC, c4: CZSC, c3: CZSC, c2: CZSC, c1: CZSC):
    """感知级别配对情况

    :param c6: 日线 CZSC 对象
    :param c5: 60分钟 CZSC 对象
    :param c4: 30分钟 CZSC 对象
    :param c3: 15分钟 CZSC 对象
    :param c2: 5分钟 CZSC 对象
    :param c1: 1分钟 CZSC 对象
    :return:
    """
    # 找出日线笔对应的次级别
    bis_c6_c4 = get_sub_bis(c4.bi_list[-15:], c6.bi_list[-1])
    if 11 >= len(bis_c6_c4) >= 3:
        c6_sub = c4
    elif len(bis_c6_c4) > 11:
        c6_sub = c5
    else:
        c6_sub = c3

    # 找出60分钟笔对应的次级别
    bis_c5_c3 = get_sub_bis(c3.bi_list[-15:], c5.bi_list[-1])
    if 11 >= len(bis_c5_c3) >= 3:
        c5_sub = c3
    elif len(bis_c5_c3) > 11:
        c5_sub = c4
    else:
        c5_sub = c2

    # 找出30分钟笔对应的次级别
    bis_c4_c2 = get_sub_bis(c2.bi_list[-15:], c4.bi_list[-1])
    if 11 >= len(bis_c4_c2) >= 3:
        c4_sub = c2
    elif len(bis_c4_c2) > 11:
        c4_sub = c3
    else:
        c4_sub = c1

    # 找出15分钟笔对应的次级别
    bis_c3_c2 = get_sub_bis(c2.bi_list[-15:], c3.bi_list[-1])
    if 11 >= len(bis_c3_c2) >= 3:
        c3_sub = c2
    else:
        c3_sub = c1

    pairs = {
        c6.freq: c6_sub.freq,
        c5.freq: c5_sub.freq,
        c4.freq: c4_sub.freq,
        c3.freq: c3_sub.freq,
        c2.freq: c1.freq,
        c1.freq: c1.freq,
    }
    return pairs


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
        self.kas = {k: CZSC(klines[k], freq=k, max_bi_count=30) for k in klines.keys()}
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

        t3 = Table()
        t3.add(["本级别", "次级别"], [[k, v] for k, v in eval(self.s['级别映射']).items()])
        t3.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅级别映射表", subtitle=""))
        tab.add(t3, "级别映射表")

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
        c1: CZSC = self.kas['1分钟']
        c2: CZSC = self.kas['5分钟']
        c3: CZSC = self.kas['15分钟']
        c4: CZSC = self.kas['30分钟']
        c5: CZSC = self.kas['60分钟']
        c6: CZSC = self.kas['日线']
        level_pairs = aware_level_pairs(c6, c5, c4, c3, c2, c1)
        self.s.update({"级别列表": self.kg.freqs, "级别映射": str(level_pairs)})
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
