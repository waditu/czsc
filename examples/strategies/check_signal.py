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
def jcc_three_soldiers_V221030(c: CZSC, di=1, th=1, ri=0.2) -> OrderedDict:
    """白三兵，贡献者：鲁克林

    **信号逻辑：**

    1. 三根K线均收盘价 > 开盘价；且开盘价越来越高； 且收盘价越来越高；
    2. 三根K线的开盘价都在前一根K线的实体范围之间
    3. 倒1K上影线与倒1K实体的比值th_cal小于th
    4. 倒1K涨幅与倒2K涨幅的比值ri_cal大于ri

    **信号列表：**

    - Signal('60分钟_D1T100R20_白三兵_满足_挺进_任意_0')
    - Signal('60分钟_D1T100R20_白三兵_满足_受阻_任意_0')
    - Signal('60分钟_D1T100R20_白三兵_满足_停顿_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线 取倒数三根k线
    :param th: 可调阈值，倒1K上影线与倒1K实体的比值，保留两位小数
    :param ri: 可调阈值，倒1K涨幅与倒2K涨幅的比值，保留两位小数
    :return: 白三兵识别结果
    """
    # th = 倒1K上涨阻力； ri = 倒1K相对涨幅；
    th = int(th * 100)
    ri = int(ri * 100)

    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}R{ri}_白三兵".split('_')

    # 先后顺序 bar3 <-- bar2 <-- bar1
    bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)

    if bar3.open < bar3.close and bar2.open < bar2.close \
            and bar1.close > bar1.open > bar2.open > bar3.open \
            and bar1.close > bar2.close > bar3.close:
        v1 = "满足"
        th_cal = (bar1.high - bar1.close) / (bar1.close - bar1.open) * 100
        ri_cal = (bar1.close - bar2.close) / (bar2.close - bar3.close) * 100

        if ri_cal > ri:
            if th_cal < th:
                v2 = "挺进"
            else:
                v2 = "受阻"
        else:
            v2 = "停顿"
    else:
        v1 = "其他"
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
        s.update(jcc_three_soldiers_V221030(cat.kas['60分钟'], di=1))
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
