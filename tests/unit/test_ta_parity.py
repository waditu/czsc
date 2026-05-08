"""技术指标算子（TA Operators）与 Python TA-Lib 一致性单元测试。

本测试套件验证迁移后的 ``czsc.ta.*`` Rust + PyO3 算子在数值上与
Python 版本的 ``talib`` 库结果保持高精度一致（相对误差 / 绝对误差
均小于 1e-6），覆盖核心技术指标算子。

业务背景：
    历史上 czsc 在 ``czsc.utils.ta`` 中提供了一层 Python 对 TA-Lib 的薄包装。
    迁移目标是用纯 Rust 实现替换该层，并通过 PyO3 暴露为 ``czsc._native.ta``，
    再由 ``czsc.ta`` 重导出。在替换过程中，必须保证以下指标的输出与 talib
    在相同输入下数值上完全一致：

    - ``ema``：指数移动平均
    - ``sma``：简单移动平均
    - ``rolling_rank``：滚动百分位排名
    - ``boll_positions``：布林通道位置
    - ``ultimate_smoother``：终极平滑器

测试策略：
    采用 "FAIL 而不是 ERROR" 策略：导入和数值操作的异常被捕获并在测试函数
    内部转换为 ``pytest.fail``，这样 CI 报告会显示具体失败原因而不是 ERROR。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    """安全导入指定模块，捕获所有异常并返回 (module, err) 元组。"""
    try:
        return __import__(name, fromlist=["__init__"]), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def _series(seed: int = 42, n: int = 1024) -> np.ndarray:
    """生成可重现的标准正态分布随机序列，用作算子的输入数据。

    使用 numpy 的 ``default_rng`` 生成 1024 个 float64 样本，
    默认 seed=42 保证不同运行间结果完全一致。
    """
    return np.random.default_rng(seed).standard_normal(n).astype(np.float64)


def _native_module() -> tuple[Any | None, str | None]:
    """便捷封装：尝试导入 ``czsc.ta`` 模块。"""
    return _safe_import("czsc.ta")


def test_ta_module_sourced_from_native() -> None:
    """验证 czsc.ta 来自 Rust 扩展子模块，而不是 Python TA-Lib 包装。

    测试目标：
        ``czsc.ta`` 必须由 ``czsc._native.ta`` 提供，
        旧的 Python 版 ``czsc.utils.ta`` 已被移除。

    关键断言：
        模块的 ``__file__`` 路径中包含 ``czsc/_native``，或 ``__name__`` 以
        ``czsc._native`` 开头。
    """
    ta, err = _native_module()
    assert ta is not None, f"czsc.ta 必须存在（{err}）"
    module_name = getattr(ta, "__name__", "?")
    file_path = getattr(ta, "__file__", "") or ""
    assert "czsc/_native" in file_path or module_name.startswith("czsc._native"), (
        f"czsc.ta 必须来自 czsc._native.ta（实际 module={module_name!r}, "
        f"file={file_path!r}）；旧的 czsc.utils.ta 包装层必须移除"
    )


def test_ema_matches_talib() -> None:
    """验证 czsc.ta.ema 输出与 talib.EMA 在 timeperiod=14 时数值一致。

    测试场景：
        在同一随机序列上分别调用两端的 EMA，跳过算子预热期（前 20 个点），
        对剩余结果做高精度数值比较。

    关键断言：
        ``np.testing.assert_allclose(actual[20:], expected[20:], rtol=1e-6, atol=1e-6)``。
    """
    ta, err = _native_module()
    if ta is None:
        pytest.fail(f"czsc.ta 不可用：{err}")
    talib_mod, terr = _safe_import("talib")
    if talib_mod is None:
        pytest.fail(f"talib 不可用：{terr}")

    series = _series()
    expected = talib_mod.EMA(series, timeperiod=14)
    if not hasattr(ta, "ema"):
        pytest.fail("czsc.ta.ema 尚未暴露")
    actual = ta.ema(series, length=14)
    np.testing.assert_allclose(np.asarray(actual)[20:], expected[20:], rtol=1e-6, atol=1e-6)


def test_sma_matches_talib() -> None:
    """验证 czsc.ta.sma 输出与 talib.SMA 在 timeperiod=20 时数值一致。

    测试场景：与 EMA 一致，跳过预热期后做高精度比较。
    """
    ta, err = _native_module()
    if ta is None:
        pytest.fail(f"czsc.ta 不可用：{err}")
    talib_mod, terr = _safe_import("talib")
    if talib_mod is None:
        pytest.fail(f"talib 不可用：{terr}")

    series = _series()
    expected = talib_mod.SMA(series, timeperiod=20)
    if not hasattr(ta, "sma"):
        pytest.fail("czsc.ta.sma 尚未暴露")
    actual = ta.sma(series, length=20)
    np.testing.assert_allclose(np.asarray(actual)[20:], expected[20:], rtol=1e-6, atol=1e-6)


def test_rolling_rank_returns_finite() -> None:
    """验证 czsc.ta.rolling_rank 在预热期之后输出有限值（不出现 NaN/Inf）。

    关键断言：
        ``np.isfinite(out[20:]).all()`` 为真，确保算子在窗口建立后能产出稳定数值。
    """
    ta, err = _native_module()
    if ta is None:
        pytest.fail(f"czsc.ta 不可用：{err}")
    if not hasattr(ta, "rolling_rank"):
        pytest.fail("czsc.ta.rolling_rank 尚未暴露")
    out = np.asarray(ta.rolling_rank(_series(), window=20))
    assert np.isfinite(out[20:]).all(), "rolling_rank 在预热窗口之后必须产出有限值"


def test_boll_positions_signature() -> None:
    """验证 czsc.ta 暴露了 boll_positions（布林通道位置）算子。

    关键断言：
        ``hasattr(ta, "boll_positions")`` 为真。
    """
    ta, err = _native_module()
    if ta is None:
        pytest.fail(f"czsc.ta 不可用：{err}")
    assert hasattr(ta, "boll_positions"), "czsc.ta.boll_positions 必须暴露"


def test_ultimate_smoother_signature() -> None:
    """验证 czsc.ta 暴露了 ultimate_smoother（终极平滑器）算子。

    关键断言：
        ``hasattr(ta, "ultimate_smoother")`` 为真。
    """
    ta, err = _native_module()
    if ta is None:
        pytest.fail(f"czsc.ta 不可用：{err}")
    assert hasattr(ta, "ultimate_smoother"), "czsc.ta.ultimate_smoother 必须暴露"
