"""公共 API 兼容性快照测试。

本测试锁定迁移后 ``czsc`` 包对外暴露的公共 API 表面，包括：

    * ``czsc.*`` 顶层应导出的核心名称
    * ``czsc.signals.*`` 应包含的信号子包
    * ``czsc.traders.*`` 应包含的公共名称
    * ``czsc.ta.*`` 技术指标命名空间应包含的名称
    * ``czsc.WeightBacktest`` 必须来自 ``wbt`` 包（架构层面的约束）
    * 已废弃的旧 API（如 ``czsc.dummy_backtest``）必须被移除

期望的 API 集合保存在 ``snapshots/api_v1.json`` 中，新增 / 删除任何
公共名称都需要先更新这份快照，从而对所有破坏性变更形成显式审计。

所有断言都被写成"找不到模块/属性 -> AssertionError"的形式，而不是让
``ImportError`` 直接抛出 —— 这样在 pytest 报告里会被记为 FAIL 而不是
ERROR，可以更清晰地呈现公共 API 的缺失情况。
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

# 公共 API 快照文件（手工维护，每次 API 变更需同步更新）
SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "api_v1.json"


def _load_snapshot() -> dict[str, Any]:
    """读取并解析 API 快照 JSON。"""
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    """安全地 import 一个模块。

    返回 (module, None) 或 (None, error_message)，把 ImportError 等异常
    转成可读字符串，避免 pytest 把它们记成 ERROR 而不是 FAIL。
    """
    try:
        return importlib.import_module(name), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def test_top_level_names_importable() -> None:
    """``czsc.*`` 顶层必须暴露快照中列出的所有公共名称。

    关键断言：``snap["top_level"]`` 中每一个名字都能通过 ``hasattr(czsc, name)``
    访问到，缺失任何一个都视为破坏性变更。
    """
    snap = _load_snapshot()
    czsc, err = _safe_import("czsc")
    assert czsc is not None, f"failed to import czsc: {err}"
    missing = [name for name in snap["top_level"] if not hasattr(czsc, name)]
    assert not missing, (
        f"czsc.* missing {len(missing)} required public names: {missing}"
    )


def test_signal_subpackages_present() -> None:
    """``czsc.signals.*`` 下的所有信号子包必须可以正常 import。

    关键断言：``snap["signal_subpackages"]`` 中每一个子包都能 import
    成功，否则记录失败原因（含异常类型与消息）。
    """
    snap = _load_snapshot()
    failures: list[str] = []
    for sub in snap["signal_subpackages"]:
        mod, err = _safe_import(f"czsc.signals.{sub}")
        if mod is None:
            failures.append(f"czsc.signals.{sub} ({err})")
    assert not failures, (
        f"czsc.signals.* missing {len(failures)} required subpackages: {failures}"
    )


def test_traders_namespace_complete() -> None:
    """``czsc.traders.*`` 必须暴露快照中列出的所有公共名称。"""
    snap = _load_snapshot()
    traders, err = _safe_import("czsc.traders")
    assert traders is not None, f"failed to import czsc.traders: {err}"
    missing = [name for name in snap["traders"] if not hasattr(traders, name)]
    assert not missing, (
        f"czsc.traders.* missing {len(missing)} required public names: {missing}"
    )


def test_ta_namespace_complete() -> None:
    """``czsc.ta.*`` 必须暴露快照中列出的所有技术指标名称。"""
    snap = _load_snapshot()
    ta, err = _safe_import("czsc.ta")
    assert ta is not None, f"failed to import czsc.ta: {err}"
    missing = [name for name in snap["ta"] if not hasattr(ta, name)]
    assert not missing, (
        f"czsc.ta.* missing {len(missing)} required public names: {missing}"
    )


def test_no_legacy_dummy_backtest() -> None:
    """已废弃的旧公共名称必须从 ``czsc.*`` 中移除。

    关键断言：``snap["removed"]`` 中的每一个名字都不应再可访问；任何
    残留都会被视为兼容性回归。
    """
    snap = _load_snapshot()
    czsc, err = _safe_import("czsc")
    assert czsc is not None, f"failed to import czsc: {err}"
    leftover = [name for name in snap["removed"] if hasattr(czsc, name)]
    assert not leftover, (
        f"czsc.* still exposes legacy names that must be removed: {leftover}"
    )


def test_no_czsc_use_python_branch() -> None:
    """已废弃的环境变量必须从 ``czsc.envs`` 中移除。

    关键断言：``snap["removed_envs"]`` 中的每一个名字都不应再可访问。
    """
    snap = _load_snapshot()
    envs, err = _safe_import("czsc.envs")
    assert envs is not None, f"failed to import czsc.envs: {err}"
    leftover = [name for name in snap["removed_envs"] if hasattr(envs, name)]
    assert not leftover, (
        f"czsc.envs still exposes removed env vars: {leftover}"
    )


def test_weight_backtest_comes_from_wbt() -> None:
    """``czsc.WeightBacktest`` 必须就是 ``wbt.WeightBacktest`` 同一个对象。

    架构层面的约束：迁移后 czsc 不再自带 WeightBacktest 实现，而是从
    外部 ``wbt`` 包再导出。同一性（``is``）检查比类型相等更严格，能
    捕获意外的 import 路径漂移。
    """
    czsc, err = _safe_import("czsc")
    assert czsc is not None, f"failed to import czsc: {err}"
    wbt, wbt_err = _safe_import("wbt")
    assert wbt is not None, f"failed to import wbt (hard dep): {wbt_err}"
    assert getattr(czsc, "WeightBacktest", None) is wbt.WeightBacktest, (
        "czsc.WeightBacktest must be the same object as wbt.WeightBacktest"
    )


@pytest.mark.parametrize("module_name", ["czsc.connectors", "czsc.sensors", "czsc.svc"])
def test_retained_subpackages_importable(module_name: str) -> None:
    """保留的子包必须在迁移过程中始终可 import。

    参数化覆盖三个保留子包：
        * ``czsc.connectors`` —— 数据源连接器
        * ``czsc.sensors``    —— 事件检测与特征分析
        * ``czsc.svc``        —— 统计与可视化服务
    """
    mod, err = _safe_import(module_name)
    assert mod is not None, f"failed to import retained subpackage {module_name}: {err}"
