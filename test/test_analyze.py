# coding: utf-8

import sys
import warnings
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import pandas as pd
import czsc
from czsc.analyze import KlineAnalyze

warnings.warn(f"czsc version is {czsc.__version__}")

kline = get_kline(ts_code="000001.SH", end_dt="2020-07-16 15:00:00", freq='D', asset='I')
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline.loc[:, "is_end"] = True
# ka = KlineAnalyze(kline, name="日线")
# print(ka)


def test_kline_analyze():
    ka = KlineAnalyze(kline, name="日线")

    # 测试增量更新
    ka_raw_len = len(ka.kline_raw)
    for x in [2890, 2910, 2783, 3120]:
        k = dict(ka.kline_raw[-1])
        k['close'] = x
        ka.update(k)
        assert len(ka.kline_raw) == ka_raw_len
        assert ka.kline_raw[-1]['close'] == x

