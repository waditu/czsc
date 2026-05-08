"""信号函数命名空间一致性单元测试。

本测试套件验证 ``czsc.signals.*`` 命名空间下的信号函数已完整迁移到
in-repo 的 Rust 扩展 ``czsc._native.signals``，并满足以下契约：

业务背景：
    czsc 的信号体系按类别组织（bar / cxt / tas / vol / pressure / obv / cvolp），
    每个子包提供若干信号函数。早期版本中部分实现来自外部 ``rs_czsc`` 包，
    迁移过程要求所有信号函数统一来自 in-repo 的 Rust 扩展，并通过薄层
    重导出（thin re-export）暴露在 Python 命名空间。

测试覆盖：
    - 每个必需子包都可以被 import；
    - 每个子包至少暴露 ``MIN_FUNCS_PER_SUBPACKAGE`` 个可调用对象；
    - 每个可调用对象的 ``__module__`` 必须以 ``czsc.`` 开头（来源于 czsc._native）；
    - ``czsc._native`` 必须存在 ``signals`` 子模块。

注意：
    本文件只锁定**命名空间契约**（namespace contract），即"接口存在且来源
    正确"；逐个信号函数的数值一致性（per-function value parity）将在
    迁移过程中通过其它测试逐步补齐。
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# 信号体系按类别组织，下列子包均必须存在
REQUIRED_SUBPACKAGES = ("bar", "cxt", "tas", "vol", "pressure", "obv", "cvolp")
# 每个子包至少应暴露的公开可调用对象数量阈值
MIN_FUNCS_PER_SUBPACKAGE = 3


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    """安全导入指定模块，捕获所有异常并返回 (module, err) 元组。"""
    try:
        return importlib.import_module(name), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


# 参数化覆盖所有必需信号子包，每个子包验证其可被导入
@pytest.mark.parametrize("sub", REQUIRED_SUBPACKAGES)
def test_signal_subpackage_exists(sub: str) -> None:
    """验证给定信号子包在迁移完成后可被成功 import。

    关键断言：
        ``importlib.import_module(f"czsc.signals.{sub}")`` 不抛异常且返回非 None。
    """
    mod, err = _safe_import(f"czsc.signals.{sub}")
    assert mod is not None, f"czsc.signals.{sub} 必须可被导入（{err}）"


# 参数化覆盖所有必需信号子包，每个子包验证其暴露足够数量的函数
@pytest.mark.parametrize("sub", REQUIRED_SUBPACKAGES)
def test_signal_subpackage_has_functions(sub: str) -> None:
    """验证给定信号子包至少暴露 ``MIN_FUNCS_PER_SUBPACKAGE`` 个可调用对象。

    测试场景：
        通过 ``dir(mod)`` 列出所有非下划线开头的属性，过滤出可调用对象，
        并对其数量做下限校验。

    关键断言：
        子包公开的可调用对象数量 ≥ ``MIN_FUNCS_PER_SUBPACKAGE``。
    """
    mod, err = _safe_import(f"czsc.signals.{sub}")
    if mod is None:
        pytest.fail(f"无法导入 czsc.signals.{sub}: {err}")
    funcs = [name for name in dir(mod) if not name.startswith("_") and callable(getattr(mod, name))]
    assert len(funcs) >= MIN_FUNCS_PER_SUBPACKAGE, (
        f"czsc.signals.{sub} 必须至少暴露 {MIN_FUNCS_PER_SUBPACKAGE} 个 信号函数；实际找到 {len(funcs)} 个：{funcs}"
    )


# 参数化覆盖所有必需信号子包，每个子包验证函数来源
@pytest.mark.parametrize("sub", REQUIRED_SUBPACKAGES)
def test_signal_subpackage_sourced_from_native(sub: str) -> None:
    """验证子包内每个函数都来源于 czsc.* 命名空间，而不是外部包。

    测试目标：
        确保 czsc.signals 是 ``czsc._native.signals`` 的薄重导出层，
        而不是含有来自 ``rs_czsc`` 等外部模块的实现。

    关键断言：
        遍历每个公开可调用对象，其 ``__module__`` 必须以 ``czsc.`` 开头。
    """
    mod, err = _safe_import(f"czsc.signals.{sub}")
    if mod is None:
        pytest.fail(f"无法导入 czsc.signals.{sub}: {err}")
    funcs = [getattr(mod, n) for n in dir(mod) if not n.startswith("_") and callable(getattr(mod, n))]
    if not funcs:
        pytest.fail(f"czsc.signals.{sub} 中没有任何可调用对象")

    foreign = [f for f in funcs if not getattr(f, "__module__", "").startswith("czsc.")]
    assert not foreign, (
        f"czsc.signals.{sub} 中包含 {len(foreign)} 个来源于 czsc.* 之外的函数 "
        f"(例如 {foreign[0].__module__}.{foreign[0].__name__})；"
        "必须全部从 czsc._native.signals 重导出"
    )


def test_native_signals_module_exists() -> None:
    """验证 czsc._native 已注册 signals 子模块。

    测试目标：
        Rust 扩展 ``czsc._native`` 在编译时通过 PyO3 注册了名为 ``signals``
        的子模块，作为信号函数的最终来源。

    关键断言：
        ``czsc._native`` 模块存在且具备 ``signals`` 属性。
    """
    native, err = _safe_import("czsc._native")
    assert native is not None, f"czsc._native 必须存在（maturin 构建产物）（{err}）"
    assert hasattr(native, "signals"), "czsc._native.signals 必须是已注册的 PyO3 子模块"
