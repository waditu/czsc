# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:21
"""
import os
import pandas as pd
from collections import OrderedDict
from czsc import CzscAdvancedTrader, Freq, signals, Operate, Signal, Factor, Event
from czsc.sensors.stocks import StocksDaySensor, TsDataCache

pd.set_option('mode.chained_assignment', None)


def sds_czsc_v1_t1(symbol):
    """sds_czsc_v1"""
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        for _, c in cat.kas.items():
            if c.freq == Freq.D:
                s.update(signals.ta.get_s_sma(c, di=1, t_seq=(5, 20)))
        return s

    def get_event():
        event = Event(name="SDS_CZSC_V1_T1", operate=Operate.LO, factors=[
            Factor(name="MACD日线长多", signals_all=[
                Signal(k1='日线', k2='倒1K', k3='SMA20多空', v1='多头'),
                Signal(k1='日线', k2='倒1K', k3='SMA20方向', v1='向上'),
            ]),
        ])
        return event

    tactic = {
        "symbol": symbol,
        "base_freq": "日线",
        "freqs": ['周线', '月线'],
        "get_signals": get_signals,
        "get_event": get_event,
    }
    return tactic


if __name__ == '__main__':
    strategy = sds_czsc_v1_t1
    data_path = r"C:\ts_data_czsc"
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-03-23')
    sdt = "20180101"
    edt = "20220320"
    experiment_name = strategy.__doc__
    experiment_path = os.path.join(data_path, experiment_name.upper())
    sss = StocksDaySensor(experiment_path, sdt, edt, dc, strategy, signals_n=0)

    # grid search 执行很慢
    # grid_params = {
    #     "fc_top_n": [10, 15, 20, 30],
    #     "fc_min_n": [1, 2, 3, 4, 5],
    #     "min_total_mv": [8e5, 10e5],
    #     "max_count": [100, 50, 20],
    # }
    # sss.grip_search(grid_params)

    row = {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": None, "max_count": None, 'window_size': 1}
    sss.write_validate_report("原始选股结果", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 20, 'window_size': 1}
    sss.write_validate_report("1日聚合测试20", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 50, 'window_size': 1}
    sss.write_validate_report("1日聚合测试50", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 100, 'window_size': 1}
    sss.write_validate_report("1日聚合测试100", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 50, 'window_size': 8}
    sss.write_validate_report("8日聚合测试", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 50, 'window_size': 1}
    sss.write_validate_report("1日聚合测试", row)
    row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 50, 'window_size': 8}
    sss.write_validate_report("8日聚合测试", row)


