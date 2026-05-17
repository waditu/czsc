"""二阶段清理 ratchet：17 个非缠论核心 API 的删除进度追踪。

关联：
- 飞书任务：《20260517 清理非核心API接口》
  https://s0cqcxuy3p.feishu.cn/wiki/NGlFw8qXoiGNcnkkDMacNKXhnph
- 执行方案：《清理非核心 API 接口 v2 — 执行方案与验收标准》
  https://s0cqcxuy3p.feishu.cn/docx/H0UodenI2oBvzHx0IeYc05rCn7e

## 设计

与上一波 PR-1 (`test_api_no_streamlit.py`) 同构的双轨 ratchet，PR-A 阶段全部
``xfail(strict=True)``。后续 PR-B / PR-C 把 17 个 API 与 3 个模块删除后，对应
用例从 ``xfail`` 转为 unexpectedly passed（XPASS strict），CI 立即红，提示
维护者把 ``xfail`` 摘掉 —— 形成显式的进度 ratchet。

### A 组（运行时 hasattr）

锚定 (module_path, attr_name) 的 31 个组合，分两阶段：

  - **PR-B 已落地（18 个，常规 PASS）**：4 个 eda、2 个 stats、2 个 utils 共 8 个
    API × 多模块入口（czsc / czsc.utils / czsc.utils.analysis / czsc.eda） = 18 个组合。
  - **PR-C 待落地（13 个，xfail strict）**：KlineChart + plot_czsc_chart × 3
    模块入口（czsc / czsc.utils.plotting / czsc.utils.plotting.kline）= 6 个 +
    7 个 plot_* 在 czsc.utils.plotting = 13 个组合。

### B 组（模块级 import）

锚定 3 个完全删除的模块：

  - ``czsc.utils.plotting.backtest``    PR-C 整文件 git rm
  - ``czsc.utils.plotting.common``      PR-C 整文件 git rm（仅服务于 backtest）
  - ``czsc.utils.plotting._macd``       PR-C 整文件 git rm（仅服务于 KlineChart.add_macd）

### 摘 xfail 的协议

PR-B / PR-C 当 PR 内：删除 API → 对应用例从 ``xfail`` 转为 XPASS strict（CI 红）
→ 在 *同一 PR* 中把 ``xfail`` 标记去掉，用例转为常规 PASS（CI 绿）。
本测试文件本身在 PR-D 完成后应当 0 个 xfail，全部常规 PASS。
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# (parent_module, attr_name, batch_marker) —— batch 仅作可读注释，无运行时语义
#
# PR-B 已删除 18 个 B-batch 条目，对应用例转为常规 PASS（在 PR-B commit 中已摘 xfail）。
# 下方仅保留 PR-C 待删的 13 个 C-batch 条目，仍 xfail strict。
SECONDARY_API_REMOVALS_DONE_B: list[tuple[str, str]] = [
    # --- PR-B：czsc.eda 4 个工具函数 + czsc 顶层别名 ---
    ("czsc", "cal_yearly_days"),
    ("czsc", "weights_simple_ensemble"),
    ("czsc", "cal_trade_price"),
    ("czsc", "turnover_rate"),
    ("czsc.eda", "cal_yearly_days"),
    ("czsc.eda", "weights_simple_ensemble"),
    ("czsc.eda", "cal_trade_price"),
    ("czsc.eda", "turnover_rate"),
    # --- PR-B：czsc/utils/__init__.py 2 个工具函数 ---
    ("czsc", "create_grid_params"),
    ("czsc", "mac_address"),
    ("czsc.utils", "create_grid_params"),
    ("czsc.utils", "mac_address"),
    # --- PR-B：czsc/utils/analysis/stats.py 2 个统计函数 ---
    ("czsc", "holds_performance"),
    ("czsc", "rolling_daily_performance"),
    ("czsc.utils", "holds_performance"),
    ("czsc.utils", "rolling_daily_performance"),
    ("czsc.utils.analysis", "holds_performance"),
    ("czsc.utils.analysis", "rolling_daily_performance"),
]

SECONDARY_API_REMOVALS: list[tuple[str, str, str]] = [
    # --- PR-C：plotting/kline.py 2 个（KlineChart + plot_czsc_chart） ---
    ("czsc", "KlineChart", "C"),
    ("czsc", "plot_czsc_chart", "C"),
    ("czsc.utils.plotting", "KlineChart", "C"),
    ("czsc.utils.plotting", "plot_czsc_chart", "C"),
    ("czsc.utils.plotting.kline", "KlineChart", "C"),
    ("czsc.utils.plotting.kline", "plot_czsc_chart", "C"),
    # --- PR-C：plotting/backtest.py 7 个 plot_* 函数 ---
    ("czsc.utils.plotting", "plot_cumulative_returns", "C"),
    ("czsc.utils.plotting", "plot_drawdown_analysis", "C"),
    ("czsc.utils.plotting", "plot_daily_return_distribution", "C"),
    ("czsc.utils.plotting", "plot_monthly_heatmap", "C"),
    ("czsc.utils.plotting", "plot_backtest_stats", "C"),
    ("czsc.utils.plotting", "plot_colored_table", "C"),
    ("czsc.utils.plotting", "plot_long_short_comparison", "C"),
]

# 完全删除的模块（PR-C 整文件 git rm）
REMOVED_MODULES: list[str] = [
    "czsc.utils.plotting.backtest",
    "czsc.utils.plotting.common",
    "czsc.utils.plotting._macd",
]


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    try:
        return importlib.import_module(name), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


@pytest.mark.parametrize(
    ("parent_module", "attr_name"),
    SECONDARY_API_REMOVALS_DONE_B,
    ids=[f"{m}.{n}" for m, n in SECONDARY_API_REMOVALS_DONE_B],
)
def test_secondary_api_removed_done_b(parent_module: str, attr_name: str) -> None:
    """PR-B 已落地：18 个工具/分析函数的入口已删，这是常规防回归断言。"""
    mod, err = _safe_import(parent_module)
    assert mod is not None, f"failed to import {parent_module}: {err}"
    assert not hasattr(mod, attr_name), f"{parent_module}.{attr_name} 应已被 PR-B 删除，但仍可访问"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "ratchet：13 个 C-batch API 待 PR-C 删除。删完后此用例 XPASS strict，在 *同一 PR* 内删除 @xfail 标记即可。"
    ),
)
@pytest.mark.parametrize(
    ("parent_module", "attr_name", "batch"),
    SECONDARY_API_REMOVALS,
    ids=[f"{m}.{n}[{b}]" for m, n, b in SECONDARY_API_REMOVALS],
)
def test_secondary_api_removed(parent_module: str, attr_name: str, batch: str) -> None:
    """A 组 ratchet：被删 API 对应的 parent module 不再暴露该 attribute。"""
    mod, err = _safe_import(parent_module)
    assert mod is not None, f"failed to import {parent_module}: {err}"
    assert not hasattr(mod, attr_name), f"{parent_module}.{attr_name} 仍可访问，应当在 PR-{batch} 中删除"


@pytest.mark.xfail(
    strict=True,
    reason=("ratchet：PR-C 会 git rm 整个模块文件。删完后此用例 XPASS strict，在 *同一 PR* 内删除 @xfail 标记即可。"),
)
@pytest.mark.parametrize("modname", REMOVED_MODULES)
def test_secondary_module_removed(modname: str) -> None:
    """B 组 ratchet：整模块文件被 git rm 后，import 必须失败。"""
    mod, _ = _safe_import(modname)
    assert mod is None, f"{modname} 仍可 import，应已在 PR-C 中删除"
