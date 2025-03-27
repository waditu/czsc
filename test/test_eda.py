import pytest
import pandas as pd
from czsc.eda import weights_simple_ensemble


def test_cal_yearly_days():
    if pd.__version__ < "2.1.0":
        pytest.skip("skip this test if pandas version is less than 1.3.0")

    from czsc.eda import cal_yearly_days

    # Test with a list of dates within a single year
    dts = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-12-31"]
    assert cal_yearly_days(dts) == 252

    # Test with a list of dates spanning more than one year
    dts = ["2022-01-01", "2022-12-31", "2023-01-01", "2023-12-31"]
    assert cal_yearly_days(dts) == 2

    # Test with a list of dates with minute precision
    dts = [
        "2023-01-01 12:00",
        "2023-01-02 13:00",
        "2023-01-01 14:00",
        "2023-02-01 15:00",
        "2023-03-01 16:00",
        "2023-03-01 17:00",
    ]
    assert cal_yearly_days(dts) == 252

    # Test with an empty list
    with pytest.raises(AssertionError):
        cal_yearly_days([])

    # Test with a list of dates with duplicates
    dts = ["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"]
    assert cal_yearly_days(dts) == 252


def test_weights_simple_ensemble_mean():
    df = pd.DataFrame({"strategy1": [0.1, 0.2, 0.3], "strategy2": [0.2, 0.3, 0.4], "strategy3": [0.3, 0.4, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="mean")
    expected = pd.Series([0.2, 0.3, 0.4], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_vote():
    df = pd.DataFrame({"strategy1": [1, -1, 1], "strategy2": [-1, 1, -1], "strategy3": [1, 1, -1]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="vote")
    expected = pd.Series([1, 1, -1], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_sum_clip():
    df = pd.DataFrame({"strategy1": [0.5, -0.5, 0.5], "strategy2": [0.5, 0.5, -0.5], "strategy3": [0.5, 0.5, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="sum_clip", clip_min=-1, clip_max=1)
    expected = pd.Series([1, 0.5, 0.5], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_only_long():
    df = pd.DataFrame({"strategy1": [0.5, -0.5, 0.5], "strategy2": [0.5, 0.5, -0.5], "strategy3": [0.5, 0.5, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="sum_clip", clip_min=-1, clip_max=1, only_long=True)
    expected = pd.Series([1, 0.5, 0.5], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_limit_leverage():
    from czsc.eda import limit_leverage

    data = {
        "dt": pd.date_range(start="2023-01-01", periods=10, freq="D"),
        "symbol": ["TEST"] * 10,
        "weight": [0.1, 0.2, -0.3, 3, -0.5, 0.6, -0.7, 0.8, -0.9, 1.0],
        "price": [100 + i for i in range(10)],
    }
    df = pd.DataFrame(data)

    # Test with leverage = 1.0
    df_result = limit_leverage(df, leverage=1.0, copy=True, window=3, min_periods=2)
    assert df_result["weight"].max() <= 1.0
    assert df_result["weight"].min() >= -1.0

    # Test with leverage = 2.0
    df_result = limit_leverage(df, leverage=2.0, copy=True, window=3, min_periods=2)
    assert df_result["weight"].max() <= 2.0
    assert df_result["weight"].min() >= -2.0

    # Test with different window and min_periods
    df_result = limit_leverage(df, leverage=1.0, window=5, min_periods=2, copy=True)
    assert df_result["weight"].max() <= 1.0
    assert df_result["weight"].min() >= -1.0

    df1 = df.copy()
    df1.rename(columns={"weight": "weight1"}, inplace=True)
    # Test with leverage = 1.0
    df_result = limit_leverage(df1, leverage=1.0, copy=True, window=3, min_periods=2, weight="weight1")
    assert df_result["weight1"].max() <= 1.0
    assert df_result["weight1"].min() >= -1.0


def test_turnover_rate_normal():
    """测试正常数据的换手率计算"""
    from czsc.eda import turnover_rate
    
    # 创建测试数据
    dates = pd.date_range(start='2024-01-01', periods=3, freq='D')
    symbols = ['A', 'B', 'C']
    
    # 创建权重数据
    weights = [
        [1.0, 0.5, 0.0],  # 第一天
        [0.5, 1.0, 0.5],  # 第二天
        [0.0, 0.5, 1.0],  # 第三天
    ]
    
    # 构建DataFrame
    data = []
    for i, date in enumerate(dates):
        for j, symbol in enumerate(symbols):
            data.append({
                'dt': date,
                'symbol': symbol,
                'weight': weights[i][j]
            })
    df = pd.DataFrame(data)
    
    # 计算换手率
    result = turnover_rate(df)
    
    # 验证结果
    assert isinstance(result, dict)
    assert "单边换手率" in result
    assert "日均换手率" in result
    assert "最大单日换手率" in result
    assert "最小单日换手率" in result
    assert "日换手详情" in result
    
    # 验证换手率计算是否正确
    # 第一天：1.0 + 0.5 + 0.0 = 1.5
    # 第二天：|0.5-1.0| + |1.0-0.5| + |0.5-0.0| = 1.5
    # 第三天：|0.0-0.5| + |0.5-1.0| + |1.0-0.5| = 1.5
    assert result["单边换手率"] == 4.5  # 1.5 + 1.5 + 1.5
    assert result["日均换手率"] == 1.5  # 4.5 / 3
    assert result["最大单日换手率"] == 1.5
    assert result["最小单日换手率"] == 1.5
    print(result['日换手详情'])


def test_turnover_rate_verbose():
    """测试verbose模式下的日志输出"""
    from czsc.eda import turnover_rate
    
    dates = pd.date_range(start='2024-01-01', periods=2, freq='D')
    symbols = ['A', 'B']
    data = [
        {'dt': dates[0], 'symbol': 'A', 'weight': 1.0},
        {'dt': dates[0], 'symbol': 'B', 'weight': 0.0},
        {'dt': dates[1], 'symbol': 'A', 'weight': 0.0},
        {'dt': dates[1], 'symbol': 'B', 'weight': 1.0},
    ]
    df = pd.DataFrame(data)
    
    # 这里我们只验证verbose=True时不会抛出异常
    result = turnover_rate(df, verbose=True)
    assert isinstance(result, dict)


def test_turnover_rate_invalid_data():
    """测试无效数据的处理"""
    from czsc.eda import turnover_rate
    
    # 测试缺少必要列的数据
    df = pd.DataFrame({'dt': ['2024-01-01'], 'symbol': ['A']})
    with pytest.raises(KeyError):
        turnover_rate(df)
    
    # 测试权重列包含非数值数据
    df = pd.DataFrame({
        'dt': ['2024-01-01'],
        'symbol': ['A'],
        'weight': ['invalid']
    })
    with pytest.raises(TypeError, match="weight 列必须包含数值数据"):
        turnover_rate(df)
