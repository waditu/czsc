"""二阶段清理 ratchet：17 个非缠论核心 API + 3 个整删模块的删除进度追踪。

关联：
- 飞书任务：《20260517 清理非核心API接口》
  https://s0cqcxuy3p.feishu.cn/wiki/NGlFw8qXoiGNcnkkDMacNKXhnph
- 执行方案：《清理非核心 API 接口 v2 — 执行方案与验收标准》
  https://s0cqcxuy3p.feishu.cn/docx/H0UodenI2oBvzHx0IeYc05rCn7e

## 设计

与上一波 PR-1 (``test_api_no_streamlit.py``) 同构的双轨 ratchet：

- A 组（运行时 hasattr）：17 个 API × 多模块入口共 31 个 (parent_module, attr_name) 组合
- B 组（模块级 import）：2 个 PR-C 整删模块（backtest / common）

PR-A 阶段全部 xfail strict；PR-B 摘 18 个 B-batch 条目的 xfail；PR-C 摘剩下 13 个
C-batch 条目 + 2 个模块条目的 xfail。本文件 PR-C 落地后应当 **0 个 xfail**，
全部常规 PASS，作为永久防回归断言保留。

注：``_macd.py``（czsc 仪表盘 MACD 私有辅助）原计划与 backtest / common 一起 git rm，
但 ``lightweight/_data.py`` 仍 lazy import ``compute_macd``，故保留作为
``czsc/utils/plotting`` 内部模块（不对外暴露）。
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# (parent_module, attr_name) —— 17 个 API 全部已删（PR-B 8 个 + PR-C 9 个），共 31 个入口组合。
# 留为永久防回归断言，任何后续 PR 把这些名字加回来都会立即红。
SECONDARY_API_REMOVALS: list[tuple[str, str]] = [
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
    # --- PR-C：plotting/kline.py 2 个（KlineChart + plot_czsc_chart） ---
    # 注：``czsc.utils.plotting.kline`` 整模块本身已在 2026-05-17 PR-A
    # git rm（见下方 REMOVED_MODULES），故 ``("czsc.utils.plotting.kline", ...)``
    # 两条入口断言已并入模块级断言，本处仅保留 czsc / czsc.utils.plotting 顶层断言。
    ("czsc", "KlineChart"),
    ("czsc", "plot_czsc_chart"),
    ("czsc.utils.plotting", "KlineChart"),
    ("czsc.utils.plotting", "plot_czsc_chart"),
    # --- PR-C：plotting/backtest.py 7 个 plot_* 函数 ---
    # 注：backtest 模块本身已被 git rm（见下方 REMOVED_MODULES），这里仅检查从
    # plotting/__init__.py 的 re-export 入口也已移除。
    ("czsc.utils.plotting", "plot_cumulative_returns"),
    ("czsc.utils.plotting", "plot_drawdown_analysis"),
    ("czsc.utils.plotting", "plot_daily_return_distribution"),
    ("czsc.utils.plotting", "plot_monthly_heatmap"),
    ("czsc.utils.plotting", "plot_backtest_stats"),
    ("czsc.utils.plotting", "plot_colored_table"),
    ("czsc.utils.plotting", "plot_long_short_comparison"),
    # --- 2026-05-17 PR-A：删除 nmi_matrix / single_linear（corr.py 内部） ---
    ("czsc.utils", "nmi_matrix"),
    ("czsc.utils", "single_linear"),
    ("czsc.utils.analysis", "nmi_matrix"),
    ("czsc.utils.analysis", "single_linear"),
    # --- 2026-05-17 PR-A：删除 czsc/utils/analysis/stats.py 整模块 5 个函数 ---
    ("czsc", "psi"),
    ("czsc.utils", "daily_performance"),
    ("czsc.utils", "top_drawdowns"),
    ("czsc.utils", "psi"),
    ("czsc.utils.analysis", "daily_performance"),
    ("czsc.utils.analysis", "top_drawdowns"),
    ("czsc.utils.analysis", "psi"),
    ("czsc.utils.analysis", "evaluate_pairs"),
    ("czsc.utils.analysis", "cal_break_even_point"),
    # --- 2026-05-17 PR-A：删除 czsc/utils/plotting/kline.py 整模块（plot_nx_graph） ---
    ("czsc.utils.plotting", "plot_nx_graph"),
    # --- 2026-05-17 PR-A：删除 czsc/utils/plotting/weight.py 整模块 6 个绘图/统计函数 ---
    ("czsc.utils.plotting", "calculate_turnover_stats"),
    ("czsc.utils.plotting", "calculate_weight_stats"),
    ("czsc.utils.plotting", "plot_weight_histogram_kde"),
    ("czsc.utils.plotting", "plot_weight_cdf"),
    ("czsc.utils.plotting", "plot_turnover_overview"),
    ("czsc.utils.plotting", "plot_turnover_cost_analysis"),
    ("czsc.utils.plotting", "plot_weight_time_series"),
]

# 完全删除的模块（整文件 git rm）。
# ``_macd.py`` 原计划整删，但 lightweight 仍 lazy import compute_macd，故保留。
REMOVED_MODULES: list[str] = [
    "czsc.utils.plotting.backtest",
    "czsc.utils.plotting.common",
    # 2026-05-17 PR-A 整删模块
    "czsc.utils.analysis.stats",
    "czsc.utils.plotting.kline",
    "czsc.utils.plotting.weight",
    # 2026-05-17 PR-C 整删 / 搬运的模块
    # - base / sig_parse 纯透传层 git rm
    # - optimize 整文件 git mv 到 czsc.utils.optimize，原路径已不可 import
    "czsc.traders.base",
    "czsc.traders.sig_parse",
    "czsc.traders.optimize",
]


def _safe_import(name: str) -> tuple[Any | None, str | None]:
    try:
        return importlib.import_module(name), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


@pytest.mark.parametrize(
    ("parent_module", "attr_name"),
    SECONDARY_API_REMOVALS,
    ids=[f"{m}.{n}" for m, n in SECONDARY_API_REMOVALS],
)
def test_secondary_api_removed(parent_module: str, attr_name: str) -> None:
    """A 组：被删 API 对应的 parent module 不再暴露该 attribute（永久防回归）。"""
    mod, err = _safe_import(parent_module)
    assert mod is not None, f"failed to import {parent_module}: {err}"
    assert not hasattr(mod, attr_name), f"{parent_module}.{attr_name} 仍可访问，应已被二阶段清理删除"


@pytest.mark.parametrize("modname", REMOVED_MODULES)
def test_secondary_module_removed(modname: str) -> None:
    """B 组：整模块文件被 git rm 后，import 必须失败（永久防回归）。"""
    mod, _ = _safe_import(modname)
    assert mod is None, f"{modname} 仍可 import，应已被二阶段清理 PR-C 删除"
