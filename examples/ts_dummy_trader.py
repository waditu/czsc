# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/11 20:57
describe: 使用 CzscDummyTrader 进行快速的族系研究
"""
import os.path
import pandas as pd
from czsc.strategies import trader_strategy_a as strategy
from czsc.traders.advanced import CzscDummyTrader
from czsc.sensors.utils import generate_symbol_signals
from examples.ts_fast_backtest import dc


# 可以直接生成信号，也可以直接读取信号
file_dfs = os.path.join(dc.data_path, "sample_dfs.pkl")
if os.path.exists(file_dfs):
    dfs = pd.read_pickle(file_dfs)
else:
    dfs = generate_symbol_signals(dc, "000001.SH", "I", "20150101", "20220101", strategy, 'hfq')
    dfs.to_pickle(file_dfs)

cdt = CzscDummyTrader(dfs, strategy)
print(cdt.results['long_performance'])

cdt1 = CzscDummyTrader(dfs, strategy)
print(cdt1.results['long_performance'])

