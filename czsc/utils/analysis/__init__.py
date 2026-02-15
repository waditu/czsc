"""
分析工具模块

包括统计分析、相关性分析和事件分析
"""

# 从 stats 导入统计函数
from .stats import (
    daily_performance,
    holds_performance,
    top_drawdowns,
    rolling_daily_performance,
    psi,
)

# 从 corr 导入相关性分析函数
from .corr import (
    nmi_matrix,
    single_linear,
    cross_sectional_ic,
)

# 从 events 导入事件分析函数
from .events import (
    overlap,
)

__all__ = [
    # Stats
    'daily_performance',
    'holds_performance',
    'top_drawdowns',
    'rolling_daily_performance',
    'psi',
    # Correlation
    'nmi_matrix',
    'single_linear',
    'cross_sectional_ic',
    # Events
    'overlap',
]
