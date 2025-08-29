"""
Streamlit Visualize Components (SVC) - 缠中说禅可视化组件库

该模块提供了一套完整的 Streamlit 可视化组件，用于金融数据分析、策略回测、因子分析等场景。

主要功能模块：
- returns: 收益相关的可视化组件
- correlation: 相关性分析组件
- factor: 因子分析组件
- backtest: 回测相关组件
- statistics: 统计分析组件
- utils: 工具类组件

使用方法：
```python
import czsc
from czsc.svc import show_daily_return, show_weight_backtest

# 或者导入整个子模块
from czsc.svc import returns, backtest
```
"""

# 导入所有子模块的函数，保持向后兼容性
from .returns import (
    show_daily_return,
    show_cumulative_returns,
    show_monthly_return,
    show_drawdowns,
    show_rolling_daily_performance,
)

from .correlation import (
    show_correlation,
    show_sectional_ic,
    show_ts_rolling_corr,
    show_ts_self_corr,
    show_cointegration,
    show_corr_graph,
    show_symbols_corr,
)

from .factor import (
    show_feature_returns,
    show_factor_layering,
    show_factor_value,
    show_event_return,
    show_event_features,
)

from .backtest import (
    show_weight_distribution,
    show_weight_backtest,
    show_holds_backtest,
    show_stoploss_by_direction,
    show_backtest_by_thresholds,
    show_yearly_backtest,
)

from .statistics import (
    show_splited_daily,
    show_yearly_stats,
    show_out_in_compare,
    show_outsample_by_dailys,
    show_psi,
    show_classify,
    show_date_effect,
    show_normality_check,
    show_describe,
    show_df_describe,
)

from .utils import (
    show_code_editor,
)

from .price_analysis import (
    show_price_sensitive,
)

from .strategy import (
    show_optuna_study,
    show_czsc_trader,
    show_strategies_recent,
    show_returns_contribution,
    show_symbols_bench,
    show_quarterly_effect,
    show_cta_periods_classify,
    show_volatility_classify,
    show_portfolio,
    show_turnover_rate,
    show_stats_compare,
    show_symbol_penalty,
    show_multi_backtest,
)

# 将所有函数添加到 __all__ 中
__all__ = [
    # 收益相关
    "show_daily_return",
    "show_cumulative_returns",
    "show_monthly_return",
    "show_drawdowns",
    "show_rolling_daily_performance",
    # 相关性分析
    "show_correlation",
    "show_sectional_ic",
    "show_ts_rolling_corr",
    "show_ts_self_corr",
    "show_cointegration",
    "show_corr_graph",
    "show_symbols_corr",
    # 因子分析
    "show_feature_returns",
    "show_factor_layering",
    "show_factor_value",
    "show_event_return",
    "show_event_features",
    # 回测相关
    "show_weight_distribution",
    "show_weight_backtest",
    "show_holds_backtest",
    "show_stoploss_by_direction",
    "show_backtest_by_thresholds",
    "show_yearly_backtest",
    # 统计分析
    "show_splited_daily",
    "show_yearly_stats",
    "show_out_in_compare",
    "show_outsample_by_dailys",
    "show_psi",
    "show_classify",
    "show_date_effect",
    "show_normality_check",
    "show_describe",
    "show_df_describe",
    # 策略分析
    "show_optuna_study",
    "show_czsc_trader",
    "show_strategies_recent",
    "show_returns_contribution",
    "show_symbols_bench",
    "show_quarterly_effect",
    "show_cta_periods_classify",
    "show_volatility_classify",
    "show_portfolio",
    "show_turnover_rate",
    "show_stats_compare",
    "show_symbol_penalty",
    "show_multi_backtest",
    # 工具类
    "show_code_editor",
    # 价格敏感性分析
    "show_price_sensitive",
]
