import sys
import time

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import talib
from czsc.utils import ta
from czsc.connectors import cooperation as coo


df = coo.get_raw_bars(symbol="SFIC9001", freq="日线", fq="后复权", sdt="20100101", edt="20210301", raw_bars=False)


def test_CHOP():
    df1 = df.copy()
    df1["CHOP"] = ta.CHOP(df1["high"], df1["low"], df1["close"])
    df1["WMA"] = ta.WMA(df1["close"], timeperiod=3)


def test_WMA():
    df1 = df.copy()
    df1["WMA"] = ta.WMA(df1["close"], timeperiod=3)
    df1["WMA2"] = talib.WMA(df1["close"], timeperiod=5)
    print(df1[["close", "WMA", "WMA2"]].tail(10))


def test_rolling_rsq():
    df1 = df.copy()
    df1["rsq"] = ta.rolling_rsq(df1["close"], window=5)
    print(df1[["close", "rsq"]].tail(10))


def test_rolling_corr():
    df1 = df.copy()
    df1["corr"] = ta.rolling_corr(df1["close"], df1["open"], window=5)
    print(df1[["close", "open", "corr"]].tail(10))


def test_rolling_beta():
    df1 = df.copy()
    df1["beta"] = ta.rolling_beta(df1["close"], df1["open"], window=5)
    print(df1[["close", "open", "beta"]].tail(10))


def test_rolling_std():
    df1 = df.copy()
    df1["std"] = ta.rolling_std(df1["close"], window=5)
    print(df1[["close", "std"]].tail(10))


def test_rolling_max():
    df1 = df.copy()
    df1["max"] = ta.rolling_max(df1["close"], window=5)
    print(df1[["close", "max"]].tail(10))


def test_rolling_min():
    df1 = df.copy()
    df1["min"] = ta.rolling_min(df1["close"], window=5)
    print(df1[["close", "min"]].tail(10))


def test_rolling_mdd():
    df1 = df.copy()
    df1["mdd"] = ta.rolling_mdd(df1["close"], window=5)
    print(df1[["close", "mdd"]].tail(10))


def test_ultimate_smoother():
    df1 = df.copy()
    df1["uo"] = ta.ultimate_smoother(df1["close"], period=5)
    print(df1[["close", "uo"]].tail(10))
