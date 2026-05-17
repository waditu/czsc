"""
绘图工具模块

权重分析图表与 lightweight-charts 缠论可视化。

二阶段清理 PR-C 之后：

- ``KlineChart`` / ``plot_czsc_chart`` 及 ``backtest.py`` 中 7 个 ``plot_*`` 函数
  已删除。缠论 K 线可视化统一改用 :mod:`czsc.utils.plotting.lightweight`
  （离线 HTML，多周期联立）。回测可视化由调用方自行用 ``plotly.express`` / ``wbt``
  组合实现，参考 ``docs/migration/cleanup-non-czsc-core.md``。
- ``plot_nx_graph``（networkx 图）仍保留在 :mod:`czsc.utils.plotting.kline` 中，
  按需 ``from czsc.utils.plotting.kline import plot_nx_graph``。
"""

from .weight import (
    calculate_turnover_stats,
    calculate_weight_stats,
    plot_turnover_cost_analysis,
    plot_turnover_overview,
    plot_weight_cdf,
    plot_weight_histogram_kde,
)

__all__ = [
    "calculate_turnover_stats",
    "calculate_weight_stats",
    "plot_weight_histogram_kde",
    "plot_weight_cdf",
    "plot_turnover_overview",
    "plot_turnover_cost_analysis",
]
