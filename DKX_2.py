# -*- coding: utf-8 -*-
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

    参数模板："{freq}_D{di}DKX#{key}_BS辅助V240427"

    **信号逻辑：**

    1.DXK》0 看多，反之，看空
    2.DKX 的DEX值大于前一日DEX 向上；反之，向下

    **信号列表：**

    - Signal('日线_D1DKX#DEX_BS辅助V240427_多头_向上_任意_0')
    - Signal('日线_D1DKX#DEX_BS辅助V240427_多头_向下_任意_0')
    - Signal('日线_D1DKX#DEX_BS辅助V240427_空头_向下_任意_0')
    - Signal('日线_D1DKX#DEX_BS辅助V240427_空头_向上_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 {'DKX':{'DEX':}}
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'DEX').upper()


    cache_key = update_dkx_cache(c, **kwargs)

    k1, k2, k3 = f"{c.freq.value}_D{di}DKX#{key}_BS辅助V240427".split('_')

    dkx = [x.cache[cache_key][key] for x in c.bars_raw[-5 - di :]]

    v1 = "多头" if dkx[-di] >= 0 else "空头"
    v2 = "向上" if dkx[-di] >=dkx[-di - 1] else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1,v2=v2)
    


'''

if __name__ == "__main__":
    # 获取股票代码为 '000001.SZ' 的 K 线数据
    df_kline = qn.get_raw_bars(symbol='688188.SH',freq='日线',sdt='20231101',edt='20240425',fq='前复权')
    #df_k = qn.get_kline(symbol='688188.SH',period='1d',count=300,start_time='20231101',end_time='20240426')
    #data = DKX(df_k,tag='1d')
    #print(df_kline)
    sc = CZSC(bars=df_kline,max_bi_num=4)
    print(sc.fx_list)
 
    update_dkx_cache(sc)

    print('--------------------------------------------------------')

    print('DEX:',sc.bars_raw[-4].cache['DKX']['DEX'])
    print('DKX:',sc.bars_raw[-4].cache['DKX'])

    print('--------------------------------------------------------')
    sig = dkx_base_V240427(sc) 
    print('sig:',sig)


    

    #sc = CZSC(df_kline)
    #print(sc.fx_list[--30])
    #print(df_k)
'''


'''使用标准信号检测方法检测'''



if __name__ == '__main__':
    bars = qn.get_raw_bars(symbol='688188.SH',freq='日线',sdt='20201101',edt='20240425',fq='前复权')
    signals_config = [{'name': dkx_base_V240427, 'freq': "日线"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


    # 也可以指定信号的K线周期，比如只检查日线信号
    # check_signals_acc(bars, get_signals, freqs=['日线'])

