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
from czsc.data.base import freq_cn2ts
from czsc.sensors.utils import read_cached_signals, SignalsPerformance
from czsc.traders.ts_backtest import TsDataCache, TsStocksBacktest
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


def analyze_tactic_signals(path: str, step: str = None):
    """分析策略中信号的基础表现

    :param path: 信号路径
    :param step:
    :return:
    """
    step = 'all' if not step else step
    file_dfs = os.path.join(path, f"{step}_dfs.pkl")
    signals_pat = fr"{path}\raw_{step}\*_signals.pkl" if step != 'all' else fr"{path}\raw_*\*_signals.pkl"

    if not os.path.exists(file_dfs):
        dfs = read_cached_signals(file_dfs, signals_pat)
        asset = "I" if step == 'index' else "E"
        results = []
        for symbol, dfg in tqdm(dfs.groupby('symbol'), desc='add nbar'):
            dfk = dc.pro_bar_minutes(symbol, sdt=dfg['dt'].min(), edt=dfg['dt'].max(),
                                     freq=freq, asset=asset, adj='hfq', raw_bar=False)
            dfk_cols = ['dt'] + [x for x in dfk.columns if x not in dfs.columns]
            dfk = dfk[dfk_cols]
            dfs_ = dfg.merge(dfk, on='dt', how='left')
            results.append(dfs_)

        dfs = pd.concat(results, ignore_index=True)
        c_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('object')]
        dfs[c_cols] = dfs[c_cols].astype('category')
        float_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('float')]
        dfs[float_cols] = dfs[float_cols].astype('float32')
        dfs.to_pickle(file_dfs, protocol=4)
    else:
        dfs = pd.read_pickle(file_dfs)

    signal_cols = [x for x in dfs.columns if len(x.split("_")) == 3]
    for key in signal_cols:
        file_xlsx = os.path.join(path, f"{step}_{key.replace(':', '')}.xlsx")
        sp = SignalsPerformance(dfs, keys=[key], dc=dc)
        sp.report(file_xlsx)
        print(f"{key} performance saved into {file_xlsx}")


if __name__ == '__main__':
    run_backtest(step_seq=('index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train', 'valid'))
    # analyze_tactic_signals(path=r"C:\ts_data\trader_stocks_v1_e_01", step='index')

