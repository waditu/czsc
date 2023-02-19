# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:52
describe: ThsConceptsSensor 策略定义
"""
import os
from collections import OrderedDict
from czsc import signals, CzscSignals
from czsc.sensors.plates import TsDataCache
from czsc.objects import Freq, Signal, Factor, Event, Operate


def get_signals(cat: CzscSignals) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    for _, c in cat.kas.items():
        if c.freq == Freq.D:
            s.update(signals.tas_ma_base_V221101(c, di=1, timeperiod=20))
            s.update(signals.tas_ma_base_V221101(c, di=1, timeperiod=120))
    return s


def get_event():
    event = Event(name="SMA", operate=Operate.LO, factors=[
        Factor(name="日超强", signals_all=[
            Signal("日线_D1K_SMA20_多头_向上_任意_0"),
            Signal("日线_D1K_SMA120_任意_向上_任意_0"),
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
