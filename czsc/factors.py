# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
import os
import webbrowser
from typing import List
from .utils.ta import MACD, np
from .analyze import CZSC, get_sub_bis, get_sub_span
from .utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from .objects import RawBar
from .enum import Factors, Signals, Direction

def get_trade_factors(name: str,
                      long_open_values: List,
                      long_close_values: List,
                      short_open_values: List = None,
                      short_close_values: List = None) -> dict:
    """获取指定 name 下的交易因子

    :param name: 因子系统的名称
    :param long_open_values: 开多因子值
    :param long_close_values: 平多因子值
    :param short_open_values: 开空因子值
    :param short_close_values: 平空因子值
    :return: 因子交易系统

    example:
    ===================
    >>> factors = get_trade_factors(name="日线笔结束", long_open_values=['BDE'], long_close_values=['BUE'])
    """
    if not short_close_values:
        short_close_values = []

    if not short_open_values:
        short_open_values = []

    long_open_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                         if sum([1 if v in x.name else 0 for v in long_open_values]) > 0]

    long_close_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                          if sum([1 if v in x.name else 0 for v in long_close_values]) > 0]

    short_open_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                          if sum([1 if v in x.name else 0 for v in short_open_values]) > 0]

    short_close_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                           if sum([1 if v in x.name else 0 for v in short_close_values]) > 0]

    factors = {
        "long_open_factors": long_open_factors,
        "long_close_factors": long_close_factors,
        "short_open_factors": short_open_factors,
        "short_close_factors": short_close_factors,
    }
    return factors

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
    if 11 >= len(bis_c6_c4) >= 5:
        c6_sub = c4
    elif len(bis_c6_c4) > 11:
        c6_sub = c5
    else:
        c6_sub = c3

    # 找出60分钟笔对应的次级别
    bis_c5_c3 = get_sub_bis(c3.bi_list[-15:], c5.bi_list[-1])
    if 11 >= len(bis_c5_c3) >= 5:
        c5_sub = c3
    elif len(bis_c5_c3) > 11:
        c5_sub = c4
    else:
        c5_sub = c2

    # 找出30分钟笔对应的次级别
    bis_c4_c2 = get_sub_bis(c2.bi_list[-15:], c4.bi_list[-1])
    if 11 >= len(bis_c4_c2) >= 5:
        c4_sub = c2
    elif len(bis_c5_c3) > 11:
        c4_sub = c3
    else:
        c4_sub = c1

    # 找出15分钟笔对应的次级别
    bis_c3_c2 = get_sub_bis(c2.bi_list[-15:], c3.bi_list[-1])
    if 11 >= len(bis_c3_c2) >= 5:
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


