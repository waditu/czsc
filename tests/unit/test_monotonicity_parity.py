"""``czsc.monotonicity`` 的 Rust 实现 vs scipy 行为一致性测试。

2026-05-17 PR-D：``monotonicity`` 从 Python 端 ``scipy.stats.spearmanr``
切到 Rust 实现 ``czsc._native.monotonicity``。本测试对比 50 组随机种子下
两个实现的输出，要求绝对误差 ≤ 1e-10；同时显式覆盖 scipy 文档承诺的
退化情形（空序列 / 单元素 / 含 NaN / 全相等）。

通过后可视为 Rust 实现"行为与 scipy 等价"的契约证据；下个 release 周期
可选择删除本测试，因为 Rust 单测（``crates/czsc-utils/src/monotonicity.rs``）
已覆盖核心算法。
"""

from __future__ import annotations

import math
import random

import pytest
from scipy.stats import spearmanr

from czsc import monotonicity as monotonicity_via_top
from czsc._native import monotonicity as monotonicity_rust


def test_monotonicity_top_level_is_rust_native():
    """顶层 ``czsc.monotonicity`` 必须是 Rust 实现的纯透传（开发宪法第一条）。"""
    assert monotonicity_via_top is monotonicity_rust


@pytest.mark.parametrize("seed", list(range(50)))
def test_rust_matches_scipy(seed: int) -> None:
    """50 组随机种子下 Rust 结果与 scipy.stats.spearmanr 等价（atol 1e-10）。"""
    rng = random.Random(seed)
    n = rng.choice([2, 5, 10, 50, 200, 1000])
    seq = [rng.uniform(-100.0, 100.0) for _ in range(n)]
    rust = monotonicity_rust(seq)
    py = spearmanr(seq, list(range(n))).statistic
    if math.isnan(rust) or math.isnan(py):
        assert math.isnan(rust) and math.isnan(py), f"NaN status mismatch: rust={rust} py={py}"
    else:
        assert abs(rust - py) <= 1e-10, f"rust={rust} py={py} diff={abs(rust - py):.2e}"


def test_monotonic_strict_increasing_one() -> None:
    """严格单调递增 → 系数应为 1.0（容差 1e-12）。"""
    assert abs(monotonicity_rust(list(range(50))) - 1.0) <= 1e-12


def test_monotonic_strict_decreasing_minus_one() -> None:
    """严格单调递减 → 系数应为 -1.0（容差 1e-12）。"""
    assert abs(monotonicity_rust(list(range(50, 0, -1))) - (-1.0)) <= 1e-12


@pytest.mark.parametrize(
    "seq",
    [
        [],
        [3.14],
        [1.0, 1.0, 1.0, 1.0],  # std=0
        [1.0, float("nan"), 2.0],  # NaN propagates
    ],
)
def test_degenerate_returns_nan(seq: list[float]) -> None:
    """退化情形（空 / 单元素 / 全相等 / 含 NaN）必须返回 NaN，与 scipy 对齐。"""
    assert math.isnan(monotonicity_rust(seq))


def test_duplicates_average_rank() -> None:
    """tied values 应使用平均秩（``rankdata method="average"``）。"""
    # spearmanr([10,20,20,30], [0,1,2,3]).statistic = 0.9486832980505138
    assert abs(monotonicity_rust([10.0, 20.0, 20.0, 30.0]) - 0.948_683_298_050_513_8) <= 1e-12
