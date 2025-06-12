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
    dates = pd.date_range(start="2024-01-01", periods=3, freq="D")
    symbols = ["A", "B", "C"]

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
            data.append({"dt": date, "symbol": symbol, "weight": weights[i][j]})
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
    print(result["日换手详情"])


def test_turnover_rate_verbose():
    """测试verbose模式下的日志输出"""
    from czsc.eda import turnover_rate

    dates = pd.date_range(start="2024-01-01", periods=2, freq="D")
    symbols = ["A", "B"]
    data = [
        {"dt": dates[0], "symbol": "A", "weight": 1.0},
        {"dt": dates[0], "symbol": "B", "weight": 0.0},
        {"dt": dates[1], "symbol": "A", "weight": 0.0},
        {"dt": dates[1], "symbol": "B", "weight": 1.0},
    ]
    df = pd.DataFrame(data)

    # 这里我们只验证verbose=True时不会抛出异常
    result = turnover_rate(df, verbose=True)
    assert isinstance(result, dict)


def test_turnover_rate_invalid_data():
    """测试无效数据的处理"""
    from czsc.eda import turnover_rate

    # 测试缺少必要列的数据
    df = pd.DataFrame({"dt": ["2024-01-01"], "symbol": ["A"]})
    with pytest.raises(KeyError):
        turnover_rate(df)

    # 测试权重列包含非数值数据
    df = pd.DataFrame({"dt": ["2024-01-01"], "symbol": ["A"], "weight": ["invalid"]})
    with pytest.raises(TypeError, match="weight 列必须包含数值数据"):
        turnover_rate(df)


def test_cross_sectional_strategy():
    """测试横截面策略功能和mock数据质量"""
    import pandas as pd
    from czsc import mock
    from czsc.eda import cross_sectional_strategy

    def __execute_one():
        """执行单次横截面策略测试"""
        df = mock.generate_cs_factor()
        df = cross_sectional_strategy(df, factor="F#RPS#20", long=0.3, short=0.3, norm=True, window=1, verbose=False)
        dfw = pd.pivot_table(df, index="dt", columns="symbol", values="weight")
        dfw["sum"] = dfw.sum(axis=1)
        assert dfw["sum"].max() < 0.01 and dfw["sum"].min() > -0.01
        return df, dfw

    # 执行基本测试
    df, dfw = __execute_one()

    # 验证mock数据质量
    assert isinstance(df, pd.DataFrame), "generate_cs_factor应该返回DataFrame"
    assert len(df) > 0, "数据不应为空"
    assert "F#RPS#20" in df.columns, "应包含F#RPS#20因子列"
    assert "symbol" in df.columns, "应包含symbol列"
    assert "dt" in df.columns, "应包含dt列"

    # 验证因子数据的合理性
    factor_values = df["F#RPS#20"]
    assert factor_values.min() >= 0, "RPS因子值应该>=0"
    assert factor_values.max() <= 1, "RPS因子值应该<=1"
    assert not factor_values.isnull().all(), "因子值不应全为空"

    # 验证策略权重的合理性
    weights = df["weight"]
    assert weights.abs().max() <= 1, "权重绝对值不应超过1"

    # 测试不同参数组合
    def test_different_params():
        """测试不同参数组合"""
        df_base = mock.generate_cs_factor()

        # 测试只做多
        df_long = cross_sectional_strategy(
            df_base.copy(), factor="F#RPS#20", long=0.2, short=0.0, norm=True, window=1, verbose=False
        )
        assert (df_long["weight"] >= 0).all(), "只做多时权重应该>=0"

        # 测试只做空
        df_short = cross_sectional_strategy(
            df_base.copy(), factor="F#RPS#20", long=0.0, short=0.2, norm=True, window=1, verbose=False
        )
        assert (df_short["weight"] <= 0).all(), "只做空时权重应该<=0"

        # 测试不归一化
        df_no_norm = cross_sectional_strategy(
            df_base, factor="F#RPS#20", long=0.3, short=0.3, norm=False, window=1, verbose=False
        )
        assert isinstance(df_no_norm, pd.DataFrame), "不归一化时应该返回DataFrame"

        # 测试多空 + window 平滑
        df_long_smooth = cross_sectional_strategy(
            df_base.copy(), factor="F#RPS#20", long=0.3, short=0.3, norm=True, window=20, verbose=False
        )
        assert isinstance(df_long_smooth, pd.DataFrame), "多空 + window 平滑时应该返回DataFrame"
        dfw_smooth = pd.pivot_table(df_long_smooth, index="dt", columns="symbol", values="weight")
        dfw_smooth["sum"] = dfw_smooth.sum(axis=1)
        assert dfw_smooth["sum"].max() < 0.01 and dfw_smooth["sum"].min() > -0.01
        print(f"多空+20日平滑：{dfw_smooth.tail()}")

        return True

    # 执行参数测试
    assert test_different_params(), "不同参数组合测试失败"

    # 验证时间序列的连续性
    dates = sorted(df["dt"].unique())
    assert len(dates) > 100, "应该有足够的时间序列数据"

    # 验证不同股票的数据完整性
    symbols = df["symbol"].unique()
    assert len(symbols) > 10, "应该有足够的股票数量"

    for symbol in symbols[:3]:  # 检查前3个股票
        symbol_data = df[df["symbol"] == symbol]
        assert len(symbol_data) == len(dates), f"股票{symbol}的数据点数量应该与日期数量一致"

    print(f"横截面策略测试通过: 共{len(dates)}个交易日，{len(symbols)}只股票")
    print(f"最新日期权重分布:\n{dfw[dfw.index == dfw.index.max()]}")


