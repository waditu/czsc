# CZSC SVC 模块 - Streamlit 可视化组件库

## 概述

CZSC SVC (Streamlit Visualize Components) 是一个专为金融数据分析设计的 Streamlit 可视化组件库。该模块将原来的单一大文件 `st_components.py` 重构为模块化的组件库，提供更好的代码组织、维护性和可扩展性。

## 模块结构

```
czsc/svc/
├── __init__.py          # 主入口，提供向后兼容的导入
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

## 主要优化

### 1. 统一的基础模块 (`base.py`)
- **安全导入函数**: 统一处理 `rs_czsc` 和 `czsc` 库的导入，提供容错机制
- **样式配置**: 统一的绩效指标样式配置，确保一致的视觉效果
- **数据预处理**: 统一的 datetime 索引处理函数

### 2. 模块化设计
- **功能分离**: 按功能将组件分为 6 个子模块
- **职责明确**: 每个模块专注于特定的分析领域
- **代码复用**: 减少重复代码，提高维护效率

### 3. 向后兼容性
- **完整导入**: `__init__.py` 提供所有函数的导入，保持原有使用方式
- **占位函数**: 为未迁移的功能提供占位函数，避免破坏性变更
- **一致接口**: 保持所有函数的输入输出接口不变

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

## 使用方式

### 1. 向后兼容导入（推荐）
```python
# 与原来完全一致的使用方式
from czsc.svc import show_daily_return, show_weight_backtest, show_price_sensitive

# 使用组件
show_daily_return(df, ret_col="returns")

# 价格敏感性分析
dfr, dfd = show_price_sensitive(
    df=df,  # 包含symbol, dt, weight, price, TP_open, TP_high等列
    fee=2.0,  # 单边费率(BP)
    digits=2,  # 小数位数
    weight_type="ts",  # 权重类型
    title_prefix="策略A - ",
    show_detailed_stats=True,
    export_results=True
)
```

### 2. 子模块导入
```python
# 导入特定子模块
from czsc.svc import returns, backtest

# 使用子模块中的函数
returns.show_daily_return(df, ret_col="returns")
backtest.show_weight_backtest(dfw)
```

### 3. 完整模块导入
```python
# 导入整个模块
import czsc.svc as svc

# 使用模块中的函数
svc.show_daily_return(df, ret_col="returns")
```

## 代码质量改进

1. **类型注解**: 添加了函数参数的类型注解，提高代码可读性
2. **文档字符串**: 优化了函数文档，提供更清晰的参数说明
3. **错误处理**: 增强了错误处理机制，提供更友好的错误信息
4. **代码简化**: 减少了重复代码，提高了代码复用性
5. **导入优化**: 统一了外部库的导入处理，增加了容错性

## 性能优化

1. **延迟加载**: 只在需要时导入相关库，减少启动时间
2. **缓存机制**: 对样式配置等进行缓存，避免重复计算
3. **数据处理**: 优化了数据预处理逻辑，提高处理效率

## 迁移指南

从原始 `st_components.py` 迁移到新的 SVC 模块：

1. **无需修改代码**: 所有现有代码都可以直接使用，只需更新导入路径
2. **逐步迁移**: 可以逐步将导入改为子模块导入，获得更好的命名空间管理
3. **功能增强**: 新模块提供了更多参数选项和更好的错误处理

## 扩展开发

添加新组件时，请遵循以下规范：

1. **选择合适的子模块**: 根据功能选择合适的子模块或创建新的子模块
2. **使用统一的基础功能**: 使用 `base.py` 中的安全导入和样式函数
3. **保持接口一致性**: 确保函数接口与现有组件保持一致
4. **添加文档**: 为新函数添加完整的文档字符串
5. **更新 __init__.py**: 在主入口文件中添加新函数的导入

## 依赖说明

- **核心依赖**: pandas, numpy, streamlit, plotly
- **可选依赖**: 
  - streamlit-ace (代码编辑器)
  - scipy (统计分析)
  - scikit-learn (机器学习相关)
  - networkx (网络图分析)
  - statsmodels (时间序列分析)

## 版本兼容性

- **Python**: ≥ 3.8
- **Streamlit**: ≥ 1.0.0
- **Pandas**: ≥ 1.3.0
- **Numpy**: ≥ 1.20.0
- **Plotly**: ≥ 5.0.0 