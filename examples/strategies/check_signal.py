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
def jcc_zhuo_yao_dai_xian_v221113(c: CZSC, di: int = 1, left: int = 20) -> OrderedDict:
    """捉腰带线

    **捉腰带线判别标准：**

    捉腰带形态是由单独一根蜡烛线构成的。看涨捉腰带形态是一 根坚挺的白色蜡烛线，其开市价位于时段的最低点
    （或者，这根蜡烛线只有极短的下影线），然后市场一路上扬，收市价位于或接近本时段的最高

    **有效信号列表：**

    - Signal('60分钟_D1L20_捉腰带线_看跌_光头阴线_任意_0')
    - Signal('60分钟_D1L20_捉腰带线_看多_光脚阳线_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param left: 从di向左数left根K线
    :return: 捉腰带线识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}L{left}_捉腰带线".split('_')
    v1, v2 = "其他", "其他"

    bar: RawBar = c.bars_raw[-di]
    # x1 - 上影线大小；x2 - 实体大小；x3 - 下影线大小
    x1, x2, x3 = bar.high - max(bar.open, bar.close), abs(bar.close - bar.open), min(bar.open, bar.close) - bar.low

    if len(c.bars_raw) > left + di:
        left_bars: List[RawBar] = c.bars_raw[-left - di:-di]
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])

        if bar.low < left_min:
            if bar.close > bar.open and x3 == 0:
                v1 = "看多"
                v2 = "光脚阳线"
        elif bar.high > left_max:
            if bar.close < bar.open and x1 == 0:
                v1 = "看跌"
                v2 = "光头阴线"

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
        s.update(jcc_zhuo_yao_dai_xian_v221113(cat.kas['60分钟'], di=1))
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
