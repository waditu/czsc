"""
绘图工具模块

本子包目前只保留缠论 K 线可视化能力：
``czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}``（离线 HTML，
多周期联立）。

历史模块清单（已删除）：

- 二阶段清理 PR-C：``KlineChart`` / ``plot_czsc_chart`` 及 ``backtest.py`` 中 7 个 ``plot_*`` 函数；
- 2026-05-17 PR-A：``kline.py``（仅剩 ``plot_nx_graph``）整文件删除；
  ``weight.py`` 整文件删除（含 ``calculate_turnover_stats`` / ``calculate_weight_stats``
  / 4 个 ``plot_weight_*`` / ``plot_turnover_*``）。

需要权重时序图或 networkx 图的调用方，请直接使用 ``plotly.express`` /
``wbt.generate_backtest_report``，参考 ``docs/migration/cleanup-non-czsc-core.md``。
"""

__all__: list[str] = []
