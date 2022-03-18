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
from tqdm import tqdm
from czsc.sensors.utils import read_cached_signals, get_dfs_base, analyze_signal_keys
from czsc.traders.ts_backtest import TsDataCache, TsStocksBacktest
from examples import tactics

os.environ['czsc_verbose'] = "1"     # 输出详细执行信息

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)

data_path = r"C:\ts_data"
dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-02-18')


def run_backtest():
    tsb = TsStocksBacktest(dc=dc, strategy=tactics.trader_strategy_a,
                           sdt='20140101', edt="20211216", init_n=1000*4)
    # tsb.batch_backtest('check')
    tsb.batch_backtest('index')
    tsb.batch_backtest('train')
    tsb.batch_backtest('valid')
    # tsb.batch_backtest('stock')


def analyze_tactic_signals():
    file_dfs = 'sf_train.pkl'
    if not os.path.exists(file_dfs):
        dfs = read_cached_signals(file_dfs, r"C:\ts_data\trader_strategy_a\raw_train\*_signals.pkl")
        asset = "I"
        freq = '15min'
        results = []
        for symbol, dfg in tqdm(dfs.groupby('symbol'), desc='add nbar'):
            dfk = dc.pro_bar_minutes(symbol, sdt=dfg['dt'].min(), edt=dfg['dt'].max(),
                                     freq=freq, asset=asset, adj='hfq', raw_bar=False)
            dfk_cols = ['dt'] + [x for x in dfk.columns if x not in dfs.columns]
            dfk = dfk[dfk_cols]
            dfs_ = dfg.merge(dfk, on='dt', how='left')

            results.append(dfs_)

        dfs = pd.concat(results, ignore_index=True)
        dfs.to_pickle(file_dfs, protocol=4)
    else:
        dfs = pd.read_pickle(file_dfs)

    base = get_dfs_base(dfs)
    dfr = analyze_signal_keys(dfs, keys=['多头_最大_回撤'])
    print(dfr[['name', 'cover', 'n1b', 'dt_n1b', 'n5b', 'dt_n5b']])


if __name__ == '__main__':
    run_backtest()


