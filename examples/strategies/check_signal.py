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

def bar_zdt_V221111(cat: CzscAdvancedTrader, freq: str, di: int = 1) -> OrderedDict:
    """更精确地倒数第1根K线的涨跌停计算

    **信号逻辑：** close等于high，且相比昨天收盘价涨幅大于9%，就是涨停；反之，跌停。

    **信号列表：**

    - Signal('15分钟_D2K_涨跌停_跌停_任意_任意_0')
    - Signal('15分钟_D2K_涨跌停_涨停_任意_任意_0')

    :param cat: CzscAdvancedTrader
    :param freq: K线周期
    :param di: 计算截止倒数第 di 根 K 线
    :return: s
    """
    cache_key = f"{freq}_D{di}K_ZDT"
    zdt_cache = cat.cache.get(cache_key, {})
    bars = get_sub_elements(cat.kas[freq].bars_raw, di=di, n=300)
    last_bar = bars[-1]
    today = last_bar.dt.date()

    if not zdt_cache:
        yesterday_last = [x for x in bars if x.dt.date() != today][-1]
        zdt_cache['昨日'] = yesterday_last.dt.date()
        zdt_cache['昨收'] = yesterday_last.close

    else:
        if today != zdt_cache['今日']:
            # 新的一天，全部刷新
            zdt_cache['昨日'] = zdt_cache['今日']
            zdt_cache['昨收'] = zdt_cache['今收']

    zdt_cache['今日'] = last_bar.dt.date()
    zdt_cache['今收'] = last_bar.close
    zdt_cache['update_dt'] = last_bar.dt
    cat.cache[cache_key] = zdt_cache

    k1, k2, k3 = freq, f"D{di}K", "涨跌停"
    if last_bar.close == last_bar.high > zdt_cache['昨收'] * 1.09:
        v1 = "涨停"
    elif last_bar.close == last_bar.low < zdt_cache['昨收'] * 0.91:
        v1 = "跌停"
    else:
        v1 = "其他"

    s = OrderedDict()
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        signals.update_macd_cache(cat.kas['60分钟'])
        # logger.info('\n\n')
        s.update(bar_zdt_V221111(cat, '日线', di=1))
        s.update(bar_zdt_V221111(cat, '日线', di=2))
        s.update(bar_zdt_V221111(cat, '日线', di=3))
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
