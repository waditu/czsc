# coding: utf-8

import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import pandas as pd
import czsc
from czsc.analyze import KlineAnalyze, find_zs
from czsc.signals_v1 import KlineSignals

warnings.warn("czsc version is {}".format(czsc.__version__))

cur_path = os.path.split(os.path.realpath(__file__))[0]
# cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline1 = kline.iloc[:2000]
kline2 = kline.iloc[2000:]

def test_ka_signals():
    ka = KlineSignals(kline1, name="日线", max_raw_len=2000,)

    for _, bar in kline2.iterrows():
        ka.update(bar)
        print(ka.get_signals())
