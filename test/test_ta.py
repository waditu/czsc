# coding: utf-8
import os
import pandas as pd
import numpy as np
import czsc

cur_path = os.path.split(os.path.realpath(__file__))[0]
file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
bars = kline.to_dict("records")
close = np.array([x['close'] for x in bars], dtype=np.double)


def test_sma():
    ma5 = czsc.SMA(close, 5)
    assert len(ma5) == len(close)
    assert round(ma5[-1], 2) == 3362.53
    assert round(ma5[-2], 2) == 3410.62


def test_macd():
    diff, dea, macd = czsc.MACD(close)

    assert len(diff) == len(dea) == len(macd) == len(close)
    assert round(macd[-1], 2) == 13.35
    assert round(macd[-5], 2) == 88.0

    assert round(diff[-1], 2) == 117.3
    assert round(diff[-5], 2) == 127.51

    assert round(dea[-1], 2) == 110.62
    assert round(dea[-5], 2) == 83.51


def test_jdk():
    high = np.array([x['high'] for x in bars], dtype=np.double)
    low = np.array([x['low'] for x in bars], dtype=np.double)
    k, d, j = czsc.KDJ(close, high, low)

    assert round(k[-1], 2) == 59.94
    assert round(d[-1], 2) == 80.47
    assert round(j[-1], 2) == 18.87
