# coding: utf-8

import sys
import warnings
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import czsc
from czsc.analyze_v2 import KlineAnalyze

warnings.warn(f"czsc version is {czsc.__version__}")

df = get_kline(ts_code="000001.SH", end_dt="2020-07-14 15:00:00", freq='D', asset='I')
ka = KlineAnalyze(df, name="日线")
print(ka)
