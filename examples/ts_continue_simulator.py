# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 15:54
describe: 使用 Tushare 数据对交易策略进行持续仿真研究
"""
from ts_fast_backtest import TsDataCache
from czsc.traders.ts_simulator import TradeSimulator
from czsc.strategies import trader_strategy_a

data_path = r"C:\ts_data"
dc = TsDataCache(data_path, sdt='2022-01-01', edt='2022-05-06')
ts = TradeSimulator(dc, trader_strategy_a)
ts.update_trader('000001.SH', 'I')
trader = ts.create_trader('000001.SH', 'I')

