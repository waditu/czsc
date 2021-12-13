# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/25 17:39
describe: 因子表现传感器
"""
import os
import numpy as np
from tqdm import tqdm
import pandas as pd
from czsc import CZSC
from czsc.utils import io
from czsc.sensors.factors import FactorsSensor, TsDataCache
from czsc.objects import Freq, Signal, Factor, Event, Operate
from czsc.signals.ta import get_s_macd, get_s_sma, OrderedDict


pd.set_option('mode.chained_assignment', None)


def get_signals(c: CZSC):
    s = OrderedDict()

    if c.freq in [Freq.D, Freq.M]:
        s.update(get_s_macd(c, di=1))

    if c.freq == Freq.D:
        s.update(get_s_sma(c, di=1, t_seq=(5, 20, 60, 120, 250)))
    return s


def get_factors():
    double_signal_factors = [
        Factor(name="日线MACD多头&日线DIF多头", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='MACD多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='DIF多空', v1='多头'),
        ]),

        Factor(name="日线SMA20多头向上", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='SMA20多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA20方向', v1='向上'),
        ]),

        Factor(name="日线SMA60多头向上", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='SMA60多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA60方向', v1='向上'),
        ]),
    ]

    triple_signal_factors = [
        Factor(name="日线MACD长多", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='DIF多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA60多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA60方向', v1='向上'),
        ]),

        Factor(name="日线MACD短多", signals_all=[
            Signal(k1='日线', k2='倒1K', k3='MACD多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA20多空', v1='多头'),
            Signal(k1='日线', k2='倒1K', k3='SMA20方向', v1='向上'),
        ]),
    ]

    factors = double_signal_factors + triple_signal_factors
    return factors


def prepare_symbol_signals(file, dc):
    signals = io.read_pkl(file)
    df = pd.DataFrame(signals)
    keys = [x for x in df.columns if len(x.split("_")) == 3]
    nb = dc.pro_bar(signals[0]['symbol'], start_date=signals[0]['dt'], end_date=signals[-1]['dt'],
                    freq='D', asset="E", raw_bar=False)
    df = df.merge(nb, left_on='dt', right_on='trade_date')
    for f in keys:
        if df[f].dtype == 'O' or df[f].dtype == 'bool':
            itm_list = list(df[f].unique())
            for itm in itm_list:
                ecol = '%s_%s' % (f, itm)
                df[ecol] = df[f].apply(lambda x: 1 if x == itm else 0)
    return df


def analyze_signals_v2():
    dc = TsDataCache(data_path=r"D:\research\ts_data", sdt='2000-01-01', edt='20211201')
    signals_path = r'D:\research\ts_data\MACD_V1_factors_20180101_20211114\signals'
    files = [os.path.join(signals_path, x) for x in os.listdir(signals_path) if x.endswith(".pkl")]

    keys = []
    for file in tqdm(files[1:100], desc='get keys'):
        df_ = prepare_symbol_signals(file, dc)
        keys = list(set([x for x in list(df_.columns) if len(x.split('_')) == 7] + keys))

    for key in keys:
        results = []
        for file in tqdm(files, desc='get keys'):
            df_ = prepare_symbol_signals(file, dc)
            if key not in df_.columns:
                continue
            cols = ['symbol', 'dt', key,
                    'n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b',
                    'b1b', 'b2b', 'b3b', 'b5b', 'b10b', 'b20b']
            results.append(df_[df_[key] == 1][cols])
        df_res = pd.concat(results, ignore_index=True)
        results = []
        for date, dfg in df_res.groupby('dt'):
            row = {"date": date, "count": len(dfg)}
            row.update(dfg[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b',
                            'b1b', 'b2b', 'b3b', 'b5b', 'b10b', 'b20b']].mean())
            results.append(row)
        df = pd.DataFrame(results)


if __name__ == '__main__':
    data_path = r"D:\research\ts_data"
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='20211211')
    sdt = "20180101"
    edt = "20211114"
    results_path = os.path.join(data_path, f"factors_{sdt}_{edt}")
    sss = FactorsSensor(results_path, sdt, edt, dc, "日线", ['周线', '月线'], get_signals, get_factors)
    sss.validate_performance()
