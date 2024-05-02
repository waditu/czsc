"""
此文件为信号函数集合模块，初步探索
describe: 基于DKX多线指标的信号函数集合
dkx = ‘多空线’
"""


import inspect
import pandas as pd
import numpy as np

import czsc.connectors.qmt_connector as qn
import czsc.utils as utils
from czsc.analyze import CZSC
from datetime import date, timedelta


from collections import OrderedDict
from deprecated import deprecated
from czsc.analyze import CZSC
from czsc.objects import Signal, Direction, BI, RawBar, FX, Mark, ZS
from czsc.traders.base import CzscSignals
from czsc.utils import get_sub_elements, fast_slow_cross, count_last_same, create_single_signal, single_linear
from czsc.utils.sig import cross_zero_axis, cal_cross_num, down_cross_count



import os
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc.traders.base import CzscTrader, check_signals_acc

from czsc.utils.ta import DKX

def update_dkx_cache(c: CZSC, **kwargs):
    """
    计算DKX指标，分别为DKX，MAKDX、DEX，以字典形式写入Bar的cache中，以便用以生成基于DKX的型号使用。
    数据格式如下；

    {'DKX': {'DKX': 299.46192857142853, 'MADKX': 293.16664761904764, 'DEX': 6.295280952380892}}

    :param c: CZSC对象
    :return: cache_key 'DKX'
    """
    cache_key = "DKX"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key
    close = np.array([x.close for x in c.bars_raw])
    low = np.array([x.low for x in c.bars_raw])
    open = np.array([x.open for x in c.bars_raw])
    high = np.array([x.high for x in c.bars_raw])
    dkx, madkx, dex = DKX(close,low,open,high)
    for i in range(len(close)):
        _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
        dkx_i = dkx[i] if not np.isnan(dkx[i]) else None
        _c.update({cache_key: {'DKX':dkx_i,'MADKX':madkx[i],'DEX':dex[i]}})
        c.bars_raw[i].cache = _c
    return cache_key

def dkx_base_V240427(c: CZSC, **kwargs) -> OrderedDict:
    """DKX|DEX多空和方向信号

    参数模板："{freq}_D{di}DKX#{key}_V240427"

    **信号逻辑：**

    1.DKX 的DEX值大于0 向上；反之，向下

    **信号列表：**

    - Signal('30分钟_D1DKX#DEX_V240427_多头_向上_任意_0')
    - Signal('30分钟_D1DKX#DEX_V240427_其他_向上_任意_0')
    - Signal('30分钟_D1DKX#DEX_V240427_空头_向下_任意_0')
    - Signal('30分钟_D1DKX#DEX_V240427_其他_向下_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 {'DKX':{'DEX':}}
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'DEX').upper()


    cache_key = update_dkx_cache(c, **kwargs)

    k1, k2, k3 = f"{c.freq.value}_D{di}DKX#{key}_V240427".split('_')
    #v1 = "任意"
    dkx = [x.cache[cache_key][key] for x in c.bars_raw[-5 - di :]]
    #print(dkx)
    v1 = "多头" if dkx[-di] >= 0 and dkx[-di-1] < 0 else "空头" if dkx[-di] < 0 and dkx[-di-1] >= 0 else "其他"
    v2 = "向上" if dkx[-di] >= 0 else "向下"
    

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1,v2=v2)

def dkx_direction_V220428(c: CZSC, **kwargs) -> OrderedDict:
    """
    DKX|DEX多空和方向信号

    参数模板："{freq}_D{di}T{t1}#{t2}_V240428"

    **信号逻辑：**

    1. 如果close连续大于MADKX3根，则v1="买点"，否则为任意
    2. 如果close连续小于MADKX3根，则v1="卖点"，否则为任意
    3. DKX 的DEX值大于0 向上；反之，向下

    **信号列表：**
    - Signal('30分钟_D1T3#3_V240428_买点_任意_任意_0')
    - Signal('30分钟_D1T3#3_V240428_卖点_任意_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 {'DKX':{'DEX':}}
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'DEX').upper()
    t1 = int(kwargs.get('t1', 3))
    t2 = int(kwargs.get('t2', 3))

    cache_key = update_dkx_cache(c, **kwargs)

    k1, k2, k3 = f"{c.freq.value}_D{di}T{t1}#{t2}_V240428".split('_')

    dkx = [x.cache[cache_key][key] for x in c.bars_raw[-5 - di :]]
    close_prices = [x.close for x in c.bars_raw[-5 - di :]]
    madkx = [x.cache[cache_key]['MADKX'] for x in c.bars_raw[-5 - di :]]
    v1=""
    buy_counter = 0
    sell_counter = 0
    # 新的v1逻辑
    if (close_prices[-1] > madkx[-1] and close_prices[-2] > madkx[-2]) and close_prices[-3] < madkx[-3]:
        v1 = "买点"
    elif (close_prices[-1] < madkx[-1] and close_prices[-2] < madkx[-2]) and close_prices[-3] > madkx[-3]:
        v1 = "卖点"
    else:
        v1 = '其他'


    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    """DKX|DEX多空和方向信号

    参数模板："{freq}_D{di}DKX##{key}_BS辅助V240427"

    **信号逻辑：**

    1. 如果close连续等于MADKX3根，则v1="买点"，否则为任意
    2. 如果close连续等于MADKX3根，则v1="卖点"，否则为任意
    3. DKX 的DEX值大于0 向上；反之，向下

    **信号列表：**
    
    - Signal('30分钟_D1CUPD#DEX_BS辅助V240427_卖点_任意_任意_0')
    - Signal('30分钟_D1CUPD#DEX_BS辅助V240427_买点_任意_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 {'DKX':{'DEX':}}
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'DEX').upper()

    cache_key = update_dkx_cache(c, **kwargs)

    k1, k2, k3 = f"{c.freq.value}_D{di}CUPD#{key}_BS辅助V240427".split('_')

    dkx = [x.cache[cache_key][key] for x in c.bars_raw[-5 - di :]]
    close_prices = [x.close for x in c.bars_raw[-5 - di :]]
    madkx = [x.cache[cache_key]['MADKX'] for x in c.bars_raw[-5 - di :]]
    v1=""
    # 新的v1逻辑
    if (close_prices[-1] > madkx[-1] and close_prices[-2] > madkx[-2]) and close_prices[-3] < madkx[-3]:
        v1 = "买点"
    elif (close_prices[-1] < madkx[-1] and close_prices[-2] < madkx[-2]) and close_prices[-3] > madkx[-3]:
        v1 = "卖点"
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

#生成信号列表函数增加进来
def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    #symbols = research.get_symbols('中证500成分股')
    #bars = research.get_raw_bars(['600100'], '30分钟', '20220101', '20221231', fq='前复权')
    bars = qn.get_raw_bars('600100.SH', '30分钟', '20230101', '20240426', fq='不复权')
    signals_config = [{'name': dkx_base_V240427, 'freq': "30分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0)  # type: ignore

def print_data(bars):
    c=CZSC(bars)
    update_dkx_cache(c)
    print(c)
    print(c.bars_raw[-1].cache)

if __name__ == '__main__':
    check()


