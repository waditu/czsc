# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/24 16:33
describe: 使用 Tushare 数据分析信号表现
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
import pandas as pd
from czsc import CZSC, Freq
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc.sensors.utils import read_cached_signals, generate_stocks_signals, analyze_signal_keys
from czsc import signals

pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)


def get_v1_signals(c: CZSC):
    s = OrderedDict()
    if c.freq == Freq.D:
        s.update(signals.bxt.get_s_three_bi(c, di=1))
        s.update(signals.vol.get_s_vol_single_sma(c, di=1, t_seq=(10, 20)))
    return s


data_path = r"C:\ts_data"
dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-02-18')
signals_path = os.path.join(data_path, 'signals_b')

# if not os.path.exists(signals_path):
#     generate_stocks_signals(dc, signals_path, sdt='20100101', edt='20220101', base_freq='日线',
#                             freqs=['周线', '月线'], get_signals=get_v1_signals)

# dfs = read_cached_signals(os.path.join(data_path, "signals_b_20180101_20220101.pkl"),
#                           path_pat=f"{signals_path}\*_signals.pkl", sdt="2018-01-01", edt="2022-01-01")

dfs = read_cached_signals(os.path.join(data_path, "signals_b_20180101_20220101.pkl"),
                          path_pat=rf"C:\ts_data\signals_v2\*.pkl", sdt="2018-01-01", edt="2022-01-01")


def report_signal_performance():
    dfr = analyze_signal_keys(dfs, keys=['日线_倒1K1B均额_1至4千万'], mode=2)

    # 按年分析
    dfs['year'] = dfs['dt'].apply(lambda x: x.year)

    results = []
    keys = ['日线_倒1K1B均额_1至4千万']
    for year, df_ in dfs.groupby('year'):
        dfr_ = analyze_signal_keys(df_, keys, mode=2)
        dfr_['year'] = year
        results.append(dfr_)
    dfr = pd.concat(results, ignore_index=True)
