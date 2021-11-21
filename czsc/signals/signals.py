# coding: utf-8
import numpy as np
from collections import OrderedDict

from czsc import analyze
from ..objects import Direction, Signal
from ..enum import Freq
from ..utils.ta import MACD, SMA
from ..signals.utils import kdj_gold_cross
from .bxt import get_s_like_bs, get_s_d0_bi, get_s_bi_status, get_s_di_bi, get_s_base_xt, get_s_three_bi
from .ta import get_s_single_k, get_s_three_k, get_s_sma, get_s_macd, get_s_bar_end


def get_default_signals(c: analyze.CZSC) -> OrderedDict:
    """在 CZSC 对象上计算信号，这个是标准函数，主要用于研究。

    实盘时可以按照自己的需要自定义计算哪些信号。

    :param c: CZSC 对象
    :return: 信号字典
    """
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})

    s.update(get_s_d0_bi(c))
    s.update(get_s_three_k(c, 1))
    s.update(get_s_di_bi(c, 1))
    s.update(get_s_macd(c, 1))
    s.update(get_s_single_k(c, 1))
    s.update(get_s_bi_status(c))

    for di in range(1, 8):
        s.update(get_s_three_bi(c, di))

    for di in range(1, 8):
        s.update(get_s_base_xt(c, di))

    for di in range(1, 8):
        s.update(get_s_like_bs(c, di))
    return s


def get_selector_signals(c: analyze.CZSC) -> OrderedDict:
    """在 CZSC 对象上计算选股信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    freq: Freq = c.freq
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})

    s.update(get_s_three_k(c, 1))
    s.update(get_s_bi_status(c))

    for di in range(1, 3):
        s.update(get_s_three_bi(c, di))

    for di in range(1, 3):
        s.update(get_s_base_xt(c, di))

    for di in range(1, 3):
        s.update(get_s_like_bs(c, di))

    default_signals = [
        # 以下是技术指标相关信号
        Signal(k1=str(freq.value), k2="成交量", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="MA5状态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="KDJ状态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="MACD状态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="潜在三买", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    if not c.bi_list:
        return s

    if len(c.bars_raw) > 30 and c.freq == Freq.D:
        last_vols = [k_.open * k_.vol for k_ in c.bars_raw[-10:]]
        if sum(last_vols) > 15e8 and min(last_vols) > 1e7:
            v = Signal(k1=str(freq.value), k2="成交量", v1="近10个交易日累计成交金额大于15亿", v2='近10个交易日最低成交额大于1亿')
            s[v.key] = v.value

    if len(c.bars_raw) > 30 and c.freq in [Freq.W, Freq.M]:
        if kdj_gold_cross(c.bars_raw, just=False):
            v = Signal(k1=str(freq.value), k2="KDJ状态", v1="金叉")
            s[v.key] = v.value

    if len(c.bars_raw) > 100:
        close = np.array([x.close for x in c.bars_raw[-100:]])
        ma5 = SMA(close, timeperiod=5)
        if c.bars_raw[-1].close >= ma5[-1]:
            v = Signal(k1=str(freq.value), k2="MA5状态", v1="收盘价在MA5上方", v2='')
            s[v.key] = v.value
            if ma5[-1] > ma5[-2] > ma5[-3]:
                v = Signal(k1=str(freq.value), k2="MA5状态", v1='收盘价在MA5上方', v2="向上趋势")
                s[v.key] = v.value

        diff, dea, macd = MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        if diff[-3:-1].mean() > 0 and dea[-3:-1].mean() > 0 and macd[-3] < macd[-2] < macd[-1]:
            v = Signal(k1=str(freq.value), k2="MACD状态", v1="DIFF大于0", v2='DEA大于0', v3='柱子增大')
            s[v.key] = v.value

    # 倒0笔潜在三买
    if len(c.bi_list) >= 5:
        if c.bi_list[-1].direction == Direction.Down:
            gg = max(c.bi_list[-1].high, c.bi_list[-3].high)
            zg = min(c.bi_list[-1].high, c.bi_list[-3].high)
            zd = max(c.bi_list[-1].low, c.bi_list[-3].low)
        else:
            gg = max(c.bi_list[-2].high, c.bi_list[-4].high)
            zg = min(c.bi_list[-2].high, c.bi_list[-4].high)
            zd = max(c.bi_list[-2].low, c.bi_list[-4].low)

        if zg > zd:
            k1 = str(freq.value)
            k2 = "倒0笔"
            k3 = "潜在三买"
            v = Signal(k1=k1, k2=k2, k3=k3, v1="构成中枢")
            if gg * 1.1 > min([x.low for x in c.bars_raw[-3:]]) > zg > zd:
                v = Signal(k1=k1, k2=k2, k3=k3,  v1="构成中枢", v2="近3K在中枢上沿附近")
                if max([x.high for x in c.bars_raw[-7:-3]]) > gg:
                    v = Signal(k1=k1, k2=k2, k3=k3, v1="构成中枢", v2="近3K在中枢上沿附近", v3='近7K突破中枢GG')

            if v and "其他" not in v.value:
                s[v.key] = v.value

    return s
