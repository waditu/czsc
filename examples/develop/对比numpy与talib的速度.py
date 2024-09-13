import sys

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import talib
from czsc.utils import ta
from czsc.connectors import cooperation as coo


df = coo.get_raw_bars(symbol="SFIC9001", freq="30分钟", fq="后复权", sdt="20100101", edt="20210301", raw_bars=False)


def test_with_numpy():
    df1 = df.copy()
    df1["x"] = ta.LINEARREG_ANGLE(df["close"].values, 10)


def test_with_talib():
    df1 = df.copy()
    df1["x"] = talib.LINEARREG_ANGLE(df["close"].values, 10)
