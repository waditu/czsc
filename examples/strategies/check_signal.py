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

def jcc_ta_xing_221124(c: CZSC, di: int = 1) -> OrderedDict:
    """塔形顶底

    **信号逻辑：**

    1. 首尾两根K线的实体最大
    2. 首k上涨，尾K下跌，且中间高点相近，且低点大于首尾低点的较大者，塔形顶部；反之，底部。

    **信号列表：**

    - Signal('15分钟_D1K_塔形_顶部_6K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_9K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_7K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_5K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_5K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_8K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_6K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_7K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_8K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_9K_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 识别结果
    """
    def __check_ta_xing(bars: List[RawBar]):
        if len(bars) < 5:
            return "其他"

        rb, lb = bars[0], bars[-1]
        sorted_solid = sorted([x.solid for x in bars])
        if min(rb.solid, lb.solid) >= sorted_solid[-2]:

            g_c1 = rb.close > rb.open and lb.close < lb.open
            g_c2 = np.var([x.high for x in bars[1: -1]]) < 0.5
            g_c3 = all(x.low > max(rb.open, lb.close) for x in bars[1: -1])
            if g_c1 and g_c2 and g_c3:
                return "顶部"

            d_c1 = rb.close < rb.open and lb.close > lb.open
            d_c2 = np.var([x.low for x in bars[1: -1]]) < 0.5
            d_c3 = all(x.high < min(rb.open, lb.close) for x in bars[1: -1])
            if d_c1 and d_c2 and d_c3:
                return "底部"

        return "其他"

    k1, k2, k3 = f"{c.freq.value}_D{di}K_塔形".split("_")

    for n in (5, 6, 7, 8, 9):
        _bars = get_sub_elements(c.bars_raw, di=di, n=n)
        v1 = __check_ta_xing(_bars)
        if v1 != "其他":
            v2 = f"{n}K"
            break
        else:
            v2 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
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
        s.update(jcc_ta_xing_221124(cat.kas['15分钟'], di=1))
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
