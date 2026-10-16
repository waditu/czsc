"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:09
describe: 测试交易工具函数（``czsc.resample_to_daily`` 等）

    ``cal_trade_price`` 已在二阶段清理 PR-B 删除，原 ``test_trade_price`` 测试
    随之移除；本文件保留 ``czsc.resample_to_daily`` 的覆盖。
"""

import numpy as np
import pandas as pd
import pytest

import czsc


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
@pytest.mark.parametrize("only_trade_date", [True, False])
def test_resample_to_daily_normalizes_datetime_precision(unit, only_trade_date):
    dates = pd.date_range("2022-01-03", periods=3, freq="7D").astype(f"datetime64[{unit}]")
    frame = pd.DataFrame({"dt": dates, "value": [10, 20, 30]})

    result = czsc.resample_to_daily(frame, only_trade_date=only_trade_date)

    assert result["dt"].dtype == "datetime64[ns]"
    assert result["dt"].is_monotonic_increasing
    assert result["value"].iloc[0] == 10
    assert result["value"].iloc[-1] == 30
    if only_trade_date:
        assert (result["dt"].dt.dayofweek < 5).all()


def test_make_it_daily():
    dts = pd.date_range(start="2022-01-01", end="2022-02-28", freq="W")
    df = pd.DataFrame({"dt": dts, "value": np.random.random(len(dts))})

    # Call the function with the test DataFrame
    result = czsc.resample_to_daily(df)

    # Check the result
    assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
    assert "dt" in result.columns, "Result should have a 'dt' column"
    assert result["dt"].dtype == "datetime64[ns]", "'dt' column should be datetime64[ns] type"
    assert not result["dt"].isnull().any(), "'dt' column should not have any null values"

    # Check if the result DataFrame has daily data
    result = czsc.resample_to_daily(df, only_trade_date=False)
    assert (result["dt"].diff().dt.days <= 1).iloc[1:].all(), "Result should have daily data"
