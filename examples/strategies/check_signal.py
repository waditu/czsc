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
def jcc_yun_xian_trend(c: CZSC, di=1) -> OrderedDict:
    """孕线形态
    二日K线模式，分多头孕线与空头孕线，两者相反，以多头孕线为例，
    在下跌趋势中，第一日K线长阴，第二日开盘和收盘价都在第一日价格
    振幅之内，为阳线，预示趋势反转，股价上升

    有效信号列表：
    * Signal('15分钟_D1_孕线_满足_多头_任意_0')
    * Signal('15分钟_D1_孕线_满足_空头_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 孕线识别结果
    """

    k1, k2, k3 = f"{c.freq.value}_D{di}_孕线".split('_')

    bars = c.bars_raw[0:-di]
    bars = pd.DataFrame([[x.open, x.high, x.low, x.close] for x in bars], columns=['open', 'high', 'low', 'close'])
    # 判断：1、val为100，多头孕线；2、val为100，空头孕线；3、val为0，不满足趋势孕线形态；
    val = ta.CDLHARAMI(bars.open, bars.high, bars.low, bars.close)
    v1, v2 = "其他", "其他"
    if val.iloc[-1] == 100:
        v1, v2 = "满足", "多头"
    elif val.iloc[-1] == -100:
        v1, v2 = "满足", "空头"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_yun_xian_V221118(c: CZSC, di=1) -> OrderedDict:
    """孕线形态

    二日K线模式，分多头孕线与空头孕线，两者相反，以多头孕线为例，
    在下跌趋势中，第一日K线长阴，第二日开盘和收盘价都在第一日价格
    振幅之内，为阳线，预示趋势反转，股价上升

    **有效信号列表：**

    - Signal('60分钟_D1_孕线_看空_任意_任意_0')
    - Signal('60分钟_D1_孕线_看多_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 孕线识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}_孕线".split('_')
    bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)

    v1 = "其他"
    if bar2.solid > max(bar2.upper, bar2.lower) and bar1.solid < max(bar1.upper, bar1.lower):
        if bar2.close > bar1.close > bar2.open and bar2.close > bar1.open > bar2.open:
            v1 = "看空"

        if bar2.close < bar1.close < bar2.open and bar2.close < bar1.open < bar2.open:
            v1 = "看多"

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
        s.update(jcc_yun_xian_V221118(cat.kas['60分钟'], di=1))
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
