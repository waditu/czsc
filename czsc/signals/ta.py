# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/21 17:48
describe: 技术分析相关信号的计算

ta-lib 安装包：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
"""
import numpy as np
from collections import OrderedDict
from deprecated import deprecated

from .. import analyze
from ..objects import Signal
from ..enum import Freq
try:
    from ..utils.ta1 import MACD, SMA
except:
    from ..utils.ta import MACD, SMA


def get_s_single_k(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """获取倒数第i根K线的单K信号"""
    if c.freq not in [Freq.D, Freq.W]:
        return OrderedDict()

    if len(c.bars_raw) < di:
        return OrderedDict()

    s = OrderedDict()
    freq: Freq = c.freq
    k1 = str(freq.value)
    default_signals = [
        Signal(k1=k1, k2=f"倒{di}K", k3="状态", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    k = c.bars_raw[-di]
    if k.close > k.open:
        v = Signal(k1=k1, k2=f"倒{di}K", k3="状态", v1="上涨")
    else:
        v = Signal(k1=k1, k2=f"倒{di}K", k3="状态", v1="下跌")
    s[v.key] = v.value
    return s


def get_s_three_k(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """倒数第i根K线的三K信号

    :param c: CZSC 对象
    :param di: 最近一根K线为倒数第i根
    :return: 信号字典
    """
    assert di >= 1
    freq: Freq = c.freq
    k1 = str(freq.value)
    k2 = f"倒{di}K"

    s = OrderedDict()
    v = Signal(k1=k1, k2=k2, k3="三K形态", v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    if len(c.bars_ubi) < 3 + di:
        return s

    if di == 1:
        tri = c.bars_ubi[-3:]
    else:
        tri = c.bars_ubi[-3 - di + 1:-di + 1]

    if tri[0].high > tri[1].high < tri[2].high:
        v = Signal(k1=k1, k2=k2, k3="三K形态", v1="底分型")
    elif tri[0].high < tri[1].high < tri[2].high:
        v = Signal(k1=k1, k2=k2, k3="三K形态", v1="向上走")
    elif tri[0].high < tri[1].high > tri[2].high:
        v = Signal(k1=k1, k2=k2, k3="三K形态", v1="顶分型")
    elif tri[0].high > tri[1].high > tri[2].high:
        v = Signal(k1=k1, k2=k2, k3="三K形态", v1="向下走")
    else:
        v = None

    if v and "其他" not in v.value:
        s[v.key] = v.value

    return s


