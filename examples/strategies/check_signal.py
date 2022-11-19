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

def jcc_szx_V221111(c: CZSC, di: int = 1, th: int = 10) -> OrderedDict:
    """十字线

    **信号逻辑：**

    1， 十字线定义，(h -l) / (c - o) 的绝对值大于 th，或 c == o
    2. 长腿十字线，上下影线都很长；墓碑十字线，上影线很长；蜻蜓十字线，下影线很长；

    **信号列表：**

    - Signal('60分钟_D1TH10_十字线_蜻蜓十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_蜻蜓十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_墓碑十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_长腿十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_墓碑十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_长腿十字线_北方_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return: 十字线识别结果
    """

    def __check_szx(bar: RawBar, th: int) -> bool:
        if bar.close == bar.open and bar.high != bar.low:
            return True

        if bar.close != bar.open and (bar.high - bar.low) / abs(bar.close - bar.open) > th:
            return True
        else:
            return False

    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_十字线".split("_")
    if len(c.bars_raw) < di + 10:
        v1 = "其他"
        v2 = "其他"
    else:
        bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)
        if __check_szx(bar1, th):
            upper = bar1.upper
            solid = bar1.solid
            lower = bar1.lower

            if lower > upper * 2:
                v1 = "蜻蜓十字线"
            elif lower == 0 or lower < solid:
                v1 = "墓碑十字线"
            elif lower > bar2.solid and upper > bar2.solid:
                v1 = "长腿十字线"
            else:
                v1 = "十字线"
        else:
            v1 = "其他"

        v2 = "北方" if bar2.close > bar2.open and bar2.solid > (bar2.upper + bar2.lower) * 3 else "任意"

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
        s.update(jcc_szx_V221111(cat.kas['60分钟'], di=1))
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
