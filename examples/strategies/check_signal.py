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

def jcc_gap_yin_yang_V221121(c: CZSC, di=1) -> OrderedDict:
    """跳空与并列阴阳形态 贡献者：平凡

    **向上跳空并列阴阳（向下反之）：**

    1. 其中一根白色蜡烛线和一根黑色蜡烛线共同形成了一个向上的窗口。
    2. 这根黑色蜡烛线的开市价位于前一个白色实体之内，收市价位于前一个白色实体之下。
    3. 在这样的情况下，这根黑色蜡烛线的收市价，需要在窗口之上。
    4. 黑白两根K线的实体相差不大

    **有效信号列表：**

    - Signal('15分钟_D1K_并列阴阳_向上跳空_任意_任意_0')
    - Signal('15分钟_D1K_并列阴阳_向下跳空_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 捉腰带线识别结果
    """

    k1, k2, k3 = f"{c.freq.value}_D{di}K_并列阴阳".split('_')

    v1 = "其他"
    if len(c.bars_raw) > di + 5:
        bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)

        if min(bar1.low, bar2.low) > bar3.high \
                and bar2.close > bar2.open \
                and bar1.close < bar1.open \
                and np.var((bar1.solid, bar2.solid)) < 0.2:
            v1 = "向上跳空"

        elif max(bar1.high, bar2.high) < bar3.low \
                and bar2.close < bar2.open \
                and bar1.close > bar1.open \
                and np.var((bar1.solid, bar2.solid)) < 0.2:
            v1 = "向下跳空"

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
        s.update(jcc_gap_yin_yang_V221121(cat.kas['15分钟'], di=1))
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
