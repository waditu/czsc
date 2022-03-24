# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/25 17:43
describe: 成交量相关信号
"""
import numpy as np
from collections import OrderedDict
from czsc import CZSC, Freq, Signal
from czsc.utils.ta import SMA


def get_s_vol_single_sma(c: CZSC, di: int = 1, t_seq=(5, 10, 20, 60)) -> OrderedDict:
    """获取倒数第i根K线的成交量单均线信号"""
    freq: Freq = c.freq
    s = OrderedDict()

    k1 = str(freq.value)
    k2 = f"倒{di}K成交量"
    for t in t_seq:
        x1 = Signal(k1=k1, k2=k2, k3=f"SMA{t}多空", v1="其他", v2='其他', v3='其他')
        x2 = Signal(k1=k1, k2=k2, k3=f"SMA{t}方向", v1="其他", v2='其他', v3='其他')
        s[x1.key] = x1.value
        s[x2.key] = x2.value

    min_k_nums = max(t_seq) + 10
    if len(c.bars_raw) < min_k_nums:
        return s

    if di == 1:
        vol = np.array([x.vol for x in c.bars_raw[-min_k_nums:]], dtype=np.float)
    else:
        vol = np.array([x.vol for x in c.bars_raw[-min_k_nums-di+1:-di+1]], dtype=np.float)

    for t in t_seq:
        sma = SMA(vol[-t-10:], timeperiod=t)
        if vol[-1] >= sma[-1]:
            v1 = Signal(k1=k1, k2=k2, k3=f"SMA{t}多空", v1="多头")
        else:
            v1 = Signal(k1=k1, k2=k2, k3=f"SMA{t}多空", v1="空头")
        s[v1.key] = v1.value

        if sma[-1] >= sma[-2]:
            v2 = Signal(k1=k1, k2=k2, k3=f"SMA{t}方向", v1="向上")
        else:
            v2 = Signal(k1=k1, k2=k2, k3=f"SMA{t}方向", v1="向下")
        s[v2.key] = v2.value
    return s


def get_s_vol_double_sma(c: CZSC, di: int = 1, t1: int = 5, t2: int = 20) -> OrderedDict:
    """获取倒数第i根K线的成交量双均线信号"""
    assert t2 > t1, "t2必须是长线均线，t1为短线均线"
    freq: Freq = c.freq
    s = OrderedDict()

    k1 = str(freq.value)
    k2 = f"倒{di}K成交量"
    k3 = f"{t1}#{t2}双均线"
    v = Signal(k1=k1, k2=k2, k3=k3, v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    min_len_bars = t2 + 10
    if len(c.bars_raw) < min_len_bars:
        return s

    if di == 1:
        vol = np.array([x.vol for x in c.bars_raw[-min_len_bars:]], dtype=np.float)
    else:
        vol = np.array([x.vol for x in c.bars_raw[-min_len_bars-di+1: -di+1]], dtype=np.float)

    sma1 = SMA(vol, timeperiod=t1)
    sma2 = SMA(vol, timeperiod=t2)

    if sma2[-1] >= sma1[-1]:
        v = Signal(k1=k1, k2=k2, k3=k3, v1="多头")
    else:
        v = Signal(k1=k1, k2=k2, k3=k3, v1="空头")
    s[v.key] = v.value
    return s


def get_s_amount_n(c: CZSC, di=1, n=10, total_amount=10):
    """N日总成交额信号"""
    s = OrderedDict()
    if c.freq != Freq.D or len(c.bars_raw) <= di + n + 5:
        return s

    k1 = str(c.freq.value)
    k2 = f"倒{di}K成交额"
    k3 = f"近{n}日累计超{total_amount}亿"

    if di == 1:
        bars = c.bars_raw[-n:]
    else:
        bars = c.bars_raw[-n-di+1: -di+1]

    assert len(bars) == n

    n_total_amount = sum([x.amount for x in bars])
    if n_total_amount > (total_amount * 1e8):
        v1 = "是"
    else:
        v1 = "否"

    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s
