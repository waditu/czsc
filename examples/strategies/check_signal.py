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
from typing import List
from loguru import logger
from czsc import CZSC, signals, RawBar, Direction
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements, single_linear
from czsc.objects import Freq, Operate, Signal, Factor, Event
from czsc.traders import CzscAdvancedTrader


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------

def check_szx(bar: RawBar, th: int = 10) -> bool:
    """判断十字线

    :param bar:
    :param th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return:
    """
    if bar.close == bar.open and bar.high != bar.low:
        return True

    if bar.close != bar.open and (bar.high - bar.low) / abs(bar.close - bar.open) > th:
        return True
    else:
        return False


def jcc_san_szx_V221122(c: CZSC, di: int = 1, th: int = 10) -> OrderedDict:
    """三星形态

    **信号逻辑：**

    1. 最近五根K线中出现三个十字星

    **信号列表：**

    - Signal('15分钟_D1T10_三星_满足_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return: 识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}_三星".split("_")
    v1 = "其他"
    if len(c.bars_raw) > 6 + di:
        bars = get_sub_elements(c.bars_raw, di, n=5)
        if sum([check_szx(bar, th) for bar in bars]) >= 3:
            v1 = "满足"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        # signals.update_macd_cache(cat.kas['60分钟'])
        # logger.info('\n\n')
        s.update(jcc_san_szx_V221122(cat.kas['15分钟'], di=1))
        return s

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,
    }
    return tactic


# 定义命令行接口【信号检查】的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"D:\ts_data")

# 信号检查参数设置【可选】
# check_params = {
#     "symbol": "000001.SZ#E",    # 交易品种，格式为 {ts_code}#{asset}
#     "sdt": "20180101",          # 开始时间
#     "edt": "20220101",          # 结束时间
# }


check_params = {
    "symbol": "300001.SZ#E",  # 交易品种，格式为 {ts_code}#{asset}
    "sdt": "20150101",  # 开始时间
    "edt": "20220101",  # 结束时间
}
