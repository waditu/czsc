# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/10 23:14
describe: coo 是 cooperation 的缩写，作为前缀代表信号开源协作成员贡献的信号
"""
import numpy as np
from deprecated import deprecated
from collections import OrderedDict
from czsc import CZSC
from czsc.utils import create_single_signal, get_sub_elements
from czsc.signals.tas import update_ma_cache, update_sar_cache, update_kdj_cache, update_cci_cache


def __cal_td_seq(close: np.ndarray):
    """TDSEQ计算辅助函数

    正值表示上涨，负值表示下跌

    :param close: np.array
        收盘价序列
    :return: np.array
    """
    if len(close) < 5:
        return np.zeros(len(close), dtype=np.int32)

    res = np.zeros(len(close), dtype=np.int32)
    for i in range(4, len(close)):
        if close[i] > close[i - 4]:
            res[i] = res[i - 1] + 1
        elif close[i] < close[i - 4]:
            res[i] = res[i - 1] - 1

    return res


@deprecated(version='1.0.0', reason="请使用 coo_td_V221111")
def coo_td_V221110(c: CZSC, **kwargs) -> OrderedDict:
    """获取倒数第i根K线的TD信号

    参数模板："{freq}_D{di}K_TD"

    **信号列表：**

    - Signal('60分钟_D2K_TD_延续_非底_任意_0')
    - Signal('60分钟_D2K_TD_延续_非顶_任意_0')
    - Signal('60分钟_D2K_TD_延续_TD顶_任意_0')
    - Signal('60分钟_D2K_TD_看空_非底_任意_0')
    - Signal('60分钟_D2K_TD_延续_TD底_任意_0')
    - Signal('60分钟_D2K_TD_看多_非顶_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :return: s
    """
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}K_TD".split("_")

    if di == 1:
        close = np.array([x.close for x in c.bars_raw[-50:]])
    else:
        close = np.array([x.close for x in c.bars_raw[-50 - di + 1 : -di + 1]])

    td = __cal_td_seq(close)
    if td[-1] > 0:
        v1 = '看多' if len(td) > 1 and td[-2] < -8 else '延续'
        v2 = 'TD顶' if td[-1] > 8 else '非顶'
    elif td[-1] < 0:
        v1 = '看空' if len(td) > 1 and td[-2] > 8 else '延续'
        v2 = 'TD底' if td[-1] < -8 else '非底'
    else:
        v1 = '其他'
        v2 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def coo_td_V221111(c: CZSC, **kwargs) -> OrderedDict:
    """获取倒数第i根K线的TD信号

    参数模板："{freq}_D{di}TD_BS辅助V221111"

    **信号逻辑：**

    神奇九转指标

    **信号列表：**

    - Signal('15分钟_D1TD_BS辅助V221111_延续_TD底_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_看多_非顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_非顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_非底_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_TD顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_看空_非底_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :return: s
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}TD_BS辅助V221111".split("_")
    if len(c.bars_raw) < 50 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    bars = get_sub_elements(c.bars_raw, di=di, n=50)
    close = np.array([x.close for x in bars])
    td = __cal_td_seq(close)

    if td[-1] > 0:
        v1 = '看多' if len(td) > 1 and td[-2] < -8 else '延续'
        v2 = 'TD顶' if td[-1] > 8 else '非顶'
    elif td[-1] < 0:
        v1 = '看空' if len(td) > 1 and td[-2] > 8 else '延续'
        v2 = 'TD底' if td[-1] < -8 else '非底'
    else:
        v1 = '其他'
        v2 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def coo_cci_V230323(c: CZSC, **kwargs) -> OrderedDict:
    """CCI结合均线的多空信号

    参数模板："{freq}_D{di}CCI{n}#{ma_type}#{m}_BS辅助V230323"

     **信号逻辑：**

    1. CCI大于100，且向上突破均线，看多；
    2. CCI小于-100，且向下突破均线，看空；

    **信号列表：**

    - Signal('15分钟_D1CCI20#SMA#5_BS辅助V230323_空头_向下_任意_0')
    - Signal('15分钟_D1CCI20#SMA#5_BS辅助V230323_空头_向上_任意_0')
    - Signal('15分钟_D1CCI20#SMA#5_BS辅助V230323_多头_向上_任意_0')
    - Signal('15分钟_D1CCI20#SMA#5_BS辅助V230323_多头_向下_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: CCI的计算周期
        - :param m: 乘以N表示均线的计算周期
    :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 20))
    m = int(kwargs.get("m", 5))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    freq = c.freq.value
    cache_key_cci = update_cci_cache(c, timeperiod=n)
    cache_key_ma = update_ma_cache(c, ma_type=ma_type, timeperiod=n * m)

    k1, k2, k3 = f"{freq}_D{di}CCI{n}#{ma_type}#{m}_BS辅助V230323".split('_')
    v1 = '其他'
    if len(c.bars_raw) < n * m + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=2)
    cci = bars[-1].cache[cache_key_cci]
    MA_CC = bars[-1].cache[cache_key_ma]

    if cci > 100 and bars[-1].close > MA_CC:
        v1 = '多头'

    if cci < -100 and bars[-1].close < MA_CC:
        v1 = '空头'

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    v2 = "向上" if cci >= bars[-2].cache[cache_key_cci] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def coo_kdj_V230322(c: CZSC, **kwargs) -> OrderedDict:
    """均线判定方向，KD决定进场时机

    参数模板："{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322"

     **信号逻辑：**

     1. K线向上突破均线，且 K < D，看多；
     2. K线向下突破均线，且 K > D，看空；

     **信号列表：**

    - Signal('15分钟_D1KDJ9#3#3#EMA#20_BS辅助V230322_空头_任意_任意_0')
    - Signal('15分钟_D1KDJ9#3#3#EMA#20_BS辅助V230322_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 均线计算周期
        - :param fastk_period:  kdj参数
        - :param slowk_period:  kdj参数
        - :param slowd_period:  kdj参数
     :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 3))
    ma_type = kwargs.get('ma_type', 'EMA').upper()
    fastk_period = int(kwargs.get('fastk_period', 9))
    slowk_period = int(kwargs.get('slowk_period', 3))
    slowd_period = int(kwargs.get('slowd_period', 3))

    ma = update_ma_cache(c, ma_type=ma_type, timeperiod=n)
    cache_key = update_kdj_cache(c, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322".split('_')
    if len(c.bars_raw) < fastk_period * slowk_period + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    kdj, mac = _bars[-1].cache[cache_key], _bars[-1].cache[ma]

    if _bars[-1].close > mac and kdj['k'] < kdj['d']:
        v1 = "多头"
    elif _bars[-1].close < mac and kdj['k'] > kdj['d']:
        v1 = "空头"
    else:
        v1 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def coo_sar_V230325(c: CZSC, **kwargs) -> OrderedDict:
    """SAR和高低点结合判断买卖时机

    参数模板："{freq}_D{di}N{n}SAR_BS辅助V230325"

     **信号逻辑：**

     1. 最高价大于N个周期收盘价的最高价，收盘价在SAR上方，看多；
     2. 最低价小于N个周期收盘价的最低价，收盘价在SAR下方，看空；

     **信号列表：**

    - Signal('15分钟_D1N20SAR_BS辅助V230325_空头_任意_任意_0')
    - Signal('15分钟_D1N20SAR_BS辅助V230325_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 信号计算的K线数量
     :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 60))
    cache_key = update_sar_cache(c)

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}SAR_BS辅助V230325".split('_')
    v1 = "其他"
    if len(c.bars_raw) < n + di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    hhv = max([x.close for x in _bars])
    llv = min([x.close for x in _bars])
    sar, close = _bars[-1].cache[cache_key], _bars[-1].close

    if close > sar and _bars[-1].high >= hhv:
        v1 = "多头"
    if close < sar and _bars[-1].low <= llv:
        v1 = "空头"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
