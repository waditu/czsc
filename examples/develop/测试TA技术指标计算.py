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
