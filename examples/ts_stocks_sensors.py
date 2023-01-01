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
        signals.update_ma_cache(cat.kas['日线'], ma_type='SMA', timeperiod=20)
        s.update(signals.tas_ma_base_V221203(cat.kas['日线'], di=1, key="SMA20"))
        return s

    def get_event():
        event = Event(name="SDS_CZSC_V1_T1", operate=Operate.LO, factors=[
            Factor(name="20日线长多", signals_all=[
                Signal('日线_D1T100_SMA20_多头_向上_远离_0'),
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
    dc = TsDataCache(data_path, sdt='2020-01-01')
    sdt = "20210101"
    edt = "20221218"
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
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 20, 'window_size': 1}
    # sss.write_validate_report("1日聚合测试20", row)
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 50, 'window_size': 1}
    # sss.write_validate_report("1日聚合测试50", row)
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 100, 'window_size': 1}
    # sss.write_validate_report("1日聚合测试100", row)
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 2, "min_total_mv": 1e6, "max_count": 50, 'window_size': 8}
    # sss.write_validate_report("8日聚合测试", row)
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 50, 'window_size': 1}
    # sss.write_validate_report("1日聚合测试", row)
    # row = {"index_code": None, "fc_top_n": 10, 'fc_min_n': 3, "min_total_mv": 1e6, "max_count": 50, 'window_size': 8}
    # sss.write_validate_report("8日聚合测试", row)

    # 给定参数获取最新的强势股列表
    df = sss.get_latest_selected(fc_top_n=None, fc_min_n=None, min_total_mv=None, max_count=None, window_size=1)
    print(df)

