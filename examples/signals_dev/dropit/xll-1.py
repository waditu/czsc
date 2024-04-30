# -*- coding: utf-8 -*-
"""
author: xielei
email: 781353528@qq.com
create_dt: 2024/02/27 20:00
describe: 构建信号


"""
from czsc import CZSC, get_sub_elements
from czsc.utils import create_single_signal
from collections import OrderedDict
import numpy as np
import talib


def xl_bar_basis_V240412(c: CZSC, **kwargs) -> OrderedDict:
    """长蜡烛形态

    参数模板："{freq}_N{n}#TH{th}_形态V240412"

    **信号逻辑：**

    1. 看涨长蜡烛形态，实体大于 (前N日K线实体长度之和) / N + 系数 * 标准差
    2. 看跌长蜡烛形态

    **信号列表：**
    - Signal('30分钟_N10#TH3_形态V240412_看涨长蜡烛_任意_任意_0')
    - Signal('30分钟_N10#TH3_形态V240412_看跌长蜡烛_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 10))
    th = int(kwargs.get("th", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}#TH{th}_形态V240412".split("_")
    v1 = "其他"

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=n + 1)
    bars_lenth = np.array([abs(x.close - x.open) for x in bars[-n - 1 : -1]])
    bar_solid_th = np.mean(bars_lenth) + th * np.std(bars_lenth)
    bar_solid = bars[-1].close - bars[-1].open

    if bar_solid > 0 and bar_solid > bar_solid_th:
        v1 = "看涨长蜡烛"
    elif bar_solid < 0 and abs(bar_solid) > bar_solid_th:
        v1 = "看跌长蜡烛"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def xl_bar_basis_V240411(c: CZSC, **kwargs) -> OrderedDict:
    """看涨吞没和看跌吞没形态

    参数模板："{freq}_N{n}_形态V240411"

    **信号逻辑：**

    1. 看涨吞没，第二根阳线实体覆盖第一根K线实体和上下影线
    2. 看跌吞没，相反

    **信号列表：**

    - Signal('30分钟_N5_形态V240411_看涨吞没_任意_任意_0')
    - Signal('30分钟_N5_形态V240411_看跌吞没_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 2))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}_形态V240411".split("_")
    v1 = "其他"

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bar1, bar2 = get_sub_elements(c.bars_raw, di=1, n=2)

    if (
        (bar1.open > bar1.close)
        and (bar2.close > bar1.high)
        and (bar2.open <= bar1.low)
    ):
        v1 = "看涨吞没"

    elif (
        (bar1.open < bar1.close)
        and (bar2.open >= bar1.high)
        and (bar2.close < bar1.low)
    ):
        v1 = "看跌吞没"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def xl_bar_basis_V240410(c: CZSC, **kwargs) -> OrderedDict:
    """ADX趋势系统

    参数模板："{freq}_N{n}_突破V240410"

    **信号逻辑：**

    简单用法：
    1，计算+DI、-DI和ADX
    2. +DI 与 -DI 金叉，且ADX 平均值在某个阈值之上，看多
    3. +DI 与 -DI 死叉，且ADX 平均值在某个阈值之上，看空

    **信号列表：**

    - Signal('30分钟_N5_突破V240410_做多_任意_任意_0')
    - Signal('30分钟_N5_突破V240410_做空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 20))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}_突破V240410".split("_")
    v1 = "其他"
    cache_key_dmi = update_dmi_cache_V240409(c, n=n)

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=n)
    plus_di1 = bars[-1].cache[cache_key_dmi].get("plus_di")
    minus_di1 = bars[-1].cache[cache_key_dmi].get("minus_di")
    plus_di2 = bars[-2].cache[cache_key_dmi].get("plus_di")
    minus_di2 = bars[-2].cache[cache_key_dmi].get("minus_di")
    adx = np.array([x.cache[cache_key_dmi].get("adx") for x in bars])

    cod1 = plus_di1 > minus_di1 and plus_di2 < minus_di2
    cod2 = adx.mean() > n
    cod3 = plus_di1 < minus_di1 and plus_di2 > minus_di2

    if cod1 and cod2:
        v1 = "做多"
    elif cod3 and cod2:
        v1 = "做空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def update_dmi_cache_V240409(c: CZSC, **kwargs):
    """更新dmi

    简单用法：
    1，计算+DI、-DI和ADX
    2. +DI 与 -DI 金叉，且ADX 平均值在某个阈值之上，看多
    3. +DI 与 -DI 死叉，且ADX 平均值在某个阈值之上，看空

    :param c: CZSC对象
    :return:
    """
    n = int(kwargs.get("n", 10))

    cache_key = f"DMI{n}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()

    if cache_key not in last_cache.keys() or len(c.bars_raw) < n + n:
        bars = c.bars_raw

    else:
        bars = c.bars_raw[-100:]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    close = np.array([x.close for x in bars])
    plus_di = talib.PLUS_DI(high, low, close, timeperiod=n)
    minus_di = talib.MINUS_DI(high, low, close, timeperiod=n)
    adx = talib.DX(high, low, close, timeperiod=n)

    for i in range(n, len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            dic_dmi = {
                "plus_di": plus_di[i],
                "minus_di": minus_di[i],
                "adx": adx[i],
            }
            _c.update({cache_key: dic_dmi if dic_dmi else None})
            bars[i].cache = _c
    return cache_key


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(
        symbols[0], "15分钟", "20181101", "20210101", fq="前复权"
    )

    signals_config = [{"name": xl_bar_basis_V240412, "freq": "15分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px")  # type: ignore


if __name__ == "__main__":
    check()
