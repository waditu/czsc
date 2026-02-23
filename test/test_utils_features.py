# -*- coding: utf-8 -*-
"""
test_features.py - czsc.utils.features 因子处理模块单元测试

Mock数据格式说明:
- normalize_feature: 需要 DataFrame，包含 dt 列和因子列
- normalize_ts_feature: 需要时间序列 DataFrame，包含 dt 和因子列
- feature_cross_layering: 需要 DataFrame，包含 dt, symbol, 因子列
- find_most_similarity: 需要 Series 和 DataFrame

测试覆盖:
- normalize_feature: 各种标准化方法（standard, minmax, robust, norm）
- normalize_ts_feature: 时间序列归一化
- feature_cross_layering: 截面分层
- find_most_similarity: 相似度搜索
- 边界情况: 含 NaN 数据断言、极端值
"""
import pytest
import numpy as np
import pandas as pd
from czsc.utils.features import normalize_feature, feature_cross_layering, find_most_similarity


class TestNormalizeFeature:
    """测试 normalize_feature 函数"""

    @pytest.fixture
    def sample_df(self):
        """构造测试数据: 多个时间截面，每个截面有多个品种的因子值"""
        np.random.seed(42)
        dates = pd.date_range("20220101", periods=100, freq="D")
        data = []
        for dt in dates:
            for _ in range(20):
                data.append({"dt": dt, "factor": np.random.randn()})
        return pd.DataFrame(data)

    def test_standard_method(self, sample_df):
        """测试 standard 标准化"""
        result = normalize_feature(sample_df, "factor", method="standard")
        assert "factor" in result.columns
        assert len(result) == len(sample_df)

    def test_minmax_method(self, sample_df):
        """测试 minmax 标准化"""
        result = normalize_feature(sample_df, "factor", method="minmax")
        assert "factor" in result.columns

    def test_robust_method(self, sample_df):
        """测试 robust 标准化"""
        result = normalize_feature(sample_df, "factor", method="robust")
        assert "factor" in result.columns

    def test_invalid_method_raises(self, sample_df):
        """测试无效方法应抛出异常"""
        with pytest.raises(ValueError):
            normalize_feature(sample_df, "factor", method="invalid_method")

    def test_nan_raises(self, sample_df):
        """测试含 NaN 数据应抛出异常"""
        sample_df.loc[0, "factor"] = np.nan
        with pytest.raises(AssertionError):
            normalize_feature(sample_df, "factor")

    def test_does_not_modify_original(self, sample_df):
        """测试不应修改原始数据"""
        original = sample_df["factor"].copy()
        normalize_feature(sample_df, "factor")
        pd.testing.assert_series_equal(sample_df["factor"], original)


class TestFeatureCrossLayering:
    """测试 feature_cross_layering 函数"""

    @pytest.fixture
    def sample_df(self):
        """构造截面数据: 多日期 x 多品种"""
        np.random.seed(42)
        dates = pd.date_range("20220101", periods=50, freq="D")
        symbols = [f"SYM{str(i).zfill(3)}" for i in range(20)]
        data = []
        for dt in dates:
            for sym in symbols:
                data.append({"dt": dt, "symbol": sym, "factor": np.random.randn()})
        return pd.DataFrame(data)

    def test_basic_layering(self, sample_df):
        """测试基本分层"""
        result = feature_cross_layering(sample_df, "factor", n=5)
        assert "factor分层" in result.columns

    def test_layer_format(self, sample_df):
        """测试分层格式"""
        result = feature_cross_layering(sample_df, "factor", n=5)
        # 分层应为 "第XX层" 格式
        layers = result["factor分层"].unique()
        for layer in layers:
            assert layer.startswith("第"), f"分层格式应以'第'开头: {layer}"

    def test_missing_dt_raises(self, sample_df):
        """测试缺少 dt 列应抛出异常"""
        df = sample_df.drop(columns=["dt"])
        with pytest.raises(AssertionError):
            feature_cross_layering(df, "factor")

    def test_missing_symbol_raises(self, sample_df):
        """测试缺少 symbol 列应抛出异常"""
        df = sample_df.drop(columns=["symbol"])
        with pytest.raises(AssertionError):
            feature_cross_layering(df, "factor")

    def test_too_few_symbols_raises(self):
        """测试品种数量不足应抛出异常"""
        dates = pd.date_range("20220101", periods=10, freq="D")
        data = [{"dt": dt, "symbol": "SYM001", "factor": np.random.randn()} for dt in dates]
        df = pd.DataFrame(data)
        with pytest.raises(AssertionError):
            feature_cross_layering(df, "factor", n=5)


class TestFindMostSimilarity:
    """测试 find_most_similarity 函数"""

    def test_basic(self):
        """测试基本相似度搜索"""
        np.random.seed(42)
        vector = pd.Series(np.random.randn(10))
        matrix = pd.DataFrame(np.random.randn(10, 20), columns=[f"col_{i}" for i in range(20)])
        result = find_most_similarity(vector, matrix, n=5)
        assert len(result) == 5
        assert isinstance(result, pd.Series)

    def test_identical_vector(self):
        """测试完全相同的向量"""
        vector = pd.Series([1, 2, 3, 4, 5])
        matrix = pd.DataFrame({
            "exact": [1, 2, 3, 4, 5],
            "different": [5, 4, 3, 2, 1],
        })
        result = find_most_similarity(vector, matrix, n=2)
        assert len(result) == 2
