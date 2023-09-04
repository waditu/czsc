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
import pandas as pd
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


def skdj_up_dw_line_V230611(c: CZSC, **kwargs) -> OrderedDict:
    """SKDJ随机波动指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}UP{up}DW{dw}_SKDJ随机波动V230611"

    **信号逻辑：**

    SKDJ 为慢速随机波动（即慢速 KDJ）。SKDJ 中的 K 即 KDJ 中的 D，
    SKJ 中的 D 即 KDJ 中的 D 取移动平均。其用法与 KDJ 相同。
    当 D<40(处于超卖状态)且 K 上穿 D 时买入，当 D>60（处于超买状
    态）K 下穿 D 时卖出。

    **信号列表：**

    - Signal('日线_D1N233M145UP60DW40_SKDJ随机波动V230611_看多_任意_任意_0')
    - Signal('日线_D1N233M145UP60DW40_SKDJ随机波动V230611_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 取K线数量n必需大于m*2
        - :param m: 计算均值需要的参数
        - :param up: 信号预警值
        - :param dw: 信号预警值
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 233))
    m = int(kwargs.get("m", 89))
    up = int(kwargs.get("up", 60))
    dw = int(kwargs.get("dw", 40))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_SKDJ随机波动V230611".split('_')

    # 计算RSV缓存
    rsv_cache = f'RSV{n}'
    for i, bar in enumerate(c.bars_raw):
        if bar.cache.get(rsv_cache) is not None:
            continue
        if i < n:
            n_bars = c.bars_raw[:i+1]
        else:
            n_bars = get_sub_elements(c.bars_raw, di=i, n=n)
        
        min_low = min([x.low for x in n_bars])
        max_high = max([x.high for x in n_bars])
        bar.cache[rsv_cache] = (bar.close - min_low) / (max_high - min_low) * 100

    v1 = "其他"
    if len(c.bars_raw) < di + m*3 + 20 or n < m:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=m*3 + 20)
    rsv = np.array([bar.cache[rsv_cache] for bar in bars])
    ma_rsv = np.convolve(rsv, np.ones(m)/m, mode='valid')
    k = np.convolve(ma_rsv, np.ones(m)/m, mode='valid')
    d = np.mean(k[-m:])

    if dw < d < k[-1]:
        v1 = "看多"
    if k[-1] < d > up:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bias_up_dw_line_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """BIAS乖离率指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618"

    **信号逻辑：**

    乖离率 BIAS 用来衡量收盘价与移动平均线之间的差距。
    当 BIAS6 大于 3 且 BIAS12 大于 5 且 BIAS24 大于 8，
    三个乖离率均进入股价强势上涨区间，产生买入信号；
    当 BIAS6 小于-3 且 BIAS12 小于-5 且BIAS24 小于-8 时，
    三种乖离率均进入股价强势下跌区间，产生卖出信号

    **信号列表：**

    - Signal('日线_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看空_任意_任意_0')
    - Signal('日线_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 6))
    m = int(kwargs.get("m", 12))
    p = int(kwargs.get("p", 24))
    th1 = int(kwargs.get("th1", 1))
    th2 = int(kwargs.get("th2", 3))
    th3 = int(kwargs.get("th3", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + max(n, m, p):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars1 = get_sub_elements(c.bars_raw, di=di, n=n)
    bars2 = get_sub_elements(c.bars_raw, di=di, n=m)
    bars3 = get_sub_elements(c.bars_raw, di=di, n=p)

    bias_ma1 = np.mean([bars1[i].close for i in range(len(bars1))])
    bias_ma2 = np.mean([bars2[i].close for i in range(len(bars2))])
    bias_ma3 = np.mean([bars3[i].close for i in range(len(bars3))])

    bias1 = (bars1[-1].close - bias_ma1) / bias_ma1 * 100
    bias2 = (bars2[-1].close - bias_ma2) / bias_ma2 * 100
    bias3 = (bars3[-1].close - bias_ma3) / bias_ma3 * 100

    if bias1 > th1 and bias2 > th2 and bias3 > th3:
        v1 = "看多"
    if bias1 < -th1 and bias2 < -th2 and bias3 < -th3:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def dema_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """DEMA短线趋势指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_DEMA短线趋势V230605"

    **信号逻辑：**
    
    DEMA指标是一种趋势指标，用于衡量价格趋势的方向和强度。
    与其他移动平均线指标相比，DEMA指标更加灵敏，能够更快地反应价格趋势的变化，因此在短期交易中具有一定的优势。
    当收盘价大于DEMA看多， 当收盘价小于DEMA看空

    **信号列表：**

    - Signal('日线_D1N5_DEMA短线趋势V230605_看多_任意_任意_0')
    - Signal('日线_D1N5_DEMA短线趋势V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为5

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_DEMA短线趋势V230605".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + 2*n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    short_bars = get_sub_elements(c.bars_raw, di=di, n=n)
    long_bars = get_sub_elements(c.bars_raw, di=di, n=n * 2)
    dema = np.mean([x.close for x in short_bars]) * 2 - np.mean([x.close for x in long_bars])

    v1 = "看多" if short_bars[-1].close > dema else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def demakder_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """DEMAKER价格趋势指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}TH{th}TL{tl}_DEMAKER价格趋势V230605"

    **信号逻辑：**

    DEMAKER指标的作用是用于判断价格的趋势和力度
    当 demaker>0.6 时上升趋势强烈，当 demaker<0.4 时下跌趋势强烈。
    当 demaker 上穿 0.6/下穿 0.4 时产生买入/卖出信号。

    **信号列表：**

    - Signal('日线_D1N105TH5TL5_DEMAKER价格趋势V230605_看多_任意_任意_0')
    - Signal('日线_D1N105TH5TL5_DEMAKER价格趋势V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为105
        - :param th: 开多阈值，默认为6
        - :param tl: 开空阈值，默认为4

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 105))
    th = int(kwargs.get("th", 5))
    tl = int(kwargs.get("tl", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}TH{th}TL{tl}_DEMAKER价格趋势V230605".split('_')

    # 增加一个约束，如果K线数量不足时直接返回
    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    demax = np.mean([bars[i].high - bars[i-1].high for i in
                     range(1, len(bars)) if bars[i].high - bars[i-1].high > 0])
    demin = np.mean([bars[i-1].low - bars[i].low for i in
                     range(1, len(bars)) if bars[i-1].low - bars[i].low > 0])
    demaker = demax / (demax + demin)

    if demaker > th / 10:
        v1 = "看多"
    if demaker < tl / 10:
        v1 = "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def emv_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """EMV简易波动指标，贡献者：琅盎

    参数模板："{freq}_D{di}_EMV简易波动V230605"

    **信号逻辑：**

    emv 综合考虑了成交量和价格（中间价）的变化。
    emv>0 则多头处于优势，emv 上升说明买方力量在增大；
    emv<0 则空头处于优势，emv 下降说明卖方力量在增大。
    如果 emv 上穿 0，则产生买入信号；
    如果 emv 下穿 0，则产生卖出信号。

    **信号列表：**

    - Signal('日线_D1_EMV简易波动V230605_看多_任意_任意_0')
    - Signal('日线_D1_EMV简易波动V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}_EMV简易波动V230605".split('_')

    # 增加一个约束，如果K线数量不足时直接返回
    v1 = "其他"
    if len(c.bars_raw) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=2)
    mid_pt_move = (_bars[-1].high + _bars[-1].low) / 2 - (_bars[-2].high + _bars[-2].low) / 2
    box_ratio = _bars[-1].vol / (_bars[-1].high - _bars[-1].low + 1e-9)
    emv = mid_pt_move / box_ratio

    v1 = "看多" if emv > 0 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def er_up_dw_line_V230604(c: CZSC, **kwargs) -> OrderedDict:
    """ER价格动量指标，贡献者：琅盎

    参数模板："{freq}_D{di}W{w}N{n}_ER价格动量V230604"

    **信号逻辑：**

    er 为动量指标。用来衡量市场的多空力量对比。在多头市场，
    人们会更贪婪地在接近高价的地方买入，BullPower 越高则当前
    多头力量越强；而在空头市场，人们可能因为恐惧而在接近低价
    的地方卖出。BearPower 越低则当前空头力量越强。当两者都大
    于 0 时，反映当前多头力量占据主导地位；两者都小于 0 则反映
    空头力量占据主导地位。
    如果 BearPower 上穿 0，则产生买入信号；
    如果 BullPower 下穿 0，则产生卖出信号。

    **信号列表：**

    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第10层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第9层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第8层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第5层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第1层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第10层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第2层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第6层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第7层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第8层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第9层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第4层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第5层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第7层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第3层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第2层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第6层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第1层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第4层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第3层_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为105

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 60))
    n = int(kwargs.get("n", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}N{n}_ER价格动量V230604".split('_')

    cache_key = f"ER{w}"
    for i, bar in enumerate(c.bars_raw, 1):
        if cache_key in bar.cache:
            continue
        _bars = c.bars_raw[i-w:i]
        ma = np.mean([x.close for x in _bars])
        bull_power = bar.high - ma if bar.high > ma else bar.low - ma
        bar.cache.update({cache_key: bull_power})

    v1 = "其他"
    if len(c.bars_raw) < di + w + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=w*10)
    factors = [x.cache[cache_key] for x in _bars]
    factors = [x for x in factors if x * factors[-1] > 0]

    v1 = "均线上方" if factors[-1] > 0 else "均线下方"
    q = pd.cut(factors, n, labels=list(range(1, n+1)), precision=5, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{q}层")


def obvm_line_V230610(c: CZSC, **kwargs) -> OrderedDict:
    """OBV能量指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_OBV能量V230610"

    **信号逻辑：**

    OBV 指标把成交量分为正的成交量（价格上升时的成交量）和负的成交量（价格下降时）的成交量。
    OBV 就是分了正负之后的成交量的累计和。

    首先，根据传入的参数 di、n 和 m，从 CZSC 对象中获取对应的 K 线数据，然后计算 OBV 序列。
    接着，使用 talib 库中的 EMA 函数计算 OBV 序列的短期和长期指数移动平均线，
    最后根据两条移动平均线的大小关系判断看多或看空信号。

    飞书文档：https://s0cqcxuy3p.feishu.cn/wiki/CEMLwa46Ii1sJZkT3IVcJKAwntc
    
    **信号列表：**

    - Signal('日线_D1N10M30_OBV能量V230610_看空_任意_任意_0')
    - Signal('日线_D1N10M30_OBV能量V230610_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param n: short窗口大小。
        - :param m: long窗口大小。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 10))
    m = int(kwargs.get("m", 30))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_OBV能量V230610".split('_')
    v1 = "其他"

    # 计算OBV，缓存到bar.cache中
    cache_key = "OBV"
    for i in range(1, len(c.bars_raw)):
        bar1, bar2 = c.bars_raw[i - 1], c.bars_raw[i]
        if cache_key not in bar1.cache:
            last_obv = bar1.vol if bar1.close > bar1.open else -bar1.vol
            bar1.cache[cache_key] = last_obv
        else:
            last_obv = bar1.cache[cache_key]

        if cache_key not in bar2.cache:
            cur_obv = bar2.vol if bar2.close > bar2.open else -bar2.vol
            bar2.cache[cache_key] = last_obv + cur_obv

    if len(c.bars_raw) < di + max(n, m) + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=max(n, m) + 10)
    obv_seq = np.array([x.cache[cache_key] for x in bars], dtype=np.float64)

    ema_n1 = ta.EMA(obv_seq, n)[-1]
    ema_n2 =ta.EMA(obv_seq, m)[-1]

    v1 =  "看多" if ema_n1 > ema_n2 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def obv_up_dw_line_V230719(c: CZSC, **kwargs) -> OrderedDict:
    """OBV能量指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719"

    **信号逻辑：**

    OBV 指标把成交量分为正的成交量（价格上升时的成交量）和负的成交量（价格下降时）的成交量。
    OBV 就是分了正负之后的成交量的累计和。

    1. 先定义OBVM，OBVM是 OBV 7天的指数平均。
    2. 再定义一条信号线Signal line，这条线是OBVM 10天的指数平均。

    其中的「7天」和「10天」都是参数，根据你的交易时间级别设置，设置的越小，OBVM对成交量的变化越敏感，
    产生的交易信号也就越多。

    开多仓的规则：当OBVM上穿Signal line，开多仓；当OBVM下穿Signal line，平仓。这个规则只捕捉上涨趋势。

    **信号列表：**

    - Signal('日线_D1N7M10MO3_OBV能量V230719_看多_任意_任意_0')
    - Signal('日线_D1N7M10MO3_OBV能量V230719_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param n: short窗口大小。
        - :param m: long窗口大小。
        - :param max_overlap: 信号计算时，最大重叠K线数量。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 7))
    m = int(kwargs.get("m", 10))
    max_overlap = int(kwargs.get("max_overlap", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719".split('_')
    v1 = "其他"

    # 计算OBV，缓存到bar.cache中
    cache_key = "OBV"
    for i in range(1, len(c.bars_raw)):
        bar1, bar2 = c.bars_raw[i - 1], c.bars_raw[i]
        if cache_key not in bar1.cache:
            last_obv = bar1.vol if bar1.close > bar1.open else -bar1.vol
            bar1.cache[cache_key] = last_obv
        else:
            last_obv = bar1.cache[cache_key]

        if cache_key not in bar2.cache:
            cur_obv = bar2.vol if bar2.close > bar2.open else -bar2.vol
            bar2.cache[cache_key] = last_obv + cur_obv

    min_k_num = di + max(n, m) + max_overlap + 10
    if len(c.bars_raw) < min_k_num:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=min_k_num)
    obv_seq = np.array([x.cache[cache_key] for x in bars], dtype=np.float64)
    obvm = ta.EMA(obv_seq, n)
    sig_ = ta.EMA(obvm, m)

    if obvm[-1] > sig_[-1] and obvm[-max_overlap] < sig_[-max_overlap]:
        v1 = "看多"
    elif obvm[-1] < sig_[-1] and obvm[-max_overlap] > sig_[-max_overlap]:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cvolp_up_dw_line_V230612(c: CZSC, **kwargs) -> OrderedDict:
    """CVOLP动量变化率指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612"

    **信号逻辑：**

    成交量移动平均平滑变化率。
    先计算了成交量的N周期指数移动平均线，然后计算了EMAP的M周期前的值，最后计算了CVOLP的值。
    CVOLP 上穿 up 买入，下穿 dw 卖出。

    **信号列表：**

    - Signal('日线_D1N13M21UP5DW5_CVOLP动量变化率V230612_看多_任意_任意_0')
    - Signal('日线_D1N13M21UP5DW5_CVOLP动量变化率V230612_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 取K线数量
        - :param m: 信号预警值
        - :param up: 看多信号预警值
        - :param dw: 看空信号预警值
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 34))
    m = int(kwargs.get("m", 55))
    up = int(kwargs.get("up", 5))
    dw = int(kwargs.get("dw", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612".split('_')

    # 增加一个约束，如果K线数量不足时直接返回
    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n + m) 

    volume = np.array([bar.vol for bar in bars])
    n_weights = np.exp(np.linspace(-1., 0., n))
    n_weights /= n_weights.sum()
    emap = np.convolve(volume, n_weights, mode='full')[:len(volume)]
    emap[:n] = emap[n]
    sroc = (emap - np.roll(emap, m))[-1] / np.roll(emap, m)[-1] 

    if sroc > up / 100:
        v1 = "看多"
    if sroc < -dw / 100:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def ntmdk_V230824(c: CZSC, **kwargs) -> OrderedDict:
    """NTMDK多空指标，贡献者：琅盎  

    参数模板："{freq}_D{di}M{m}_NTMDK多空V230824"

    **信号逻辑：**

    此信号函数的逻辑非常简单，流传于股市中有一句话：日日新高日日持股，
    那么此信号函数利用的是收盘价和M日前的收盘价进行比较，如果差值为正
    即多头成立，反之空头成立。

    **信号列表：**

    - Signal('日线_D1M10_NTMDK多空V230824_看空_任意_任意_0')
    - Signal('日线_D1M10_NTMDK多空V230824_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param m: m天前的价格

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    m = int(kwargs.get("m", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}M{m}_NTMDK多空V230824".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + m + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    bars = get_sub_elements(c.bars_raw, di=di, n=m)
    v1 = "看多" if bars[-1].close > bars[0].close else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def kcatr_up_dw_line_V230823(c: CZSC, **kwargs) -> OrderedDict:
    """用ATR波幅构造上下轨，收盘价突破判断多空  贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823"

    **信号逻辑：**

    与布林带类似，都是用价格的移动平均构造中轨，不同的是表示波幅
    的方法，这里用 atr 来作为波幅构造上下轨。价格突破上轨，
    可看成新的上升趋势，买入；价格突破下轨，

    **信号列表：**

    - Signal('日线_D1N30M16T2_KCATR多空V230823_看多_任意_任意_0')
    - Signal('日线_D1N30M16T2_KCATR多空V230823_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数进行ATR计算，默认为30
        - :param m: 获取K线的根数进行均价计算，默认为16
        - :param th: 突破ATR的倍数，默认为2

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 16))
    th = int(kwargs.get("th", 2))  # 突破ATR的倍数

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + max(m, n) + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)
    atr = np.mean([
        max(
            abs(n_bars[i].high - n_bars[i].low),
            abs(n_bars[i].high - n_bars[i - 1].close),
            abs(n_bars[i].low - n_bars[i - 1].close),
        )
        for i in range(1, len(n_bars))
    ])
    middle = np.mean([x.close for x in m_bars])

    if m_bars[-1].close > middle + atr * th:
        v1 = "看多"
    elif m_bars[-1].close < middle - atr * th:
        v1 = "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
