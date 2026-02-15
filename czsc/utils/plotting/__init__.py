"""
绘图工具模块

统一的可视化工具，包括回测图表、权重分析图表、K线图表等
"""

# 从 backtest 导入回测相关绘图函数
from .backtest import (
    plot_cumulative_returns,
    plot_drawdown_analysis,
    plot_daily_return_distribution,
    plot_monthly_heatmap,
    plot_backtest_stats,
    plot_colored_table,
    plot_long_short_comparison,
)

# 从 weight 导入权重相关绘图函数
from .weight import (
    calculate_turnover_stats,
    calculate_weight_stats,
    plot_weight_histogram_kde,
    plot_weight_cdf,
    plot_turnover_overview,
    plot_turnover_cost_analysis,
)

# 从 kline 导入K线相关绘图类和函数
from .kline import (
    KlineChart,
)

# 从 common 导出常用常量
from .common import (
    COLOR_DRAWDOWN,
    COLOR_RETURN,
    COLOR_ANNO_GRAY,
    COLOR_ANNO_RED,
    COLOR_BORDER,
    COLOR_HEADER_BG,
    QUANTILES_DRAWDOWN,
    QUANTILES_DRAWDOWN_ANALYSIS,
    SIGMA_LEVELS,
    MONTH_LABELS,
    TemplateType,
    figure_to_html,
    add_year_boundary_lines,
)

__all__ = [
    # Backtest plotting functions
    'plot_cumulative_returns',
    'plot_drawdown_analysis',
    'plot_daily_return_distribution',
    'plot_monthly_heatmap',
    'plot_backtest_stats',
    'plot_colored_table',
    'plot_long_short_comparison',
    # Weight plotting functions
    'calculate_turnover_stats',
    'calculate_weight_stats',
    'plot_weight_histogram_kde',
    'plot_weight_cdf',
    'plot_turnover_overview',
    'plot_turnover_cost_analysis',
    # Kline plotting
    'KlineChart',
    # Common constants and utilities
    'COLOR_DRAWDOWN',
    'COLOR_RETURN',
    'COLOR_ANNO_GRAY',
    'COLOR_ANNO_RED',
    'COLOR_BORDER',
    'COLOR_HEADER_BG',
    'QUANTILES_DRAWDOWN',
    'QUANTILES_DRAWDOWN_ANALYSIS',
    'SIGMA_LEVELS',
    'MONTH_LABELS',
    'TemplateType',
    'figure_to_html',
    'add_year_boundary_lines',
]
