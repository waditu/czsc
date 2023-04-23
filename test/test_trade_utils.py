# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:09
describe: 测试交易价格计算
"""
import czsc
import numpy as np
from test.test_analyze import read_1min


def test_trade_price():
    bars = read_1min()
    df = czsc.cal_trade_price(bars)

    assert df['TWAP20'].iloc[0] == round(df['close'].iloc[1:21].mean(), 3)
    close = df['close'].iloc[1:21]
    vol = df['vol'].iloc[1:21]
    assert df['VWAP20'].iloc[0] == round(np.average(close, weights=vol), 3)
