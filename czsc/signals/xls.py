# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/04/07 22:17
describe: 谢磊贡献的信号函数
"""
import numpy as np
from typing import Union, List
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements
from czsc.signals.tas import update_ma_cache
from czsc.signals.jcc import check_szx
from czsc import CZSC


def xl_bar_position_V240328(c: CZSC, **kwargs) -> OrderedDict:
    """相对位置信号; 贡献者：谢磊

    参数模板："{freq}_N{n}_BS辅助V240328"

    **信号逻辑：**

    1. 用当前价格与EMA的比值做一个偏离度指标
    2. 当偏离度越高就越有可能是相对低点的位置

    **信号列表：**
    - Signal('30分钟_N10_BS辅助V240328_相对低点_任意_任意_0')
    - Signal('30分钟_N10_BS辅助V240328_相对高点_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """

    n = int(kwargs.get("n", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}_BS辅助V240328".split("_")
    v1 = "其他"

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=n + 2 * n)
    close = np.array([x.close for x in bars])
    cache_key_ema = update_ma_cache(c, ma_type="EMA", timeperiod=n)
    ema = np.array([x.cache[cache_key_ema] for x in bars])
    nor = (close - ema) / ema

    if nor[-1] < np.quantile(nor, 0.3, method="midpoint"):
        v1 = "相对低点"

    elif nor[-1] > np.quantile(nor, 0.7, method="midpoint"):
        v1 = "相对高点"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def xl_bar_trend_V240329(c: CZSC, **kwargs) -> OrderedDict:
    """底部反转形态信号; 贡献者：谢磊

    正向的十字孕线（Bullish Harami Cross）是一种看涨的蜡烛图形态，属于孕线形态的一种变体。
    这种形态出现在下跌趋势的末端，可能预示着趋势即将反转向上。正向的十字孕线由两根蜡烛图组成：
    第一根是一个长实体的阴线，显示了强劲的下跌趋势；第二根是一个十字线（或接近十字线的形态），
    其开盘价和收盘价都处于第一根阴线实体的中部以下，但实体部分较小，且颜色可以是阳线或阴线。

    参数模板："{freq}_N{n}M{m}_十字线反转V240329"

    **信号逻辑：**

    1， 十字线定义，(h -l) / (c - o) 的绝对值大于 th，或 c == o


    **信号列表：**
    - Signal('30分钟_N5M5_十字线反转V240329_底部十字孕线_任意_任意_0')
    - Signal('30分钟_N5M5_十字线反转V240329_顶部十字孕线_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 10))
    m = int(kwargs.get("m", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}M{m}_十字线反转V240329".split("_")
    v1, v2 = "其他", "其他"

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    bar1, bar2 = get_sub_elements(c.bars_raw, di=1, n=2)
    if check_szx(bar2, n) and bar1.close < bar1.open and (bar1.open - bar1.close) / (bar1.high - bar1.low) * 10 >= m:
        v1 = "底部十字孕线"

    if check_szx(bar2, n) and bar1.close > bar1.open and (bar1.close - bar1.open) / (bar1.high - bar1.low) * 10 >= m:
        v1 = "顶部十字孕线"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def xl_bar_trend_V240330(c: CZSC, **kwargs) -> OrderedDict:
    """完全分类，均线金叉过滤信号; 贡献者：谢磊

    参数模板："{freq}_N{n}M{m}#{ma_type}_双均线过滤V240330"

    **信号逻辑：**

    1， 当25日均线大于350日均线，看多
    2.  当25日均线小于350日均线，看空
    3.  均线类型可选，平均线，EMA线。

    **信号列表：**

    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第03次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第04次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第05次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第06次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第07次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第08次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第09次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第10次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第01次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第02次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第03次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第04次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第01次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看空_第02次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第05次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第06次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第07次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第08次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第09次_任意_0')
    - Signal('15分钟_N5M21#SMA_双均线过滤V240330_看多_第10次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 5))
    m = int(kwargs.get("m", 21))
    ma_type = kwargs.get("ma_type", "SMA")

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}M{m}#{ma_type}_双均线过滤V240330".split("_")
    v1, v2 = "其他", "其他"

    if len(c.bars_raw) < m + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    cache_key1 = update_ma_cache(c, ma_type=ma_type, timeperiod=n)
    cache_key2 = update_ma_cache(c, ma_type=ma_type, timeperiod=m)
    bars = get_sub_elements(c.bars_raw, di=1, n=m + 1)
    cache1 = [x.cache[cache_key1] for x in bars]
    cache2 = [x.cache[cache_key2] for x in bars]

    def _countN(x1: Union[List, np.array], x2: Union[List, np.array]):  # type: ignore
        """输入两个序列，计算 次数

        :param x1: list
        :param x2: list
        :return: int
        """
        x = np.array(x1) < np.array(x2)
        y = np.array(x1) > np.array(x2)
        num = 0
        for i in range(len(x) - 1):
            b1, b2 = x[i], x[i + 1]
            if b2 and b1 != b2:
                num = 1
            elif b2 and b1 == b2:
                num += 1
            b3, b4 = y[i], y[i + 1]
            if b4 and b3 != b4:
                num = 1
            elif b4 and b3 == b4:
                num += 1

            if num >= 10:
                num = 10
        return num

    num = _countN(cache1, cache2)
    num = f"第{str(num).zfill(2)}次"
    if cache1[-1] > cache2[-1]:
        v1 = "看多"
        v2 = num

    elif cache1[-1] < cache2[-1]:
        v1 = "看空"
        v2 = num

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def xl_bar_trend_V240331(c: CZSC, **kwargs) -> OrderedDict:
    """突破信号; 贡献者：谢磊

    参数模板："{freq}_N{n}_突破信号V240331"

    **信号逻辑：**

    1， 突破前N日最高价，入场，做多
    2.  跌破前N日最低价，入场，做空

    **信号列表：**

    - Signal('30分钟_N20_突破信号V240331_做多_任意_任意_0')
    - Signal('30分钟_N20_突破信号V240331_做空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 20))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}_突破信号V240331".split("_")
    v1 = "其他"

    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars2 = get_sub_elements(c.bars_raw, di=1, n=n + 1)
    hh = max([x.high for x in bars2[0:-1]])
    ll = min([x.low for x in bars2[0:-1]])
    _high = bars2[-1].high
    _low = bars2[-1].low

    if _high >= hh:
        v1 = "做多"

    elif _low <= ll:
        v1 = "做空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


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

    if (bar1.open > bar1.close) and (bar2.close > bar1.high) and (bar2.open <= bar1.low):
        v1 = "看涨吞没"

    elif (bar1.open < bar1.close) and (bar2.open >= bar1.high) and (bar2.close < bar1.low):
        v1 = "看跌吞没"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def xl_bar_trend_V240623(c: CZSC, **kwargs) -> OrderedDict:
    """突破信号; 贡献者：谢磊

    参数模板："{freq}_N{n}通道_突破信号V240623"

    **信号逻辑：**

    1， 突破前N日最高价，入场，做多
    2.  跌破前N日最低价，入场，做空

    **信号列表：**

    - Signal('30分钟_N20通道_突破信号V240623_做多_连续2次上涨_任意_0')
    - Signal('30分钟_N20通道_突破信号V240623_做空_连续2次下跌_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - n: int, 默认20，突破前N日的最高价或最低价

    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 20))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}通道_突破信号V240623".split("_")
    v1 = "其他"
    v2 = "任意"

    bars2 = get_sub_elements(c.bars_raw, di=1, n=n + 1)
    hh = max([x.high for x in bars2[0:-2]])
    ll = min([x.low for x in bars2[0:-2]])
    _high = bars2[-2].high
    _low = bars2[-2].low

    if _high >= hh:
        v1 = "做多"
        if bars2[-1].high > _high:
            v2 = "连续2次上涨"

    elif _low <= ll:
        v1 = "做空"
        if bars2[-1].low < _low:
            v2 = "连续2次下跌"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
