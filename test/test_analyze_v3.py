# coding: utf-8

import sys
import warnings
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import pandas as pd
import czsc
from czsc.analyze_v3 import KlineAnalyze

warnings.warn(f"czsc version is {czsc.__version__}")

kline = get_kline(ts_code="000001.SH", end_dt="2020-07-16 15:00:00", freq='D', asset='I')
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline.loc[:, "is_end"] = True
# ka = KlineAnalyze(kline, name="日线")
# print(ka)


def test_objects():
    if isinstance(kline, pd.DataFrame):
        columns = kline.columns.to_list()
        bars = [{k: v for k, v in zip(columns, row)} for row in kline.values]
    else:
        bars = kline

    ka = KlineAnalyze(name="日线")
    for bar in bars:
        ka.update(bar)


