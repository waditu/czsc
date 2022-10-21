# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:52
describe: ThsConceptsSensor 策略定义
"""
import os
from collections import OrderedDict
from czsc import signals, CzscAdvancedTrader
from czsc.sensors.plates import TsDataCache
from czsc.objects import Freq, Signal, Factor, Event, Operate


def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    for _, c in cat.kas.items():
        if c.freq == Freq.D:
            s.update(signals.ta.get_s_sma(c, di=1, t_seq=(5, 20, 120)))
    return s


def get_event():
    event = Event(name="SMA_V2", operate=Operate.LO, factors=[
        Factor(name="日超强", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='SMA20多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA20方向', v1='向上'),
            Signal(k1='日线', k2='倒1K', k3='SMA120方向', v1='向上'),
        ]),
    ])
    return event


mode = "backtest"
if mode == "backtest":
    data_path = r"C:\ts_data_czsc"
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-03-23')
    sdt = "20180101"
    edt = "20211114"
    results_path = os.path.join(data_path, f"ths_concepts_{get_event().name}_{sdt}_{edt}")
elif mode == "realtime":
    data_path = r"C:\ts_data_czsc"
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-03-23')
    sdt = "20180101"
    edt = "20211114"
    results_path = os.path.join(data_path, f"ths_concepts_{get_event().name}_{sdt}_{edt}")