def test_mock_klines_data_quality():
    """测试优化后的mock klines数据质量"""
    from czsc import mock
    import numpy as np

    # 生成数据
    df = mock.generate_klines(seed=42)

    # 基本验证
    assert isinstance(df, pd.DataFrame), "应该返回DataFrame"
    assert len(df) > 0, "数据不应为空"

    # 验证必要列存在
    required_cols = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
    for col in required_cols:
        assert col in df.columns, f"缺少必要列: {col}"

    # 验证数据类型
    assert pd.api.types.is_datetime64_any_dtype(df["dt"]), "dt列应该是日期类型"
    assert pd.api.types.is_numeric_dtype(df["open"]), "open列应该是数值类型"
    assert pd.api.types.is_numeric_dtype(df["close"]), "close列应该是数值类型"
    assert pd.api.types.is_numeric_dtype(df["high"]), "high列应该是数值类型"
    assert pd.api.types.is_numeric_dtype(df["low"]), "low列应该是数值类型"
    assert pd.api.types.is_numeric_dtype(df["vol"]), "vol列应该是数值类型"
    assert pd.api.types.is_numeric_dtype(df["amount"]), "amount列应该是数值类型"

    # 验证价格关系的正确性
    price_check = (df["high"] >= df[["open", "close"]].max(axis=1)) & (df["low"] <= df[["open", "close"]].min(axis=1))
    assert price_check.all(), "所有K线的价格关系都应该正确(high>=max(open,close), low<=min(open,close))"

    # 验证价格为正数
    assert (df["open"] > 0).all(), "开盘价应该为正数"
    assert (df["close"] > 0).all(), "收盘价应该为正数"
    assert (df["high"] > 0).all(), "最高价应该为正数"
    assert (df["low"] > 0).all(), "最低价应该为正数"
    assert (df["vol"] > 0).all(), "成交量应该为正数"
    assert (df["amount"] > 0).all(), "成交金额应该为正数"

    # 验证不同股票的价格走势差异
    symbols = df["symbol"].unique()
    final_prices = df.groupby("symbol")["close"].last()
    price_changes = df.groupby("symbol")["close"].apply(lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100)

    # 应该有涨有跌，不应该所有股票都是同样的走势
    assert price_changes.std() > 10, "不同股票的涨跌幅应该有足够的差异性"
    assert price_changes.max() > 0, "应该有股票上涨"
    assert price_changes.min() < 0, "应该有股票下跌"

    # 验证成交量与价格波动的相关性
    df["price_volatility"] = abs(df["close"] - df["open"]) / df["open"]
    correlation = df["vol"].corr(df["price_volatility"])
    assert correlation > 0, "成交量与价格波动应该呈正相关"
    assert correlation < 0.8, "相关性不应该过高（避免过于人工化）"

    print(f"Mock数据质量测试通过:")
    print(f"- 数据总量: {len(df):,}行")
    print(f"- 股票数量: {len(symbols)}只")
    print(f"- 时间跨度: {df['dt'].min()} 至 {df['dt'].max()}")
    print(f"- 价格涨跌幅范围: {price_changes.min():.1f}% 至 {price_changes.max():.1f}%")
    print(f"- 成交量与波动率相关性: {correlation:.3f}")


def test_mock_data_consistency():
    """测试mock数据的一致性和可重现性"""
    from czsc import mock

    # 使用相同种子生成两次数据
    df1 = mock.generate_klines(seed=123)
    df2 = mock.generate_klines(seed=123)

    # 验证两次生成的数据完全一致
    pd.testing.assert_frame_equal(df1, df2, "相同种子应该生成相同的数据")

    # 使用不同种子生成数据
    df3 = mock.generate_klines(seed=456)

    # 验证不同种子生成的数据确实不同
    assert not df1.equals(df3), "不同种子应该生成不同的数据"

    # 但数据结构应该相同
    assert df1.columns.equals(df3.columns), "数据列结构应该相同"
    assert len(df1) == len(df3), "数据行数应该相同"
    assert df1["symbol"].nunique() == df3["symbol"].nunique(), "股票数量应该相同"

    print("Mock数据一致性测试通过")
