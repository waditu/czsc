# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:09
describe: 测试交易价格计算
"""
import czsc
import pandas as pd
import numpy as np
from czsc import mock


def test_trade_price():
    """测试交易价格计算功能"""
    df = mock.generate_symbol_kines("000001", "1分钟", sdt="20240101", edt="20240102", seed=42)
    df = df[['dt', 'symbol', 'open', 'high', 'low', 'close', 'vol']].copy()
    df = czsc.cal_trade_price(df, digits=3)

    # 使用近似对比，允许0.002的误差
    expected_twap = round(df['close'].iloc[1:21].mean(), 3)
    assert abs(df['TP_TWAP20'].iloc[0] - expected_twap) <= 0.002
    
    close = df['close'].iloc[1:21]
    vol = df['vol'].iloc[1:21]
    expected_vwap = round(np.average(close, weights=vol), 3)
    assert abs(df['TP_VWAP20'].iloc[0] - expected_vwap) <= 0.002


def test_make_it_daily():
    dts = pd.date_range(start='2022-01-01', end='2022-02-28', freq='W')
    df = pd.DataFrame({'dt': dts, 'value': np.random.random(len(dts))})

    # Call the function with the test DataFrame
    result = czsc.resample_to_daily(df)

    # Check the result
    assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"
    assert 'dt' in result.columns, "Result should have a 'dt' column"
    assert result['dt'].dtype == 'datetime64[ns]', "'dt' column should be datetime64[ns] type"
    assert not result['dt'].isnull().any(), "'dt' column should not have any null values"

    # Check if the result DataFrame has daily data
    result = czsc.resample_to_daily(df, only_trade_date=False)
    assert (result['dt'].diff().dt.days <= 1).iloc[1:].all(), "Result should have daily data"