def check_triple_level(c1: CZSC, c2: CZSC, c3: CZSC):
    """三级别联立笔因子计算

    c1, c2, c3 可能组合
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
    v = Factors.Other.value
    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) <= 7:
        factor_l1 = "L1"  # L1 - 向下笔转折右侧
        # L1A
        if c2.signals['倒1五笔'] in [Signals.X5LB0.value] and c2.bi_list[-1].rsq <= 0.8 \
                and c2.signals['倒1近七笔最低点'] == c2.signals['倒1近十一笔最低点']:
            v = Factors['{}A0'.format(factor_l1)].value

        if len(c1.bars_ubi) <= 7 and c1.bi_list[-1].fx_b.power == "强":
            # L1B
            if (c3.signals['倒1七笔'] == Signals.X7LE0.value or c3.signals['倒1五笔'] == Signals.X5LF0.value) \
                    and c3.signals['倒1近七笔最低点'] == c3.signals['倒1近十一笔最低点']:
                v = Factors['{}B0'.format(factor_l1)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) > 7:
        factor_l2 = "L2"
        # L2A
        if "底背弛" in c2.signals['倒1五笔'] or "底背弛" in c2.signals['倒1七笔'] or "底背弛" in c2.signals['倒1九笔']:
            v = Factors['{}A0'.format(factor_l2)].value
            if c3.signals['倒1五笔'] in [Signals.X5LF0.value, Signals.X5LB0.value] \
                    and c3.signals['倒1近七笔最低点'] == c3.signals['倒1近九笔最低点']:
                v = Factors['{}A1'.format(factor_l2)].value
        # L2B
        if c2.signals['倒1九笔'] == Signals.X9LA0.value:
            v = Factors['{}B0'.format(factor_l2)].value
            if c3.signals['倒1五笔'] in [Signals.X5LF0.value, Signals.X5LB0.value] \
                    and c3.signals['倒1近七笔最低点'] == c3.signals['倒1近九笔最低点']:
                v = Factors['{}B1'.format(factor_l2)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) <= 7 \
            and min([x.low for x in c1.bars_ubi]) > c1.bi_list[-1].low:
        factor_l3 = "L3"
        # L3A
        if c3.signals['倒1七笔'] == Signals.X7LE0.value \
                and c3.signals['倒1近七笔最低点'] == c3.signals['倒1近十一笔最低点']:
            v = Factors['{}A0'.format(factor_l3)].value

        # L3B
        if c3.signals['倒1五笔'] == Signals.X5LF0.value \
                and c3.signals['倒1近五笔最低点'] == c3.signals['倒1近九笔最低点']:
            v = Factors['{}B0'.format(factor_l3)].value

        # L3C
        if c2.signals['倒1五笔'] == Signals.X5LF0.value \
                and c2.signals['倒1近七笔最低点'] == c2.signals['倒1近十一笔最低点']:
            v = Factors['{}C0'.format(factor_l3)].value

        factor_l4 = "L4"
        # L4A
        if "底背弛" in c3.signals['倒1五笔'] or "底背弛" in c3.signals['倒1七笔'] or "底背弛" in c3.signals['倒1九笔']:
            v = Factors['{}A0'.format(factor_l4)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Up and len(c1.bars_ubi) <= 7:
        factor_s1 = "S1"
        # S1A
        if c2.signals['倒1五笔'] in [Signals.X5SB0.value] and c2.bi_list[-1].rsq <= 0.8 \
                and c2.signals['倒1近七笔最高点'] == c2.signals['倒1近九笔最高点']:
            if c3.signals['倒1五笔'] in [Signals.X5SF0.value, Signals.X5SB0.value]:
                v = Factors['{}A1'.format(factor_s1)].value
            else:
                v = Factors['{}A0'.format(factor_s1)].value
        # S1B
        if c2.signals['倒1五笔'] == Signals.X5SF0.value \
                and c2.signals['倒1近七笔最高点'] == c2.signals['倒1近九笔最高点']:
            v = Factors['{}B0'.format(factor_s1)].value
            if c3.signals['倒1五笔'] in [Signals.X5SF0.value, Signals.X5SB0.value]:
                v = Factors['{}B1'.format(factor_s1)].value

        if v != Factors.Other.value:
            return v

    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) > 7:
        factor_s2 = "S2"
        # S2A
        if "顶背驰" in c2.signals['倒1九笔'] or "顶背驰" in c2.signals['倒1七笔'] or "顶背驰" in c2.signals['倒1五笔']:
            v = Factors['{}A0'.format(factor_s2)].value
            if c3.signals['倒1五笔'] in [Signals.X5SF0.value, Signals.X5SB0.value]:
                v = Factors['{}A1'.format(factor_s2)].value

    if c1.bi_list[-1].direction == Direction.Down and len(c1.bars_ubi) <= 7 \
            and max([x.high for x in c1.bars_ubi]) < c1.bi_list[-1].high:
        factor_s3 = "S3"
        # S3A
        if c3.signals['倒1七笔'] == Signals.X7SE0.value \
                and c3.signals['倒1近七笔最高点'] == c3.signals['倒1近九笔最高点']:
            v = Factors['{}B0'.format(factor_s3)].value

        # S3B
        if c3.signals['倒1五笔'] == Signals.X5SF0.value \
                and c3.signals['倒1近七笔最高点'] == c3.signals['倒1近九笔最高点']:
            v = Factors['{}B0'.format(factor_s3)].value

        factor_s4 = "S4"
        # S4A
        if "顶背驰" in c3.signals['倒1九笔'] or "顶背驰" in c3.signals['倒1七笔'] or "顶背驰" in c3.signals['倒1五笔']:
            v = Factors['{}A0'.format(factor_s4)].value
    return v


def check_bi_end(c1: CZSC, c2: CZSC):
    """两级别联立笔结束因子（右侧判断）计算

    :param c1: 本级别
    :param c2: 次级别
    :return:
    """
    v = Factors.Other.value

    c1_dir = c1.bi_list[-1].direction if c1.bi_list else None
    c2_dir = c2.bi_list[-1].direction if c2.bi_list else None

    def __c2_macd():
        close = np.array([x.close for x in c2.bars_raw[-400:]], dtype=np.double)
        return MACD(close)

    if c1_dir == c2_dir == Direction.Up and c2.bi_list[-1].high < c1.bi_list[-1].high:
        diff, dea, macd = __c2_macd()
        if (diff[-1] < 0 and dea[-1] < 0 and macd[-1] < macd[-2]) and len(c2.bars_ubi) <= 5:
            v = Factors.BUE1.value
        elif c2.signals['倒1五笔'] in [Signals.X5SB0.value, Signals.X5SF0.value]:
            v = Factors.BUE2.value
        elif c2.signals['倒1七笔'] in [Signals.X7SE0.value, Signals.X7SF0.value]:
            v = Factors.BUE3.value
        else:
            v = Factors.BUE0.value

    if c1_dir == c2_dir == Direction.Down and c2.bi_list[-1].low > c1.bi_list[-1].low:
        diff, dea, macd = __c2_macd()
        if (diff[-1] > 0 and dea[-1] > 0 and macd[-1] > macd[-2]) and len(c2.bars_ubi) <= 5:
            v = Factors.BDE1.value
        elif c2.signals['倒1五笔'] in [Signals.X5LB0.value, Signals.X5LF0.value]:
            v = Factors.BDE2.value
        elif c2.signals['倒1七笔'] in [Signals.X7LE0.value, Signals.X7LF0.value]:
            v = Factors.BDE3.value
        else:
            v = Factors.BDE0.value

    return v

# ----------------------------------------------------------------------------------------------------------------------

class CzscFactors:
    """缠中说禅技术分析理论之多级别联立因子"""
    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min]):
        """

        :param kg: 基于tick或1分钟的K线合成器
        """
        self.kg = kg
        self.freqs = kg.freqs
        klines = self.kg.get_klines({k: 3000 for k in self.freqs})
        self.kas = {k: CZSC(klines[k], freq=k, max_bi_count=30) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self.__cal_signals()
        self.calculate_factors()
        self.cache = OrderedDict()

    def __repr__(self):
        return "<CzscFactors for {}>".format(self.symbol)

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
        t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items()
                              if "_" in k and isinstance(v, str)
                              and v not in ["Other~其他", "向下", 'Y~是', 'N~否', '向上']])
        t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
        tab.add(t1, "信号表")

        t2 = Table()
        ths_ = [["同花顺F10",  "http://basic.10jqka.com.cn/{}".format(self.symbol[:6])]]
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k and v != "Other~其他"] + ths_)
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

    def __cal_signals(self):
        """计算信号"""
        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update({"{}_{}".format(ks.freq, k) if k not in ['symbol', 'dt', 'close'] else k: v
                      for k, v in ks.signals.items()})

        s.update(self.kas['1分钟'].bars_raw[-1].__dict__)
        return s

    def __aware_level_pairs(self):
        c1: CZSC = self.kas['1分钟']
        c2: CZSC = self.kas['5分钟']
        c3: CZSC = self.kas['15分钟']
        c4: CZSC = self.kas['30分钟']
        c5: CZSC = self.kas['60分钟']
        c6: CZSC = self.kas['日线']
        self.level_pairs = aware_level_pairs(c6, c5, c4, c3, c2, c1)

    def __cal_factors_d(self):
        """计算日线笔因子"""
        s = self.s
        c1: CZSC = self.kas['日线']

        if not c1.bi_list:
            print("{} 日线笔数量为 0".format(self.symbol))
            return s

        c2 = self.kas[self.level_pairs[c1.freq]]
        c3 = self.kas[self.level_pairs[c2.freq]]
        s.update({
            "日线笔因子": check_triple_level(c1, c2, c3),
            "日线笔结束": check_bi_end(c1, c2),
        })
        return s

    def __cal_factors_f60(self):
        """计算60分钟笔因子"""
        s = self.s
        c1: CZSC = self.kas['60分钟']

        if not c1.bi_list:
            print("{} 60分钟笔数量为 0".format(self.symbol))
            return s

        c2 = self.kas[self.level_pairs[c1.freq]]
        c3 = self.kas[self.level_pairs[c2.freq]]
        s.update({
            "60分钟笔因子": check_triple_level(c1, c2, c3),
            "60分钟笔结束": check_bi_end(c1, c2),
        })
        return s

    def __cal_factors_f30(self):
        s = self.s
        c1: CZSC = self.kas['30分钟']

        if not c1.bi_list:
            print("{} 30分钟笔数量为 0".format(self.symbol))
            return s

        c2 = self.kas[self.level_pairs[c1.freq]]
        c3 = self.kas[self.level_pairs[c2.freq]]
        s.update({
            "30分钟笔因子": check_triple_level(c1, c2, c3),
            "30分钟笔结束": check_bi_end(c1, c2),
        })
        return s

    def __cal_factors_f15(self):
        s = self.s
        c1: CZSC = self.kas['15分钟']

        if not c1.bi_list:
            print("{} 15分钟笔数量为 0".format(self.symbol))
            return s

        c2 = self.kas[self.level_pairs[c1.freq]]
        c3 = self.kas[self.level_pairs[c2.freq]]
        s.update({
            "15分钟笔因子": check_triple_level(c1, c2, c3),
            "15分钟笔结束": check_bi_end(c1, c2),
        })
        return s

    def __cal_factors_f5(self):
        s = self.s
        c1: CZSC = self.kas['5分钟']

        if not c1.bi_list:
            print("{} 5分钟笔数量为 0".format(self.symbol))
            return s

        c2 = self.kas[self.level_pairs[c1.freq]]
        s.update({
            "5分钟笔结束": check_bi_end(c1, c2),
        })
        return s

    def calculate_factors(self):
        """在这里定义因子计算的顺序，同时也可以根据需要，仅计算自己感兴趣的因子"""
        self.__aware_level_pairs()
        self.s = self.__cal_factors_d()
        self.s = self.__cal_factors_f60()
        self.s = self.__cal_factors_f30()
        self.s = self.__cal_factors_f15()
        self.s = self.__cal_factors_f5()

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
        self.s = self.__cal_signals()
        self.calculate_factors()



