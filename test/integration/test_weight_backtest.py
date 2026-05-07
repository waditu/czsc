"""权重回测（WeightBacktest）跨包集成测试。

本测试套件验证 ``czsc`` 顶层命名空间中暴露的权重回测相关 API 是直接来自
外部 ``wbt`` 包的对象重导出（re-export），即对象身份必须完全一致。

业务背景：
    ``WeightBacktest``、``daily_performance``、``top_drawdowns`` 这三个 API
    在 czsc 中不再维护并行实现，而是统一由独立的 ``wbt`` 包提供，并将
    ``wbt`` 列为 czsc 的硬依赖（hard dependency）。这样可以避免在两个包
    之间出现实现漂移（implementation drift），同时让 wbt 可以被其它项目
    单独使用。

测试覆盖：
    - ``wbt`` 包必须可被成功导入
    - ``czsc.WeightBacktest`` 必须与 ``wbt.WeightBacktest`` 是同一对象
    - ``czsc.daily_performance``、``czsc.top_drawdowns`` 同上
    - ``czsc.WeightBacktest`` 不得来自 ``rs_czsc`` 模块（已废弃的来源）
"""

from __future__ import annotations

from typing import Any

import pytest


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    """安全地按名称导入模块，捕获所有异常并以元组形式返回。

    导入成功时返回 ``(module, None)``；导入失败时返回 ``(None, error_msg)``，
    其中 ``error_msg`` 包含异常类型名和异常消息，便于失败时输出可读的诊断信息。
    """
    try:
        return __import__(name, fromlist=["__init__"]), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


# 参数化覆盖三个必须从 wbt 重导出的 API 名称
@pytest.mark.parametrize(
    "attr_name",
    ["WeightBacktest", "daily_performance", "top_drawdowns"],
)
def test_czsc_attr_is_wbt_attr(attr_name: str) -> None:
    """验证 czsc 顶层属性与 wbt 中对应属性是同一个 Python 对象。

    测试场景：
        参数化执行三次，分别校验 ``WeightBacktest`` 类、``daily_performance``
        和 ``top_drawdowns`` 函数。

    关键断言：
        使用 Python 的 ``is`` 运算符断言对象身份完全相同（不是等价，而是同一对象），
        以此防止 czsc 私下维护一个并行实现或重新包装的副本。
    """
    czsc, czsc_err = _safe_import("czsc")
    assert czsc is not None, f"failed to import czsc: {czsc_err}"
    wbt, wbt_err = _safe_import("wbt")
    if wbt is None:
        pytest.fail(
            f"wbt 必须作为硬依赖存在 ({wbt_err})；"
            f"czsc.{attr_name} 必须从 wbt 重导出"
        )

    czsc_attr = getattr(czsc, attr_name, None)
    wbt_attr = getattr(wbt, attr_name, None)

    if czsc_attr is None:
        pytest.fail(f"czsc.{attr_name} 缺失；期望从 wbt 重导出")
    if wbt_attr is None:
        pytest.fail(f"wbt.{attr_name} 缺失；请检查 wbt 版本是否正确")

    assert czsc_attr is wbt_attr, (
        f"czsc.{attr_name} 必须与 wbt.{attr_name} 是同一对象 "
        f"(实际 czsc.{attr_name}={czsc_attr!r} 来自 "
        f"{getattr(czsc_attr, '__module__', '?')}, wbt.{attr_name}={wbt_attr!r} "
        f"来自 {getattr(wbt_attr, '__module__', '?')})"
    )


def test_no_residual_rs_czsc_dependency() -> None:
    """验证 czsc.WeightBacktest 不再通过 rs_czsc 路由。

    测试目标：
        确保 czsc 已经完全切换为通过 wbt 提供 WeightBacktest，
        而不是继续依赖已经废弃的 ``rs_czsc`` PyPI 包。

    关键断言：
        ``czsc.WeightBacktest.__module__`` 中不得包含 ``rs_czsc`` 字符串。
    """
    czsc, err = _safe_import("czsc")
    assert czsc is not None, err
    # 该属性必须由 wbt 提供，而不是来自 rs_czsc
    wb = getattr(czsc, "WeightBacktest", None)
    if wb is None:
        pytest.fail("czsc.WeightBacktest 缺失")
    module = getattr(wb, "__module__", "?")
    assert "rs_czsc" not in module, (
        f"czsc.WeightBacktest 仍然通过 {module!r} 路由；"
        f"必须替换为 wbt.WeightBacktest"
    )
