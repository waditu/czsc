# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/16 20:31
describe: czsc.utils 单元测试
"""
import pytest
import pandas as pd
import numpy as np
from czsc import utils


def test_x_round():
    assert utils.x_round(100, 3) == 100
    assert utils.x_round(1.000342, 3) == 1.0
    assert utils.x_round(1.000342, 4) == 1.0003
    assert utils.x_round(1.000342, 5) == 1.00034


def test_subtract_fee():
    from czsc.utils.stats import subtract_fee

    # 构造测试数据
    data = {
        'dt': pd.date_range('2022-01-01', periods=20, freq='D'),
        'pos': [0, 1, 1, -1, -1, -1, 0, 0, 1, 1, 1, 1, 1, 0, 0, -1, -1, 0, 1, 1],
        'price': [10, 11, 12, 13, 14, 10, 11, 12, 13, 14, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    }
    df = pd.DataFrame(data)

    # 执行函数
    df = subtract_fee(df, fee=100)

    # 验证结果
    assert int(df['edge_pre_fee'].sum()) == 2748
    assert int(df['edge_post_fee'].sum()) == 1848

    # 构造测试数据
    data = {
        'dt': pd.date_range('2022-01-01', periods=5, freq='D'),
        'pos': [0, 1, 1, -1, 0],
    }
    df = pd.DataFrame(data)

    # 执行函数并捕获异常
    with pytest.raises(AssertionError):
        subtract_fee(df, fee=1)

    # 构造测试数据
    data = {
        'dt': pd.date_range('2022-01-01', periods=5, freq='D'),
        'pos': [0, 1, 2, -1, 0],
        'price': [10, 11, 12, 13, 14]
    }
    df = pd.DataFrame(data)

    # 执行函数并捕获异常
    with pytest.raises(AssertionError):
        subtract_fee(df, fee=1)


def test_ranker():
    import numpy as np
    import pandas as pd
    from czsc.utils.cross import cross_sectional_ranker

    np.random.seed(42)
    dates = pd.date_range('2021-01-01', '2023-01-05')
    symbols = ['AAPL', 'GOOG', 'TSLA', 'MSFT']
    data = {'date': [], 'symbol': [], 'return': [], 'factor1': [], 'factor2': []}
    for date in dates:
        returns = np.random.randn(len(symbols))
        ranks = np.argsort(returns) + 1
        for ticker, rank in zip(symbols, ranks):
            data['date'].append(date)
            data['symbol'].append(ticker)
            data['return'].append(rank)  # 'return' 现在代表了每天的收益率排名
            data['factor1'].append(np.random.randn())
            data['factor2'].append(np.random.randn())
    df = pd.DataFrame(data)
    df['dt'] = df['date']

    x_cols = ['factor1', 'factor2']
    y_col = 'return'

    dfp = cross_sectional_ranker(df, x_cols, y_col)
    assert dfp['rank'].max() == len(symbols)
    assert dfp['rank'].min() == 1
    assert dfp['rank'].mean() == 2.5


def test_daily_performance():
    from czsc.utils.stats import daily_performance

    # Test case 1: empty daily returns
    result = daily_performance([])
    assert result == {"年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0, "日胜率": 0, "年化波动率": 0, "非零覆盖": 0, "盈亏平衡点": 0}

    # Test case 2: daily returns with zero standard deviation
    result = daily_performance([1, 1, 1, 1, 1])
    assert result == {"年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0, "日胜率": 0, "年化波动率": 0, "非零覆盖": 0, "盈亏平衡点": 0}

    # Test case 3: daily returns with all zeros
    result = daily_performance([0, 0, 0, 0, 0])
    assert result == {"年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0, "日胜率": 0, "年化波动率": 0, "非零覆盖": 0, "盈亏平衡点": 0}

    # Test case 4: normal daily returns
    daily_returns = np.array([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
    result = daily_performance(daily_returns)
    assert result == {'年化': 2.016, '夏普': 8.27, '最大回撤': 0.02, '卡玛': 100.8, '日胜率': 0.7, '年化波动率': 0.2439, '非零覆盖': 1.0, '盈亏平衡点': 0.7}

    result = daily_performance([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
    assert result == {'年化': 2.016, '夏普': 8.27, '最大回撤': 0.02, '卡玛': 100.8, '日胜率': 0.7, '年化波动率': 0.2439, '非零覆盖': 1.0, '盈亏平衡点': 0.7}
