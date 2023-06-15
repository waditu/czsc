# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/11 18:11
describe: 琅盎的信号函数
"""
from loguru import logger
try:
    import talib as ta
except:
    logger.warning("ta-lib 没有正确安装，相关信号函数无法正常执行。"
                   "请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import numpy as np
from typing import List
from collections import OrderedDict
from czsc.analyze import CZSC, RawBar
from czsc.utils.sig import get_sub_elements, create_single_signal


def adtm_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """ADTM能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603"

    **信号逻辑：**

    1. 如果今天的开盘价大于昨天的开盘价，取最高价 - 开盘价、开盘价 - 昨天的开盘价这二者中最大值,
        再将取出的最大值求和；反之取0，形成up_sum
    2. 如果今天的开盘价小于昨天的开盘价，取开盘价 - 最低价、昨天的开盘价 -开盘价这二者中最大值,
        再将取出的最大值求和；么之取0，形成dw_sum
    3. 当 up_sum > dw_sum 或 最大值的差值之商小于TH 看多，反之看空


    **信号列表：**

    - Signal('日线_D1N30M20TH5_ADTMV230603_看空_任意_任意_0')
    - Signal('日线_D1N30M20TH5_ADTMV230603_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
        - :param th: adtm阈值，默认为5，代表 5 / 10 = 0.5
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 20))
    th = int(kwargs.get("th", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603".split('_')

    v1 = "其他"
    if len(c.bars_raw) < di + max(n, m) + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)

    up_sum = np.sum([max(n_bars[i].high - n_bars[i].open, n_bars[i].open - n_bars[i - 1].open)
                     for i in range(1, len(n_bars)) if n_bars[i].open > n_bars[i - 1].open])
    dw_sum = np.sum([max(m_bars[i].open - m_bars[i].low, m_bars[i - 1].open - m_bars[i].open)
                     for i in range(1, len(m_bars)) if m_bars[i].open < m_bars[i - 1].open])

    adtm = (up_sum - dw_sum) / max(up_sum, dw_sum)
    if up_sum > dw_sum or adtm > th / 10:
        v1 = "看多"
    if up_sum < dw_sum or adtm < th / 10:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def amv_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """AMV能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_AMV能量V230603"

    **信号逻辑：**

    用成交量作为权重对开盘价和收盘价的均值进行加权移动平均。成交量越大的价格对移动平均结果的影响越大，
    AMV 指标减小了成交量小的价格波动的影响。当短期 AMV 线上穿/下穿长期 AMV线时，产生买入/卖出信号。


    **信号列表：**

    - Signal('日线_D1N30M120_AMV能量V230603_看多_任意_任意_0')
    - Signal('日线_D1N30M120_AMV能量V230603_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 120))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_AMV能量V230603".split('_')
    if n > m or len(c.bars_raw) < di + m + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)

    amov1 = np.sum([(n_bars[i].amount * (n_bars[i].open + n_bars[i].close) / 2) for i in range(len(n_bars))])
    amov2 = np.sum([(m_bars[i].amount * (m_bars[i].open + m_bars[i].close) / 2) for i in range(len(m_bars))])
    vol_sum1 = np.sum([n_bars[i].amount for i in range(len(n_bars))])
    vol_sum2 = np.sum([m_bars[i].amount for i in range(len(m_bars))])
    amv1 = amov1 / vol_sum1
    amv2 = amov2 / vol_sum2

    v1 = "看多" if amv1 > amv2 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def asi_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """ASI多空分类，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}P{p}_ASI多空V230603"

    **信号逻辑：**

    由于 SI 的波动性比较大，所以我们一般对 SI 累计求和得到 ASI 并捕
    捉 ASI 的变化趋势。一般我们不会直接看 ASI 的数值（对 SI 累计求
    和的求和起点不同会导致求出 ASI 的值不同），而是会观察 ASI 的变
    化方向。我们利用 ASI 与其均线的交叉来产生交易信号,上穿/下穿均
    线时买入/卖出

    **信号列表：**

    - Signal('日线_D1N30P120_ASI多空V230603_看多_任意_任意_0')
    - Signal('日线_D1N30P120_ASI多空V230603_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param p: 获取K线的根数，默认为20
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    p = int(kwargs.get("p", 120))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}P{p}_ASI多空V230603".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + p + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=p)  
    close_prices = np.array([bar.close for bar in _bars])
    open_prices = np.array([bar.open for bar in _bars])
    high_prices = np.array([bar.high for bar in _bars])
    low_prices = np.array([bar.low for bar in _bars])

    o = np.concatenate([[close_prices[0]], close_prices[:-1]])
    a = np.abs(high_prices - o)
    b = np.abs(low_prices - o)
    c = np.abs(high_prices - np.concatenate([[low_prices[0]], low_prices[:-1]])) # type: ignore
    d = np.abs(o - np.concatenate([[open_prices[0]], open_prices[:-1]]))

    k = np.maximum(a, b)  
    m = np.maximum(high_prices - low_prices, n)
    r1 = a + 0.5 * b + 0.25 * d
    r2 = b + 0.5 * a + 0.25 * d
    r3 = c + 0.25 * d
    r4 = np.where((a >= b) & (a >= c), r1, r2)
    r = np.where((c >= a) & (c >= b), r3, r4)
    
    if (r * k / m != 0).all():
        si = 50 * (close_prices - c + (c - open_prices) + 0.5 * (close_prices - open_prices)) / (r * k / m)
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    asi = np.cumsum(si) 

    v1 = "看多" if asi[-1] > np.mean(asi[-p:]) else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def clv_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """CLV多空分类，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_CLV多空V230605"

    **信号逻辑：**

    CLV 用来衡量收盘价在最低价和最高价之间的位置。
    当CLOSE=HIGH 时，CLV=1; 当 CLOSE=LOW 时，CLV=-1;当 CLOSE位于 HIGH 和 LOW 的中点时，
    CLV=0。CLV>0（<0），说明收盘价离最高（低）价更近。我们用 CLVMA 上穿/下穿 0 来产生买入/卖出信号

    **信号列表：**
    
    - Signal('日线_D1N70_CLV多空V230605_看多_任意_任意_0')
    - Signal('日线_D1N70_CLV多空V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为60
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 70))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_CLV多空V230605".split('_')

    if len(c.bars_raw) < di + 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)  

    close = np.array([bar.close for bar in _bars])
    low = np.array([bar.low for bar in _bars])
    high = np.array([bar.high for bar in _bars])
    clv_ma = np.mean((2 * close - low - high) / (high - low))

    v1 = "看多" if clv_ma > 0 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cmo_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """CMO能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_CMO能量V230605"

    信号逻辑：**

    CMO指标用过去N天的价格上涨量和价格下跌量得到，CMO>(<)0 表示当前处于上涨（下跌）趋势，CMO 越
    大（小）则当前上涨（下跌）趋势越强。我们用 CMO 上穿 30/下穿-30来产生买入/卖出信号。

    信号列表：

    - Signal('30分钟_D1N70M30_CMO能量V230605_看空_任意_任意_0')
    - Signal('30分钟_D1N70M30_CMO能量V230605_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为60
        - :param m: 信号预警轴，默认为30
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 70))
    m = int(kwargs.get("m", 30))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_CMO能量V230605".split('_')

    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    up_sum = np.sum([_bars[i].close - _bars[i - 1].close for i in range(1, len(_bars))
                     if (_bars[i].close - _bars[i - 1].close) > 0])
    dw_sum = np.sum([_bars[i - 1].close - _bars[i].close for i in range(1, len(_bars))
                     if (_bars[i - 1].close - _bars[i].close) > 0])

    cmo = (up_sum - dw_sum) / (up_sum + dw_sum) * 100
    if cmo > m:
        v1 = "看多"
    if cmo < -m:
        v1 = "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
