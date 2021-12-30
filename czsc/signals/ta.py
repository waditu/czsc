# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/21 17:48
describe: 技术分析相关信号的计算
"""
import numpy as np
from collections import OrderedDict
from datetime import datetime

from czsc import analyze
from ..objects import Signal
from ..enum import Freq
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


def get_s_macd(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """获取倒数第i根K线的MACD相关信号"""
    freq: Freq = c.freq
    s = OrderedDict()

    k1 = str(freq.value)
    k2 = f"倒{di}K"
    default_signals = [
        Signal(k1=k1, k2=k2, k3="DIF多空", v1="其他", v2='其他', v3='其他'),
        Signal(k1=k1, k2=k2, k3="DIF方向", v1="其他", v2='其他', v3='其他'),

        Signal(k1=k1, k2=k2, k3="DEA多空", v1="其他", v2='其他', v3='其他'),
        Signal(k1=k1, k2=k2, k3="DEA方向", v1="其他", v2='其他', v3='其他'),

        Signal(k1=k1, k2=k2, k3="MACD多空", v1="其他", v2='其他', v3='其他'),
        Signal(k1=k1, k2=k2, k3="MACD方向", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    if len(c.bars_raw) < 100:
        return s

    if di == 1:
        close = np.array([x.close for x in c.bars_raw[-100:]])
    else:
        close = np.array([x.close for x in c.bars_raw[-100-di+1:-di+1]])
    dif, dea, macd = MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

    # DIF 多空信号
    dif_base = sum([abs(dif[-2] - dif[-1]), abs(dif[-3] - dif[-2]), abs(dif[-4] - dif[-3])]) / 3
    if dif[-1] > dif_base:
        v = Signal(k1=k1, k2=k2, k3="DIF多空", v1="多头")
    elif dif[-1] < -dif_base:
        v = Signal(k1=k1, k2=k2, k3="DIF多空", v1="空头")
    else:
        v = Signal(k1=k1, k2=k2, k3="DIF多空", v1="模糊")
    s[v.key] = v.value

    if dif[-1] > dif[-2] > dif[-3]:
        v = Signal(k1=k1, k2=k2, k3="DIF方向", v1="向上")
    elif dif[-1] < dif[-2] < dif[-3]:
        v = Signal(k1=k1, k2=k2, k3="DIF方向", v1="向下")
    else:
        v = Signal(k1=k1, k2=k2, k3="DIF方向", v1="模糊")
    s[v.key] = v.value

    # DEA 多空信号
    dea_base = sum([abs(dea[-2] - dea[-1]), abs(dea[-3] - dea[-2]), abs(dea[-4] - dea[-3])]) / 3
    if dea[-1] > dea_base:
        v = Signal(k1=k1, k2=k2, k3="DEA多空", v1="多头")
    elif dea[-1] < -dea_base:
        v = Signal(k1=k1, k2=k2, k3="DEA多空", v1="空头")
    else:
        v = Signal(k1=k1, k2=k2, k3="DEA多空", v1="模糊")
    s[v.key] = v.value

    # DEA 方向信号
    if dea[-1] > dea[-2]:
        v = Signal(k1=k1, k2=k2, k3="DEA方向", v1="向上")
    elif dea[-1] < dea[-2]:
        v = Signal(k1=k1, k2=k2, k3="DEA方向", v1="向下")
    else:
        v = Signal(k1=k1, k2=k2, k3="DEA方向", v1="模糊")
    s[v.key] = v.value

    # MACD 多空信号
    if macd[-1] >= 0:
        v = Signal(k1=k1, k2=k2, k3="MACD多空", v1="多头")
    else:
        v = Signal(k1=k1, k2=k2, k3="MACD多空", v1="空头")
    s[v.key] = v.value

    # MACD 方向信号
    if macd[-1] > macd[-2] > macd[-3]:
        v = Signal(k1=k1, k2=k2, k3="MACD方向", v1="向上")
    elif macd[-1] < macd[-2] < macd[-3]:
        v = Signal(k1=k1, k2=k2, k3="MACD方向", v1="向下")
    else:
        v = Signal(k1=k1, k2=k2, k3="MACD方向", v1="模糊")
    s[v.key] = v.value
    return s


def get_s_sma(c: analyze.CZSC, di: int = 1, t_seq=(5, 10, 20, 60)) -> OrderedDict:
    """获取倒数第i根K线的SMA相关信号"""
    freq: Freq = c.freq
    s = OrderedDict()

    k1 = str(freq.value)
    k2 = f"倒{di}K"
    for t in t_seq:
        x1 = Signal(k1=k1, k2=k2, k3=f"SMA{t}多空", v1="其他", v2='其他', v3='其他')
        x2 = Signal(k1=k1, k2=k2, k3=f"SMA{t}方向", v1="其他", v2='其他', v3='其他')
        s[x1.key] = x1.value
        s[x2.key] = x2.value

    if len(c.bars_raw) < 100:
        return s

    if di == 1:
        close = np.array([x.close for x in c.bars_raw[-100:]])
    else:
        close = np.array([x.close for x in c.bars_raw[-100-di+1:-di+1]])

    for t in t_seq:
        sma = SMA(close, timeperiod=t)
        if close[-1] >= sma[-1]:
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


def get_s_bar_end(c: analyze.CZSC) -> OrderedDict:
    """K线结束时间判断"""
    freq: Freq = c.freq
    if freq != Freq.F1:
        return OrderedDict()

    s = OrderedDict()
    default_signals = [
        Signal(k1="5分钟", k2="倒1K", k3="结束", v1="其他", v2='其他', v3='其他'),
        Signal(k1="15分钟", k2="倒1K", k3="结束", v1="其他", v2='其他', v3='其他'),
        Signal(k1="30分钟", k2="倒1K", k3="结束", v1="其他", v2='其他', v3='其他'),
        Signal(k1="60分钟", k2="倒1K", k3="结束", v1="其他", v2='其他', v3='其他'),
        Signal(k1="日线", k2="倒1K", k3="结束", v1="其他", v2='其他', v3='其他'),

        Signal(k1="股票", k2="开仓", k3="时间范围A", v1="其他", v2='其他', v3='其他'),
        Signal(k1="股票", k2="开仓", k3="时间范围B", v1="其他", v2='其他', v3='其他'),
        Signal(k1="股票", k2="开仓", k3="时间范围C", v1="其他", v2='其他', v3='其他'),
        Signal(k1="股票", k2="开仓", k3="时间范围D", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    dt: datetime = c.bars_raw[-1].dt
    for i in [5, 15, 30, 60]:
        if dt.minute % i == 0:
            v = Signal(k1=f"{i}分钟", k2="倒1K", k3="结束", v1="是")
        else:
            v = Signal(k1=f"{i}分钟", k2="倒1K", k3="结束", v1="否")
        s[v.key] = v.value

    if dt.hour == 14 and 45 < dt.minute < 56:
        v = Signal(k1="日线", k2="倒1K", k3="结束", v1="是")
        s[v.key] = v.value

    if "10:00" <= dt.strftime("%H:%M") <= "14:59":
        v = Signal(k1="股票", k2="开仓", k3="时间范围A", v1="上午十点", v2='下午三点')
        s[v.key] = v.value

    if "11:00" <= dt.strftime("%H:%M") <= "14:59":
        v = Signal(k1="股票", k2="开仓", k3="时间范围B", v1="上午十一点", v2='下午三点')
        s[v.key] = v.value

    if "13:30" <= dt.strftime("%H:%M") <= "14:59":
        v = Signal(k1="股票", k2="开仓", k3="时间范围C", v1="下午一点半", v2='下午三点')
        s[v.key] = v.value

    if "14:30" <= dt.strftime("%H:%M") <= "14:59":
        v = Signal(k1="股票", k2="开仓", k3="时间范围D", v1="下午两点半", v2='下午三点')
        s[v.key] = v.value

    return s

