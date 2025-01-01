import pandas as pd
from czsc.utils.kline_quality import check_kline_quality
from test.test_analyze import read_daily


def test_check_zero_volume():
    df = read_daily()
    df = pd.DataFrame([bar.__dict__ for bar in df])
    df["vol"] = df["vol"].astype(int)
    # 执行数据质量检查
    df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]]
    issues = check_kline_quality(df)
