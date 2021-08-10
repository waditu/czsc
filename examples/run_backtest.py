# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/9 16:42
describe: 快速回测样例

快速回测二步走：
1）通过聚宽获取最近三年的1分钟数据，生成signals，signals可以重复使用
2）设定 long_open_event, long_exit_event 执行快速回测，查看回测结果
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
from czsc.data import jq
from czsc.objects import Signal, Factor, Event, Freq, Operate
from czsc.utils.io import read_pkl, save_pkl
from czsc.cobra.backtest import generate_signals, get_default_signals, long_trade_simulator, long_trade_estimator


# data_path = os.path.expanduser('~')
data_path = r"C:\jq_data\backtest"
symbol = '000001.XSHG'

# 通过聚宽获取最近三年的1分钟数据，生成signals，signals可以重复使用
file_signals = os.path.join(data_path, f'{symbol}_signals.pkl')
if os.path.exists(file_signals):
    signals = read_pkl(file_signals)
else:
    f1_raw_bars = jq.get_kline_period(symbol=symbol, freq='1min', start_date='20180401', end_date='20210801')
    signals = generate_signals(f1_raw_bars, init_count=50000, get_signals=get_default_signals)
    save_pkl(signals, file_signals)

# 设定 long_open_event, long_exit_event 执行快速回测，查看回测结果
long_open_event = Event(name='开多', operate=Operate.LO, factors=[
    Factor(name="15分钟一买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
    Factor(name="15分钟二买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
    Factor(name="15分钟三买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
])
long_exit_event = Event(name="一卖", operate=Operate.LE, factors=[
    Factor(name="15分钟一卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
    Factor(name="15分钟二卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
    Factor(name="15分钟三卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
])

pairs = long_trade_simulator(signals, long_open_event, long_exit_event)
res = long_trade_estimator(pairs)
