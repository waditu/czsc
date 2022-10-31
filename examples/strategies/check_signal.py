# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
from collections import OrderedDict
from czsc import signals
from czsc.data import TsDataCache, get_symbols
from czsc.objects import Freq, Operate, Signal, Factor, Event
from czsc.traders import CzscAdvancedTrader
from czsc import signals


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------

def trader_strategy(symbol):
    """择时策略"""
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(jcc_zhu_huo_xian_V221027(cat.kas['15分钟'], di=2))
        return s

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,
    }

    return tactic


# 定义命令行接口的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"C:\ts_data_czsc")


# 信号检查参数设置【可选】
check_params = {
    "symbol": "000001.SZ#E",    # 交易品种
    "sdt": "20150101",          # 开始时间
    "edt": "20220101",          # 结束时间
}




