# CZSC SVC 模块 - Streamlit 可视化组件库

## 概述

CZSC SVC (Streamlit Visualize Components) 是一个专为金融数据分析设计的 Streamlit 可视化组件库。


## 模块结构

```
czsc/svc/
├── __init__.py          # 主入口
├── base.py              # 基础功能模块，统一处理导入和样式
├── returns.py           # 收益相关可视化组件
├── correlation.py       # 相关性分析组件
├── factor.py            # 因子分析组件
├── backtest.py          # 回测相关组件
├── statistics.py        # 统计分析组件
├── strategy.py          # 策略分析组件
├── utils.py             # 工具类组件
├── price_analysis.py    # 价格敏感性分析组件
└── README.md           # 说明文档
```

## 组件功能

### 收益分析 (`returns.py`)
- `show_daily_return` - 日收益分析
- `show_cumulative_returns` - 累计收益曲线
- `show_monthly_return` - 月度收益分析
- `show_drawdowns` - 回撤分析
- `show_rolling_daily_performance` - 滚动绩效分析

### 相关性分析 (`correlation.py`)
- `show_correlation` - 相关性矩阵热力图
- `show_sectional_ic` - 截面IC分析
- `show_ts_rolling_corr` - 时序滚动相关性
- `show_ts_self_corr` - 自相关分析
- `show_cointegration` - 协整检验
- `show_corr_graph` - 相关性网络图
- `show_symbols_corr` - 品种相关性分析

### 因子分析 (`factor.py`)
- `show_feature_returns` - 特征收益分析
- `show_factor_layering` - 因子分层分析
- `show_factor_value` - 因子数值分布
- `show_event_return` - 事件收益分析
- `show_event_features` - 事件特征分析

### 回测分析 (`backtest.py`)
- `show_weight_distribution` - 权重分布分析
- `show_weight_backtest` - 权重回测
- `show_holds_backtest` - 持仓回测
- `show_stoploss_by_direction` - 止损分析

### 统计分析 (`statistics.py`)
- `show_splited_daily` - 分段收益分析
- `show_yearly_stats` - 年度统计
- `show_out_in_compare` - 样本内外对比
- `show_outsample_by_dailys` - 样本外分析
- `show_psi` - PSI分析
- `show_classify` - 分类分析
- `show_date_effect` - 日期效应分析
- `show_normality_check` - 正态性检验
- `show_describe` - 描述性统计
- `show_df_describe` - DataFrame描述统计

### 策略分析 (`strategy.py`)
- `show_optuna_study` - Optuna优化结果展示
- `show_czsc_trader` - 缠中说禅交易员详情
- `show_strategies_recent` - 最近N天策略表现
- `show_returns_contribution` - 子策略收益贡献分析
- `show_symbols_bench` - 多品种基准收益分析
- `show_quarterly_effect` - 季节性收益对比
- `show_cta_periods_classify` - 不同市场环境下策略表现
- `show_volatility_classify` - 波动率分类回测
- `show_portfolio` - 组合日收益绩效分析
- `show_turnover_rate` - 换手率变化展示
- `show_stats_compare` - 多组策略回测绩效对比
- `show_symbol_penalty` - 依次删除收益最高品种对比

### 工具组件 (`utils.py`)
- `show_code_editor` - 代码编辑器

### 价格敏感性分析 (`price_analysis.py`)
- `show_price_sensitive` - 价格敏感性分析组件  
- `price_sensitive_summary` - 价格敏感性分析摘要
  
  注：累计收益展示功能直接使用 `returns.show_cumulative_returns`

