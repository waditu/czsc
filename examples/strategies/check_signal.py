# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
import talib as ta
import pandas as pd
from collections import OrderedDict
from typing import List
from loguru import logger
from czsc import CZSC, signals, RawBar
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements
from czsc.objects import Freq, Operate, Signal, Factor, Event
from czsc.traders import CzscAdvancedTrader


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------

def bar_accelerate_V221118(c: CZSC, di: int = 1, window: int = 13, ma1='SMA10') -> OrderedDict:
    """辨别加速走势

    **信号逻辑：**

    上涨加速指窗口内K线收盘价全部大于 ma1，且 close 与 ma1 的距离不断正向放大；反之为下跌加速。

    **信号列表：**

    - Signal('60分钟_D1W13_SMA10加速_上涨_任意_任意_0')
    - Signal('60分钟_D1W13_SMA10加速_下跌_任意_任意_0')

    **注意事项：**

    此信号函数必须与 `czsc.signals.update_ma_cache` 结合使用，需要该函数更新MA缓存

    :param c: CZSC对象
    :param di: 取近n根K线为截止
    :param ma1: 快线
    :param window: 识别加速走势的窗口大小
    :return: 信号识别结果
    """
    assert window > 3, "辨别加速，至少需要3根以上K线"
    s = OrderedDict()
    k1, k2, k3 = c.freq.value, f"D{di}W{window}", f"{ma1}加速"

    bars = get_sub_elements(c.bars_raw, di=di, n=window)
    delta = [x.close - x.cache[ma1] for x in bars]

    if all(x > 0 for x in delta) and delta[-1] > delta[-2] > delta[-3]:
        v1 = "上涨"
    elif all(x < 0 for x in delta) and delta[-1] < delta[-2] < delta[-3]:
        v1 = "下跌"
    else:
        v1 = "其他"

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        signals.update_ma_cache(cat.kas['60分钟'], ma_type='SMA', timeperiod=10)
        s.update(bar_accelerate_V221118(cat.kas['60分钟'], di=1, window=13, ma1='SMA10'))
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
