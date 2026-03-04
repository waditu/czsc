# -*- coding: utf-8 -*-
"""
性能对比测试：weights_convert (pandas) vs weights_convert_pl (polars)

使用 mock 的 5 分钟 A 股数据，覆盖三年以上时间、6 个股票，
对比 pandas 版本和 polars 版本的性能差异。
"""
import numpy as np
import pandas as pd
import pytest
import time

from czsc.mock import generate_symbol_kines
from czsc.utils.weights_convert import weights_convert as weights_convert_pd

try:
    import polars  # noqa: F401

    from czsc.utils.weights_convert_pl import weights_convert as weights_convert_pl
except ImportError:
    weights_convert_pl = None

pytestmark = pytest.mark.skipif(weights_convert_pl is None, reason="polars is not installed")


# ==================== 测试数据生成 ====================

SYMBOLS = ["000001", "000002", "000003", "000004", "000005", "000006"]
SDT = "20210101"
EDT = "20240101"
FREQ = "5分钟"


@pytest.fixture(scope="module")
def benchmark_weights_df():
    """生成三年以上、6 只股票的 5 分钟权重数据"""
    np.random.seed(42)
    dfs = []
    for sym in SYMBOLS:
        df = generate_symbol_kines(sym, FREQ, sdt=SDT, edt=EDT, seed=42)
        df["weight"] = np.random.uniform(-0.5, 0.8, len(df))
        # 20% 概率权重为 0
        mask = np.random.random(len(df)) < 0.2
        df.loc[mask, "weight"] = 0.0
        dfs.append(df[["dt", "symbol", "weight"]])
    return pd.concat(dfs, ignore_index=True)


# ==================== 正确性测试 ====================


def test_pl_matches_pd_basic():
    """验证 polars 版本与 pandas 版本在基础场景下结果一致"""
    data = {
        "dt": pd.to_datetime(
            ["2024-01-01 09:30:00", "2024-01-01 10:00:00", "2024-01-01 11:00:00"]
        ),
        "symbol": ["AAPL"] * 3,
        "weight": [0.0, 0.5, 0.2],
    }
    df = pd.DataFrame(data)
    result_pd = weights_convert_pd(df, rule="t+1")
    result_pl = weights_convert_pl(df, rule="t+1")
    pd.testing.assert_series_equal(
        result_pd["weight"].reset_index(drop=True),
        result_pl["weight"].reset_index(drop=True),
        check_names=False,
    )


def test_pl_matches_pd_multi_symbol():
    """验证多品种场景下 polars 与 pandas 结果一致"""
    symbols_data = []
    for symbol in ["AAPL", "MSFT", "GOOG"]:
        data = {
            "dt": pd.to_datetime(
                [
                    "2024-01-01 09:30:00",
                    "2024-01-01 10:00:00",
                    "2024-01-01 11:00:00",
                    "2024-01-02 09:30:00",
                    "2024-01-02 10:00:00",
                ]
            ),
            "symbol": [symbol] * 5,
            "weight": [0.0, 0.5, 0.2, 0.3, 0.0],
        }
        symbols_data.append(pd.DataFrame(data))
    df = pd.concat(symbols_data, ignore_index=True)
    result_pd = weights_convert_pd(df, rule="t+1")
    result_pl = weights_convert_pl(df, rule="t+1")
    pd.testing.assert_series_equal(
        result_pd["weight"].reset_index(drop=True),
        result_pl["weight"].reset_index(drop=True),
        check_names=False,
    )


def test_pl_matches_pd_large_data(benchmark_weights_df):
    """验证大规模数据下 polars 与 pandas 结果一致"""
    result_pd = weights_convert_pd(benchmark_weights_df, rule="t+1")
    result_pl = weights_convert_pl(benchmark_weights_df, rule="t+1")
    pd.testing.assert_series_equal(
        result_pd["weight"].reset_index(drop=True),
        result_pl["weight"].reset_index(drop=True),
        check_names=False,
        atol=1e-10,
    )


def test_pl_rule_none():
    """验证 rule='none' 行为一致"""
    data = {
        "dt": pd.to_datetime(["2024-01-01 09:30:00", "2024-01-01 10:00:00"]),
        "symbol": ["AAPL"] * 2,
        "weight": [0.0, 0.5],
    }
    df = pd.DataFrame(data)
    result_pd = weights_convert_pd(df, rule="none")
    result_pl = weights_convert_pl(df, rule="none")
    pd.testing.assert_frame_equal(result_pd, result_pl)


def test_pl_empty_dataframe():
    """验证空 DataFrame 行为一致"""
    df = pd.DataFrame(columns=["dt", "symbol", "weight"])
    df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    df["weight"] = df["weight"].astype(float)
    result_pd = weights_convert_pd(df, rule="t+1")
    result_pl = weights_convert_pl(df, rule="t+1")
    assert len(result_pd) == 0
    assert len(result_pl) == 0


def test_pl_invalid_rule():
    """验证无效规则抛出异常"""
    df = pd.DataFrame(columns=["dt", "symbol", "weight"])
    with pytest.raises(ValueError, match="不支持的转换规则"):
        weights_convert_pl(df, rule="invalid")


# ==================== 性能基准测试 ====================


def test_benchmark_performance(benchmark_weights_df):
    """性能基准测试：对比 pandas 和 polars 版本的执行时间

    使用 6 只股票、3 年以上的 5 分钟数据进行测试。
    """
    n_rows = len(benchmark_weights_df)
    n_symbols = benchmark_weights_df["symbol"].nunique()
    dt_range = f"{benchmark_weights_df['dt'].min()} ~ {benchmark_weights_df['dt'].max()}"

    print(f"\n{'='*60}")
    print(f"性能基准测试")
    print(f"  数据行数: {n_rows:,}")
    print(f"  品种数量: {n_symbols}")
    print(f"  时间范围: {dt_range}")
    print(f"{'='*60}")

    # Pandas 版本计时
    n_runs = 3
    times_pd = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        result_pd = weights_convert_pd(benchmark_weights_df, rule="t+1")
        t1 = time.perf_counter()
        times_pd.append(t1 - t0)

    # Polars 版本计时
    times_pl = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        result_pl = weights_convert_pl(benchmark_weights_df, rule="t+1")
        t1 = time.perf_counter()
        times_pl.append(t1 - t0)

    best_pd = min(times_pd)
    best_pl = min(times_pl)
    speedup = best_pd / best_pl

    print(f"\n  Pandas 版本: {best_pd:.4f}s (best of {n_runs})")
    print(f"  Polars 版本: {best_pl:.4f}s (best of {n_runs})")
    print(f"  加速比: {speedup:.1f}x")
    print(f"{'='*60}\n")

    # 验证结果一致性
    pd.testing.assert_series_equal(
        result_pd["weight"].reset_index(drop=True),
        result_pl["weight"].reset_index(drop=True),
        check_names=False,
        atol=1e-10,
    )

    # Polars 版本应快于 Pandas（使用保守阈值以适应不同 CI 环境）
    assert speedup > 1.5, f"Polars 版本应至少快 1.5 倍，实际加速比: {speedup:.1f}x"
