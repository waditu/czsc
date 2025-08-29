# -*- coding: utf-8 -*-
"""
测试mock模块数据质量的单元测试
"""
import pytest
import pandas as pd
import numpy as np


class TestMockDataQuality:
    """Mock数据质量测试类"""

    def test_generate_klines_basic_structure(self):
        """测试generate_klines的基本结构"""
        from czsc import mock

        df = mock.generate_klines(seed=42)

        # 基本结构验证
        assert isinstance(df, pd.DataFrame), "应该返回DataFrame"
        assert len(df) > 0, "数据不应为空"

        # 验证必要列存在
        required_cols = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
        for col in required_cols:
            assert col in df.columns, f"缺少必要列: {col}"

    def test_generate_klines_data_types(self):
        """测试数据类型的正确性"""
        from czsc import mock

        df = mock.generate_klines(seed=42)

        # 验证数据类型
        assert pd.api.types.is_datetime64_any_dtype(df["dt"]), "dt列应该是日期类型"
        assert pd.api.types.is_numeric_dtype(df["open"]), "open列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["close"]), "close列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["high"]), "high列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["low"]), "low列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["vol"]), "vol列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["amount"]), "amount列应该是数值类型"

    def test_generate_klines_price_relationships(self):
        """测试价格关系的正确性"""
        from czsc import mock

        df = mock.generate_klines(seed=42)

        # 验证价格关系正确性
        price_check = (df["high"] >= df[["open", "close"]].max(axis=1)) & (
            df["low"] <= df[["open", "close"]].min(axis=1)
        )
        assert price_check.all(), "所有K线的价格关系都应该正确"

        # 验证价格为正数
        assert (df["open"] > 0).all(), "开盘价应该为正数"
        assert (df["close"] > 0).all(), "收盘价应该为正数"
        assert (df["high"] > 0).all(), "最高价应该为正数"
        assert (df["low"] > 0).all(), "最低价应该为正数"
        assert (df["vol"] > 0).all(), "成交量应该为正数"
        assert (df["amount"] > 0).all(), "成交金额应该为正数"

    def test_generate_klines_market_realism(self):
        """测试市场真实性"""
        from czsc import mock

        df = mock.generate_klines(seed=42)

        # 验证不同股票的价格走势差异
        symbols = df["symbol"].unique()
        assert len(symbols) >= 10, "应该有足够的股票数量"

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

    def test_generate_klines_consistency(self):
        """测试数据一致性和可重现性"""
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

    def test_generate_klines_no_missing_values(self):
        """测试无缺失值"""
        from czsc import mock

        df = mock.generate_klines(seed=42)
        assert df.isnull().sum().sum() == 0, "生成的数据不应该有缺失值"

    def test_generate_cs_factor_basic_structure(self):
        """测试generate_cs_factor的基本结构"""
        from czsc import mock

        df = mock.generate_cs_factor(seed=42)

        # 基本结构验证
        assert isinstance(df, pd.DataFrame), "应该返回DataFrame"
        assert len(df) > 0, "数据不应为空"
        assert "F#RPS#20" in df.columns, "应包含F#RPS#20因子列"
        assert "symbol" in df.columns, "应包含symbol列"
        assert "dt" in df.columns, "应包含dt列"

    def test_generate_cs_factor_data_quality(self):
        """测试因子数据质量"""
        from czsc import mock

        df = mock.generate_cs_factor(seed=42)

        # 验证因子数据的合理性
        factor_values = df["F#RPS#20"]
        assert factor_values.min() >= 0, "RPS因子值应该>=0"
        assert factor_values.max() <= 1, "RPS因子值应该<=1"
        assert not factor_values.isnull().all(), "因子值不应全为空"

    def test_time_series_continuity(self):
        """测试时间序列连续性"""
        from czsc import mock

        df = mock.generate_cs_factor(seed=42)

        # 验证时间序列的连续性
        dates = sorted(df["dt"].unique())
        assert len(dates) > 100, "应该有足够的时间序列数据"

        # 验证不同股票的数据完整性
        symbols = df["symbol"].unique()
        assert len(symbols) >= 10, "应该有足够的股票数量"

        for symbol in symbols[:3]:  # 检查前3个股票
            symbol_data = df[df["symbol"] == symbol]
            assert len(symbol_data) == len(dates), f"股票{symbol}的数据点数量应该与日期数量一致"

    def test_performance_benchmark(self):
        """测试性能基准"""
        from czsc import mock
        import time

        start_time = time.time()
        df = mock.generate_klines(seed=42)
        elapsed_time = time.time() - start_time

        # 性能基准：应该在合理时间内生成大量数据
        assert elapsed_time < 10, f"生成{len(df)}行数据耗时{elapsed_time:.2f}秒，应该在10秒内完成"
        assert len(df) > 50000, "应该生成足够多的数据"

    def test_generate_klines_with_weights(self):
        """测试带权重的K线数据生成"""
        from czsc import mock

        df = mock.generate_klines_with_weights(seed=42)

        # 验证权重列存在
        assert "weight" in df.columns, "应包含weight列"
        assert "price" in df.columns, "应包含price列"

        # 验证权重范围
        weights = df["weight"]
        assert weights.min() >= -1, "权重最小值应该>=-1"
        assert weights.max() <= 1, "权重最大值应该<=1"

    def test_generate_ts_factor(self):
        """测试时序因子数据生成"""
        from czsc import mock

        df = mock.generate_ts_factor(seed=42)

        # 验证因子列存在
        assert "F#SMA#20" in df.columns, "应包含F#SMA#20因子列"

        # 验证SMA因子的合理性（移动平均不应该有异常值）
        sma_values = df["F#SMA#20"]
        assert sma_values.min() >= 0, "SMA因子值应该为正数"
        assert not sma_values.isnull().all(), "SMA因子值不应全为空"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
