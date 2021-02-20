# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
import os
import webbrowser
from typing import List
from .analyze import CZSC, get_sub_bis, get_sub_span
from .utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from .objects import RawBar
from .enum import Factors, Signals, Direction


def check_triple_level(c1: CZSC, c2: CZSC, c3: CZSC):
    """三级别联立笔因子计算

    c1, c2, c3 可能的组合
    1）日线、60分钟、15分钟
    2）日线、30分钟、5分钟
    3）日线、15分钟、1分钟
    4）60分钟、15分钟、1分钟
    5）60分钟、5分钟、1分钟

    :param c1: 本级别 CZSC 对象
    :param c2: 次级别 CZSC 对象
    :param c3: 小级别 CZSC 对象
    :return:
    """
    c_map = {"日线": "C6", "60分钟": "C5", "30分钟": "C4", "15分钟": "C3", "5分钟": "C2", "1分钟": "C1"}
    factor_key_base = "{}{}".format(c_map[c1.freq], c_map[c2.freq])

    v = Factors.Other.value
    c2_h9 = max([x.high for x in c2.bi_list[-9:]])
    c2_l9 = max([x.high for x in c2.bi_list[-9:]])

    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) <= 7:
        factor_l1 = factor_key_base + "L1"  # L1 - 向下笔转折右侧
        if c2.signals['倒1的五笔形态'] == Signals.X5LB0.value:
            if c2_h9 == c2.bi_list[-1].high:
                v = Factors['{}A1'.format(factor_l1)].value
            elif "顶背弛" in c1.signals['倒2的五笔形态'] \
                    and "顶背弛" in c1.signals['倒2的七笔形态'] \
                    and "顶背弛" in c1.signals['倒2的九笔形态']:
                v = Factors['{}A2'.format(factor_l1)].value
            elif "底背弛" in c1.signals['倒1的五笔形态'] \
                    and "底背弛" in c1.signals['倒1的七笔形态'] \
                    and "底背弛" in c1.signals['倒1的九笔形态']:
                v = Factors['{}A3'.format(factor_l1)].value
            else:
                v = Factors['{}A0'.format(factor_l1)].value

        if c1.bi_list[-1].fx_b.power == "强" and c2.signals['倒1的七笔形态'] == Signals.X7LE0.value:
            v = Factors['{}B0'.format(factor_l1)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) > 7:
        factor_l2 = factor_key_base + "L2"
        if "底背弛" in c2.signals['倒1的五笔形态']:
            v = Factors['{}A0'.format(factor_l2)].value

        if "底背弛" in c2.signals['倒1的七笔形态']:
            v = Factors['{}B0'.format(factor_l2)].value

        if "底背弛" in c2.signals['倒1的九笔形态']:
            v = Factors['{}C0'.format(factor_l2)].value
            if c2.signals['倒1的九笔形态'] == Signals.X9LA0.value:
                v = Factors['{}C1'.format(factor_l2)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) <= 7 \
            and min([x.low for x in c1.bars_ubi]) > c1.bi_list[-1].low:
        if c3.signals['倒1的五笔形态'] in [Signals.X5LF0.value, Signals.X5LB0.value]:
            factor_l3 = factor_key_base + "L3"
            if c2.signals['倒1的七笔形态'] == Signals.X7LE0.value:
                v = Factors['{}A0'.format(factor_l3)].value
        else:
            factor_l4 = factor_key_base + "L4"
            if "底背弛" in c2.signals['倒1的七笔形态']:
                v = Factors['{}A0'.format(factor_l4)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) <= 7:
        factor_s1 = factor_key_base + "S1"
        if c2.signals['倒1的五笔形态'] == Signals.X5SB0.value:
            if c2_l9 == c2.bi_list[-1].low:
                v = Factors['{}A1'.format(factor_s1)].value
            elif "底背弛" in c1.signals['倒2的五笔形态'] \
                    and "底背弛" in c1.signals['倒2的七笔形态'] \
                    and "底背弛" in c1.signals['倒2的九笔形态']:
                v = Factors['{}A2'.format(factor_s1)].value
            elif "顶背弛" in c1.signals['倒1的五笔形态'] \
                    and "顶背弛" in c1.signals['倒1的七笔形态'] \
                    and "顶背弛" in c1.signals['倒1的九笔形态']:
                v = Factors['{}A3'.format(factor_s1)].value
            else:
                v = Factors['{}A0'.format(factor_s1)].value

        if c2.signals['倒1的五笔形态'] == Signals.X5SA0.value:
            v = Factors['{}B0'.format(factor_s1)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) > 7:
        factor_s2 = factor_key_base + "S2"
        if "顶背驰" in c2.signals['倒1的七笔形态']:
            v = Factors['{}A0'.format(factor_s2)].value

    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) <= 7 \
            and max([x.high for x in c1.bars_ubi]) < c1.bi_list[-1].high:
        if c3.signals['倒1的五笔形态'] in [Signals.X5SF0.value, Signals.X5SB0.value]:
            factor_s3 = factor_key_base + "S3"
            if c2.signals['倒1的五笔形态'] == Signals.X5SF0.value:
                v = Factors['{}A0'.format(factor_s3)].value
        else:
            factor_s4 = factor_key_base + "S4"
            if "顶背弛" in c3.signals['倒1的五笔形态']:
                v = Factors['{}A0'.format(factor_s4)].value
    return v

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
        self.s = self._calculate_factors_f60()
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

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        home_path = os.path.expanduser("~")
        file_html = os.path.join(home_path, "temp_czsc_factors.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def _calculate_signals(self):
        """计算信号"""
        s = OrderedDict()
        for freq, ks in self.kas.items():
            # s.update(ks.signals)
            s.update({"{}_{}".format(ks.freq, k) if k not in ['symbol', 'dt', 'close'] else k: v
                      for k, v in ks.signals.items()})

        s.update(self.kas['1分钟'].bars_raw[-1].__dict__)
        return s

    def _calculate_factors_d(self):
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

        # 感知日线笔的真实级别，确定 c1, c2, c3
        if len(c6.bars_ubi) > 9:
            direction = Direction.Down if c6.bi_list[-1].direction == Direction.Up else Direction.Up
            bis_c6_c4 = get_sub_span(c4.bi_list[-15:], start_dt=c6.bars_ubi[1].dt,
                                     end_dt=c6.bars_ubi[-1].dt, direction=direction)
        else:
            bis_c6_c4 = get_sub_bis(c4.bi_list[-15:], c6.bi_list[-1])

        if 9 >= len(bis_c6_c4) >= 5:
            c1_, c2_, c3_ = c6, c4, c2
        elif len(bis_c6_c4) > 9:
            c1_, c2_, c3_ = c6, c5, c3
        elif len(bis_c6_c4) < 5:
            c1_, c2_, c3_ = c6, c3, c1
        else:
            raise ValueError

        s.update({"日线笔因子": check_triple_level(c1_, c2_, c3_)})
        return s

    def _calculate_factors_f60(self):
        """计算因子"""
        s = self.s
        s.update({"60分钟笔因子": Factors.Other.value})
        c1: CZSC = self.kas['1分钟']
        c2: CZSC = self.kas['5分钟']
        c3: CZSC = self.kas['15分钟']
        c5: CZSC = self.kas['60分钟']

        if not c5.bi_list:
            print("{} 60分钟笔数量为 0".format(self.symbol))
            return s

        # 感知60分钟笔的真实级别，确定 c1, c2, c3
        if len(c5.bars_ubi) > 9:
            direction = Direction.Down if c5.bi_list[-1].direction == Direction.Up else Direction.Up
            bis_c5_c4 = get_sub_span(c3.bi_list[-15:], start_dt=c5.bars_ubi[1].dt,
                                     end_dt=c5.bars_ubi[-1].dt, direction=direction)
        else:
            bis_c5_c4 = get_sub_bis(c3.bi_list[-15:], c5.bi_list[-1])

        if len(bis_c5_c4) >= 5:
            c1_, c2_, c3_ = c5, c3, c1
        else:
            c1_, c2_, c3_ = c5, c2, c1

        s.update({"60分钟笔因子": check_triple_level(c1_, c2_, c3_)})
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
        self.s = self._calculate_factors_f60()

