# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/12 22:00
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
import pandas as pd
from czsc.traders.ts_backtest import TsDataCache, TsStocksBacktest, freq_cn2ts
from examples import tactics

os.environ['czsc_verbose'] = "0"     # 是否输出详细执行信息，0 不输出，1 输出

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)

data_path = r"C:\ts_data"
dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-02-18')
strategy = tactics.trader_strategy_a
freq = freq_cn2ts[strategy()['base_freq']]


def run_backtest(step_seq=('check', 'index', 'etfs', 'train', 'valid', 'stock')):
    """

    :param step_seq: 回测执行顺序
    :return:
    """
    tsb = TsStocksBacktest(dc, strategy, sdt='20140101', edt="20211216", init_n=1000*4)
    for step in step_seq:
        tsb.batch_backtest(step.lower())
        tsb.analyze_signals(step.lower())


if __name__ == '__main__':
    run_backtest(step_seq=('index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train', 'valid'))

