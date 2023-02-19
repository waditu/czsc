# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
import talib as ta
import numpy as np
import pandas as pd
from collections import OrderedDict
from typing import List, Union, Tuple
from loguru import logger
from czsc import CZSC, signals, RawBar, Direction
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements, single_linear, fast_slow_cross, same_dir_counts
from czsc.objects import Freq, Operate, Signal, Factor, Event, BI
from czsc.traders import CzscSignals


def count_last_same(seq: Union[List, np.array, Tuple]):
    """统计与seq列表最后一个元素相似的连续元素数量

    :param seq: 数字序列
    :return:
    """
    s = seq[-1]
    c = 0
    for _s in seq[::-1]:
        if _s == s:
            c += 1
        else:
            break
    return c


# 【必须】定义信号函数 get_signals
# ----------------------------------------------------------------------------------------------------------------------
# def tas_kdj_evc_V221201(c: CZSC, di: int = 1, key='K', th=10, count_range=(5, 8), **kwargs) -> OrderedDict:
#     """KDJ极值计数信号, evc 是 extreme value counts 的首字母缩写
#
#     **信号逻辑：**
#
#      1. K < th，记录一次多头信号，连续出现信号次数在 count_range 范围，则认为是有效多头信号；
#      2. K > 100 - th, 记录一次空头信号，连续出现信号次数在 count_range 范围，则认为是有效空头信号
#
#     **信号列表：**
#
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C5_任意_0')
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C5_任意_0')
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C6_任意_0')
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C7_任意_0')
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C6_任意_0')
#     - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C7_任意_0')
#
#     :param c: CZSC对象
#     :param di: 信号计算截止倒数第i根K线
#     :param key: KDJ 值的名称，可以是 K， D， J
#     :param th: 信号计算截止倒数第i根K线
#     :param count_range: 信号计数范围
#     :return:
#     """
#     cache_key = update_kdj_cache(c, **kwargs)
#     c1, c2 = count_range
#     assert c2 > c1
#     k1, k2, k3 = f"{c.freq.value}_D{di}T{th}{cache_key}_{key.upper()}值突破{c1}#{c2}".split('_')
#     bars = get_sub_elements(c.bars_raw, di=di, n=3+c2)
#
#     v1 = "其他"
#     v2 = "任意"
#     if len(bars) == 3 + c2:
#         key = key.lower()
#         long = [x.cache[cache_key][key] < th for x in bars]
#         short = [x.cache[cache_key][key] > 100 - th for x in bars]
#         lc = count_last_same(long) if long[-1] else 0
#         sc = count_last_same(short) if short[-1] else 0
#
#         if c2 > lc >= c1:
#             v1 = "多头"
#             v2 = f"C{lc}"
#
#         if c2 > sc >= c1:
#             assert v1 == '其他'
#             v1 = "空头"
#             v2 = f"C{sc}"
#
#     s = OrderedDict()
#     signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
#     s[signal.key] = signal.value
#     return s

def get_signals(cat: CzscSignals) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    s.update(signals.tas_kdj_base_V221101(cat.kas['15分钟'], di=1, fastk_period=36))
    return s


# 定义命令行接口【信号检查】的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 信号检查参数设置【可选】
check_params = {
    "symbol": "002642.SZ#E",    # 交易品种，格式为 {ts_code}#{asset}
    "sdt": "20180101",          # 开始时间
    "edt": "20221231",          # 结束时间
}


# 【必须】定义K线数据读取函数，这里是为了方便接入任意数据源的K线行情
# ----------------------------------------------------------------------------------------------------------------------
def read_bars(symbol, sdt='20170101', edt='20221001'):
    """自定义K线数据读取函数，便于接入任意来源的行情数据进行回测一类的分析

    :param symbol: 标的名称
    :param sdt: 行情开始时间
    :param edt: 行情介绍时间
    :return: list of RawBar
    """
    adj = 'hfq'
    freq = '15min'
    ts_code, asset = symbol.split("#")
    # 初始化 Tushare 数据缓存
    dc = TsDataCache(r"D:\ts_data")

    if "min" in freq:
        bars = dc.pro_bar_minutes(ts_code, sdt, edt, freq=freq, asset=asset, adj=adj, raw_bar=True)
    else:
        bars = dc.pro_bar(ts_code, sdt, edt, freq=freq, asset=asset, adj=adj, raw_bar=True)
    return bars

