import pandas as pd
from czsc.utils.kline_quality import (
    check_high_low,
    check_price_gap,
    check_abnormal_volume,
    check_zero_volume,
)
from test.test_analyze import read_daily


def test_check_high_low():
    df = read_daily()
    df = pd.DataFrame([x.__dict__ for x in df])
    error_rate, error_klines = check_high_low(df)
    assert error_rate == 0


def test_check_price_gap():
    df = read_daily()
    df = pd.DataFrame([x.__dict__ for x in df])
    error_rate, error_klines = check_price_gap(df)
    assert round(error_rate, 4) == 0.0183
    print(error_klines)


def test_check_abnormal_volume():
    df = read_daily()
    df = pd.DataFrame([x.__dict__ for x in df])
    error_rate, error_klines = check_abnormal_volume(df)
    assert round(error_rate, 4) == 0.0306
    print(error_klines)


def test_check_zero_volume():
    df = read_daily()
    df = pd.DataFrame([x.__dict__ for x in df])
    error_rate, error_klines = check_zero_volume(df)
    assert error_rate == 0
    print(error_klines)
