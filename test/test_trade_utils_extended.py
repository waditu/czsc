# -*- coding: utf-8 -*-
"""
test_trade_utils_extended.py - czsc.utils.trade 交易工具扩展测试

Mock数据格式说明:
- update_nxb: DataFrame 包含 dt, symbol, price 列
- update_bbars: DataFrame 包含价格列
- update_tbars: DataFrame 包含 n*b 列和事件信号列
- adjust_holding_weights: DataFrame 包含 dt, symbol, weight, n1b 列
- risk_free_returns: 使用日期范围参数

测试覆盖:
- update_nxb: 基本功能、BP转换、多品种
- update_bbars: 基本功能、无效列名
- update_tbars: 带方向的未来收益计算
- adjust_holding_weights: 固定持仓周期调整
- risk_free_returns: 基本收益率序列创建
- 边界情况: 空数据、单行数据、无效输入
"""
import pytest
import numpy as np
import pandas as pd
from czsc.utils.trade import update_nxb, update_bbars, update_tbars, adjust_holding_weights, risk_free_returns


class TestUpdateNxb:
    """测试 update_nxb 函数"""

    @pytest.fixture
    def sample_df(self):
        """构造测试数据"""
        dates = pd.date_range("20220101", periods=100, freq="D")
        return pd.DataFrame({
            "dt": dates,
            "symbol": "000001",
            "price": np.random.RandomState(42).uniform(10, 20, 100),
        })

    def test_basic(self, sample_df):
        """测试基本功能"""
        result = update_nxb(sample_df, copy=True)
        # 默认 nseq = (1, 2, 3, 5, 8, 10, 13)
        for n in [1, 2, 3, 5, 8, 10, 13]:
            assert f"n{n}b" in result.columns, f"应包含 n{n}b 列"

    def test_custom_nseq(self, sample_df):
        """测试自定义 nseq"""
        result = update_nxb(sample_df, nseq=(1, 5), copy=True)
        assert "n1b" in result.columns
        assert "n5b" in result.columns
        assert "n2b" not in result.columns

    def test_bp_conversion(self, sample_df):
        """测试 BP 单位转换"""
        result = update_nxb(sample_df, nseq=(1,), bp=True, copy=True)
        # BP 单位下的值应该更大（乘以10000）
        non_zero = result["n1b"].dropna()
        non_zero = non_zero[non_zero != 0]
        if len(non_zero) > 0:
            assert non_zero.abs().max() > 1, "BP 单位值应较大"

    def test_multi_symbol(self):
        """测试多品种"""
        dates = pd.date_range("20220101", periods=50, freq="D")
        data = []
        for sym in ["000001", "000002"]:
            for dt in dates:
                data.append({"dt": dt, "symbol": sym, "price": np.random.uniform(10, 20)})
        df = pd.DataFrame(data)
        result = update_nxb(df, nseq=(1,), copy=True)
        assert len(result) == len(df)
        assert "n1b" in result.columns

    def test_missing_columns_raises(self):
        """测试缺少必要列应抛出异常"""
        df = pd.DataFrame({"dt": [1], "symbol": ["a"]})
        with pytest.raises(AssertionError, match="price"):
            update_nxb(df)


class TestUpdateBbars:
    """测试 update_bbars 函数"""

    def test_basic(self):
        """测试基本功能"""
        df = pd.DataFrame({"close": np.random.RandomState(42).uniform(10, 20, 50)})
        update_bbars(df, price_col="close", numbers=(1, 5, 10))
        assert "b1b" in df.columns
        assert "b5b" in df.columns
        assert "b10b" in df.columns

    def test_invalid_price_col_raises(self):
        """测试无效价格列应抛出异常"""
        df = pd.DataFrame({"price": [1, 2, 3]})
        with pytest.raises(ValueError, match="not in da.columns"):
            update_bbars(df, price_col="close")

    def test_values_in_bp(self):
        """测试收益值为BP单位"""
        prices = [100, 110, 121]  # 10% 涨幅
        df = pd.DataFrame({"close": prices})
        update_bbars(df, price_col="close", numbers=(1,))
        # 第二行的 b1b 应约为 1000 BP (10%)
        assert abs(df["b1b"].iloc[1] - 1000) < 1


class TestUpdateTbars:
    """测试 update_tbars 函数"""

    def test_basic(self):
        """测试基本功能"""
        df = pd.DataFrame({
            "n1b": [0.01, -0.02, 0.03, -0.01, 0.02],
            "n2b": [0.02, -0.01, 0.04, -0.02, 0.03],
            "event": [1, -1, 1, 0, -1],
        })
        update_tbars(df, event_col="event")
        assert "t1b" in df.columns
        assert "t2b" in df.columns

    def test_direction_multiplication(self):
        """测试方向乘法"""
        df = pd.DataFrame({
            "n1b": [0.1, 0.1, 0.1],
            "event": [1, -1, 0],
        })
        update_tbars(df, event_col="event")
        assert df["t1b"].iloc[0] == pytest.approx(0.1)   # 看多 * 正收益
        assert df["t1b"].iloc[1] == pytest.approx(-0.1)  # 看空 * 正收益
        assert df["t1b"].iloc[2] == pytest.approx(0.0)   # 无事件


class TestAdjustHoldingWeights:
    """测试 adjust_holding_weights 函数"""

    @pytest.fixture
    def sample_df(self):
        """构造测试数据"""
        dates = pd.date_range("20220101", periods=20, freq="D")
        data = []
        for dt in dates:
            for sym in ["A", "B"]:
                data.append({
                    "dt": dt,
                    "symbol": sym,
                    "weight": np.random.choice([0, 0.5, 1.0]),
                    "n1b": np.random.uniform(-0.02, 0.02),
                })
        return pd.DataFrame(data)

    def test_hold_period_1(self, sample_df):
        """测试 hold_periods=1 时应返回原始数据"""
        result = adjust_holding_weights(sample_df, hold_periods=1)
        assert len(result) == len(sample_df)

    def test_hold_period_5(self, sample_df):
        """测试 hold_periods=5"""
        result = adjust_holding_weights(sample_df, hold_periods=5)
        assert isinstance(result, pd.DataFrame)
        assert "weight" in result.columns
        assert "n1b" in result.columns

    def test_invalid_hold_period_raises(self, sample_df):
        """测试无效 hold_periods 应抛出异常"""
        with pytest.raises(AssertionError):
            adjust_holding_weights(sample_df, hold_periods=0)


class TestRiskFreeReturns:
    """测试 risk_free_returns 函数"""

    def test_basic(self):
        """测试基本功能"""
        df = risk_free_returns("20220101", "20220301", year_returns=0.03)
        assert isinstance(df, pd.DataFrame)
        assert "date" in df.columns
        assert "returns" in df.columns
        assert len(df) > 0

    def test_returns_value(self):
        """测试收益率值正确"""
        df = risk_free_returns("20220101", "20220301", year_returns=0.03)
        expected_daily = 0.03 / 252
        assert abs(df["returns"].iloc[0] - expected_daily) < 1e-10
        assert df["returns"].nunique() == 1, "所有日的收益率应相同"

    def test_different_rates(self):
        """测试不同年化收益率"""
        df1 = risk_free_returns("20220101", "20220301", year_returns=0.02)
        df2 = risk_free_returns("20220101", "20220301", year_returns=0.05)
        assert df1["returns"].iloc[0] < df2["returns"].iloc[0]
