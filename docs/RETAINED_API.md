# Retained API

这份文档描述当前 `czsc` 项目认可的公开表面。

原则只有两条：

1. 根包 `czsc` 只保留高频、稳定、当前实现确实存在的快捷入口。
2. 低频、专门、容易膨胀的能力统一从明确子模块导入。

## 根包快捷入口

### 核心对象

- `CZSC`
- `RawBar`
- `NewBar`
- `Signal`
- `Event`
- `Position`
- `Operate`
- `Direction`
- `Freq`
- `ZS`
- `format_standard_kline`

### 交易入口

- `CzscSignals`
- `CzscTrader`
- `SignalsParser`
- `check_signals_acc`
- `generate_czsc_signals`
- `get_signals_config`
- `get_signals_freqs`
- `get_unique_signals`

### 高频工具

- `DataClient`
- `DiskCache`
- `disk_cache`
- `clear_cache`
- `clear_expired_cache`
- `read_json`
- `save_json`
- `dill_dump`
- `dill_load`
- `generate_fernet_key`
- `fernet_encrypt`
- `fernet_decrypt`
- `resample_to_daily`
- `risk_free_returns`
- `update_bbars`
- `update_nxb`
- `update_tbars`

### 研究函数

根包仍保留当前可运行的 `eda` 高频入口，例如：

- `remove_beta_effects`
- `vwap`
- `twap`
- `cross_sectional_strategy`
- `judge_factor_direction`
- `monotonicity`
- `weights_simple_ensemble`
- `unify_weights`
- `turnover_rate`
- `make_price_features`

### Lazy 模块

- `mock`
- `svc`
- `fsa`
- `aphorism`
- `cwc`

### Lazy 属性

- `CzscStrategyBase`
- `CzscJsonStrategy`
- `capture_warnings`
- `execute_with_warning_capture`
- `adjust_holding_weights`
- `log_strategy_info`
- `calculate_bi_info`
- `symbols_bi_infos`
- `plot_czsc_chart`
- `KlineChart`
- `check_kline_quality`
- `generate_backtest_report`

## 应从子模块导入的能力

这些能力仍可用，但不建议继续往根包堆：

- 报告细分能力：`czsc.utils.backtest_report`
- HTML 报告构建：`czsc.utils.html_report_builder`
- PDF 报告构建：`czsc.utils.pdf_report_builder`
- 图表绘制：`czsc.utils.plotting.*`
- 信号工具：`czsc.utils.sig`
- 数据分析工具：`czsc.utils.analysis.*`
- 数据访问与缓存：`czsc.utils.data.*`

## 已明确移除的历史入口

以下名字不再视为保留 API：

- `CTAResearch`
- `DummyBacktest`
- `OpensOptimize`
- `ExitsOptimize`
- `PairsPerformance`
- `sensors`
- `rwc`

如果你仍然看到这些名字出现在文档、示例或类型桩中，那就是待清理残留，而不是兼容承诺。
