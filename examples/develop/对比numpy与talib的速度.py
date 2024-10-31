import sys
import time

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import talib
from czsc.utils import ta
from czsc.connectors import cooperation as coo


df = coo.get_raw_bars(symbol="SFIC9001", freq="日线", fq="后复权", sdt="20100101", edt="20210301", raw_bars=False)


def test_vs_volatility():
    df1 = df.copy()
    df1["STD"] = df["close"].pct_change().rolling(30).std()
    df1["RS"] = ta.RS_VOLATILITY(df1, timeperiod=30)
    df1["PK"] = ta.PK_VOLATILITY(df1, timeperiod=30)
    df1[["STD", "RS", "PK"]].corr()


def test_compare_LINEARREG_ANGLE():
    df1 = df.copy()
    s1 = time.time()
    df1["x1"] = ta.LINEARREG_ANGLE(df["close"].values, 10)
    e1 = time.time() - s1

    s2 = time.time()
    df1["x2"] = talib.LINEARREG_ANGLE(df["close"].values, 10)
    e2 = time.time() - s2

    print(f"计算时间差异，ta: {e1}, talib: {e2}；相差：{e1 - e2}")
    df1["diff"] = df1["x1"] - df1["x2"]
    assert df1["diff"].abs().max() < 1e-6
    print(df1["diff"].abs().max())


def test_compare_CCI():
    # 数据对不上，需要调整
    df1 = df.copy()
    s1 = time.time()
    df1["x1"] = ta.CCI(df1["high"].values, df1["low"].values, df1["close"].values, timeperiod=14)
    e1 = time.time() - s1

    s2 = time.time()
    df1["x2"] = talib.CCI(df1["high"].values, df1["low"].values, df1["close"].values, timeperiod=14)
    e2 = time.time() - s2

    print(f"计算时间差异，ta: {e1}, talib: {e2}；相差：{e1 - e2}")
    df1["diff"] = df1["x1"] - df1["x2"]
    print(df1["diff"].abs().describe())

    assert df1["diff"].abs().max() < 1e-6


def test_compare_MFI():
    # 数据对不上，需要调整
    df1 = df.copy()
    s1 = time.time()
    df1["x1"] = ta.MFI(df1["high"], df1["low"], df1["close"], df1["vol"], timeperiod=14)
    e1 = time.time() - s1

    s2 = time.time()
    df1["x2"] = talib.MFI(df1["high"].values, df1["low"].values, df1["close"].values, df1["vol"].values, timeperiod=14)
    e2 = time.time() - s2

    print(f"计算时间差异，ta: {e1}, talib: {e2}；相差：{e1 - e2}")
    df1["diff"] = df1["x1"] - df1["x2"]
    print(df1["diff"].abs().describe())

    assert df1["diff"].abs().max() < 1e-6


def test_compare_PLUS_DI():
    # 数据对不上，需要调整
    df1 = coo.get_raw_bars(symbol="SFIC9001", freq="日线", fq="后复权", sdt="20100101", edt="20210301", raw_bars=False)

    s1 = time.time()
    df1["x1"] = ta.PLUS_DI(df1["high"], df1["low"], df1["close"], timeperiod=14)
    e1 = time.time() - s1

    s2 = time.time()
    df1["x2"] = talib.PLUS_DI(df1["high"].values, df1["low"].values, df1["close"].values, timeperiod=14)
    e2 = time.time() - s2

    print(f"计算时间差异，ta: {e1}, talib: {e2}；相差：{e1 - e2}")
    df1["diff"] = df1["x1"] - df1["x2"]
    print(df1["diff"].abs().describe())

    assert df1["diff"].abs().max() < 1e-6
