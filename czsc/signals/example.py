# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/7/3 19:07
describe: 信号计算案例汇总
"""

import numpy as np
try:
    import talib as ta
except:
    from czsc.utils import ta
from collections import OrderedDict
from typing import List, Union, Tuple, Dict
from czsc.objects import Freq, Signal, RawBar, NewBar
from czsc.traders.advanced import CzscAdvancedTrader
from czsc.signals.utils import check_cross_info


def update_sma_cache(cat: CzscAdvancedTrader, freq: str,
                     sma_params: Tuple = (5, 13, 21, 34, 55, 89, 144, 233)):
    """更新某个级别的均线缓存

    :param cat: 交易对象
    :param freq: 指定周期
    :param sma_params: 均线参数
    :return:
    """
    assert freq in cat.freqs, f"{freq} 不在 {cat.freqs} 中"
    cache_key = f"{freq}均线"
    sma_cache = cat.cache.get(cache_key, {})
    sma_cache['update_dt'] = cat.end_dt
    close = np.array([x.close for x in cat.kas[freq].bars_raw])
    sma_cache['close'] = close
    for t in sma_params:
        sma_cache[f"SMA{t}"] = ta.SMA(close, timeperiod=t)
    cat.cache[cache_key] = sma_cache


def update_macd_cache(cat: CzscAdvancedTrader, freq: str):
    """更新某个级别的均线缓存

    :param cat: 交易对象
    :param freq: 指定周期
    :return:
    """
    assert freq in cat.freqs, f"{freq} 不在 {cat.freqs} 中"
    cache_key = f"{freq}MACD"
    cache = cat.cache.get(cache_key, {})
    cache['update_dt'] = cat.end_dt
    close = np.array([x.close for x in cat.kas[freq].bars_raw])
    cache['close'] = close

    dif, dea, macd = ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    cross = check_cross_info(dif, dea)
    cache.update({"dif": dif, 'dea': dea, 'macd': macd, 'cross': cross})
    cat.cache[cache_key] = cache


def update_boll_cache(cat: CzscAdvancedTrader, freq: str):
    """更新某个级别的均线缓存

    :param cat: 交易对象
    :param freq: 指定周期
    :return:
    """
    assert freq in cat.freqs, f"{freq} 不在 {cat.freqs} 中"
    cache_key = f"{freq}BOLL"
    cache = cat.cache.get(cache_key, {})
    cache['update_dt'] = cat.end_dt
    close = np.array([x.close for x in cat.kas[freq].bars_raw])
    cache['close'] = close

    u1, m, l1 = ta.BBANDS(close, timeperiod=20, nbdevup=1.382, nbdevdn=1.382, matype=ta.MA_Type.SMA)
    u2, m, l2 = ta.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=ta.MA_Type.SMA)
    u3, m, l3 = ta.BBANDS(close, timeperiod=20, nbdevup=2.764, nbdevdn=2.764, matype=ta.MA_Type.SMA)

    cache.update({"上轨3": u3, "上轨2": u2, "上轨1": u1, "中线": m, "下轨1": l1, "下轨2": l2, "下轨3": l3})
    cat.cache[cache_key] = cache


def single_sma(cat: CzscAdvancedTrader, freq: str, t_seq=(5, 13, 21)) -> OrderedDict:
    """单均线相关信号

    完全分类：
        Signal('日线_倒1K_SMA5_多头_向上_任意_0'),
        Signal('日线_倒1K_SMA5_空头_向下_任意_0'),
        Signal('日线_倒1K_SMA5_多头_向下_任意_0'),
        Signal('日线_倒1K_SMA5_空头_向上_任意_0'),

        Signal('日线_倒1K_SMA13_空头_向下_任意_0'),
        Signal('日线_倒1K_SMA13_空头_向上_任意_0'),
        Signal('日线_倒1K_SMA13_多头_向上_任意_0'),
        Signal('日线_倒1K_SMA13_多头_向下_任意_0'),

        Signal('日线_倒1K_SMA21_空头_向下_任意_0'),
        Signal('日线_倒1K_SMA21_多头_向下_任意_0'),
        Signal('日线_倒1K_SMA21_多头_向上_任意_0'),
        Signal('日线_倒1K_SMA21_空头_向上_任意_0')
    :param cat:
    :param freq:
    :param t_seq:
    :return:
    """
    assert freq in cat.freqs, f"{freq} 不在 {cat.freqs} 中"
    cache_key = f"{freq}均线"
    sma_cache = cat.cache[cache_key]
    assert sma_cache and sma_cache['update_dt'] == cat.end_dt

    s = OrderedDict()
    k1 = freq
    k2 = "倒1K"
    close = sma_cache['close']
    for t in t_seq:
        sma = sma_cache[f"SMA{t}"]
        if len(sma) == 0:
            v1, v2 = '其他', '其他'
        else:
            v1 = "多头" if close[-1] >= sma[-1] else "空头"
            v2 = "向上" if sma[-1] >= sma[-2] else "向下"

        x1 = Signal(k1=k1, k2=k2, k3=f"SMA{t}", v1=v1, v2=v2)
        s[x1.key] = x1.value
    return s


def macd_base(cat: CzscAdvancedTrader, freq: str):
    """MACD柱子信号

    完全分类：
        Signal('日线_倒1K_MACD_空头_向下_任意_0'),
        Signal('日线_倒1K_MACD_多头_向下_任意_0'),
        Signal('日线_倒1K_MACD_空头_向上_任意_0'),
        Signal('日线_倒1K_MACD_多头_向上_任意_0'),

        Signal('日线_倒1K_MACD强弱_强势_任意_任意_0'),
        Signal('日线_倒1K_MACD强弱_超弱_任意_任意_0'),
        Signal('日线_倒1K_MACD强弱_超强_任意_任意_0'),
        Signal('日线_倒1K_MACD强弱_弱势_任意_任意_0')
    :return:
    """
    s = OrderedDict()
    cache_key = f"{freq}MACD"
    cache = cat.cache[cache_key]
    assert cache and cache['update_dt'] == cat.end_dt
    dif, dea, macd = cache['dif'], cache['dea'], cache['macd']

    v1 = "多头" if macd[-1] >= 0 else "空头"
    v2 = "向上" if macd[-1] >= macd[-2] else "向下"
    signal = Signal(k1=freq, k2="倒1K", k3="MACD", v1=v1, v2=v2)
    s[signal.key] = signal.value

    # MACD强弱
    if dif[-1] >= dea[-1] >= 0:
        v1 = "超强"
    elif dif[-1] - dea[-1] > 0:
        v1 = "强势"
    elif dif[-1] <= dea[-1] <= 0:
        v1 = "超弱"
    elif dif[-1] - dea[-1] < 0:
        v1 = "弱势"
    else:
        v1 = "其他"

    signal = Signal(k1=freq, k2="倒1K", k3="MACD强弱", v1=v1)
    s[signal.key] = signal.value
    return s




