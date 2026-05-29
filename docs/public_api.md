# CZSC 公开 API 参考手册

> 本文档列出 `czsc` 包通过 `__all__` 暴露给用户的所有公开 API，按功能分类。
> 每个 API 标注：用途说明、真正的功能实现位置、依赖的内部函数/模块。
>
> 生成日期：2026-05-24 | 基于 `czsc/__init__.py` 中 `__all__` 列表

---

## 目录

1. [缠论核心类型（Rust 实现）](#1-缠论核心类型rust-实现)
2. [缠论核心算法函数（Rust 实现）](#2-缠论核心算法函数rust-实现)
3. [交易器与信号管理](#3-交易器与信号管理)
4. [策略门面](#4-策略门面)
5. [研究 / 回测 / 优化入口](#5-研究--回测--优化入口)
6. [数据格式转换](#6-数据格式转换)
7. [技术指标（TA）算子](#7-技术指标ta算子)
8. [探索性数据分析（EDA）](#8-探索性数据分析eda)
9. [回测与绩效（来自 wbt）](#9-回测与绩效来自-wbt)
10. [缓存与数据管理](#10-缓存与数据管理)
11. [IO 工具](#11-io-工具)
12. [交易工具](#12-交易工具)
13. [通用工具函数](#13-通用工具函数)
14. [K 线质量检查](#14-k-线质量检查)
15. [日志与告警工具](#15-日志与告警工具)
16. [可视化](#16-可视化)
17. [飞书集成（fsa）](#17-飞书集成fsa)
18. [数据连接器（connectors）](#18-数据连接器connectors)
19. [模拟数据（mock）](#19-模拟数据mock)
20. [环境变量（envs）](#20-环境变量envs)
21. [包元信息](#21-包元信息)

---

## 1. 缠论核心类型（Rust 实现）

所有核心类型由 Rust crate `czsc-core` 实现，通过 `czsc-python`（PyO3）暴露为 `czsc._native.*`，
顶层 `czsc` 命名空间做 re-export。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `CZSC` | 缠论分析主对象，管理原始 K 线、分型、笔列表 | `crates/czsc-core/src/czsc.rs` → `czsc._native.CZSC` | `RawBar`, `NewBar`, `FX`, `BI`, `check_fx`, `check_bi`, `remove_include` |
| `RawBar` | 原始 K 线数据结构 | `crates/czsc-core/src/bar.rs` → `czsc._native.RawBar` | `Freq` |
| `NewBar` | 去包含关系后的 K 线数据结构 | `crates/czsc-core/src/bar.rs` → `czsc._native.NewBar` | `RawBar` |
| `FX` | 分型（顶分型/底分型）数据结构 | `crates/czsc-core/src/fx.rs` → `czsc._native.FX` | `NewBar`, `Mark` |
| `BI` | 笔数据结构，包含力度、R²、斜率等统计量 | `crates/czsc-core/src/bi.rs` → `czsc._native.BI` | `FX`, `NewBar`, `Direction`, `FakeBI` |
| `FakeBI` | 笔内部分型连接得到的近似次级别笔 | `crates/czsc-core/src/bi.rs` → `czsc._native.FakeBI` | `FX` |
| `ZS` | 中枢数据结构 | `crates/czsc-core/src/zs.rs` → `czsc._native.ZS` | `BI`, `Direction` |
| `Freq` | K 线周期枚举（F1/F5/F15/F30/F60/D/W/M 等） | `crates/czsc-core/src/enums.rs` → `czsc._native.Freq` | 无 |
| `Mark` | 分型标记枚举（顶/底/无） | `crates/czsc-core/src/enums.rs` → `czsc._native.Mark` | 无 |
| `Direction` | 方向枚举（向上/向下/无） | `crates/czsc-core/src/enums.rs` → `czsc._native.Direction` | 无 |
| `Operate` | 操作枚举（开多/开空/平多/平空等） | `crates/czsc-core/src/enums.rs` → `czsc._native.Operate` | 无 |
| `Signal` | 信号数据结构 | `crates/czsc-core/src/signal.rs` → `czsc._native.Signal` | 无 |
| `Event` | 事件数据结构（信号的逻辑组合：AND/OR/NOT） | `crates/czsc-trader/src/event.rs` → `czsc._native.Event` | `Signal`, `Operate` |
| `Position` | 持仓/仓位数据结构（开仓事件+平仓事件+风控） | `crates/czsc-trader/src/position.rs` → `czsc._native.Position` | `Event`, `Operate` |
| `BarGenerator` | 多周期 K 线合成器（基础周期→多个大级别） | `crates/czsc-trader/src/bar_generator.rs` → `czsc._native.BarGenerator` | `RawBar`, `Freq`, `freq_end_time`, `is_trading_time` |
| `ParsedSignalDoc` | 信号文档解析结果 | `crates/czsc-signals/` → `czsc._native.ParsedSignalDoc` | 无 |

---

## 2. 缠论核心算法函数（Rust 实现）

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `check_fx` | 检查三根无包含 K 线是否构成分型 | `crates/czsc-core/src/analyze.rs` → `czsc._native.check_fx` | `NewBar`, `FX`, `Mark` |
| `check_fxs` | 批量检查分型序列 | `crates/czsc-core/src/analyze.rs` → `czsc._native.check_fxs` | `check_fx`, `FX` |
| `check_bi` | 检查两个分型之间是否构成笔 | `crates/czsc-core/src/analyze.rs` → `czsc._native.check_bi` | `FX`, `BI`, `NewBar` |
| `remove_include` | 去除 K 线包含关系 | `crates/czsc-core/src/analyze.rs` → `czsc._native.remove_include` | `RawBar`, `NewBar` |
| `freq_end_time` | 计算指定周期的 K 线结束时间 | `crates/czsc-core/src/utils.rs` → `czsc._native.freq_end_time` | `Freq` |
| `is_trading_time` | 判断给定时间是否为交易时间 | `crates/czsc-core/src/utils.rs` → `czsc._native.is_trading_time` | `Freq` |
| `parse_signal_doc` | 解析信号函数的文档字符串 | `crates/czsc-signals/` → `czsc._native.parse_signal_doc` | `ParsedSignalDoc` |

---

## 3. 交易器与信号管理

统一入口：`czsc.traders`（facade 模块），实际实现在 `czsc._native`（Rust）。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `CzscSignals` | 多周期联立信号分析器（不含仓位管理） | `crates/czsc-trader/src/signals.rs` → `czsc._native.CzscSignals` | `BarGenerator`, `CZSC`, 信号函数注册表 |
| `CzscTrader` | 多周期联立交易器（含仓位管理+信号） | `crates/czsc-trader/src/trader.rs` → `czsc._native.CzscTrader` | `CzscSignals`, `Position`, `Event` |
| `generate_czsc_signals` | 在 K 线序列上批量生成信号，返回 DataFrame | `crates/czsc-trader/` → `czsc._native.generate_czsc_signals` | `BarGenerator`, `CzscTrader`, 信号函数注册表 |
| `get_signals_config` | 将信号序列解析为信号配置列表（运行时格式） | `crates/czsc-trader/` → `czsc._native.get_signals_config` | `derive_signals_config` |
| `get_signals_freqs` | 从信号配置中提取涉及的周期列表 | `crates/czsc-trader/` → `czsc._native.get_signals_freqs` | `derive_signals_freqs` |
| `derive_signals_config` | 从信号 key 列表派生信号配置 | `crates/czsc-trader/` → `czsc._native.derive_signals_config` | 信号函数注册表 |
| `derive_signals_freqs` | 从信号配置列表派生周期列表 | `crates/czsc-trader/` → `czsc._native.derive_signals_freqs` | 无 |
| `get_unique_signals` | 从 Position 列表中提取去重的唯一信号 key | `crates/czsc-trader/` → `czsc._native.get_unique_signals` | `Position` |

---

## 4. 策略门面

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `CzscStrategyBase` | 策略开发抽象基类；子类实现 `positions` 属性即可获得回测/回放/序列化能力 | `czsc/strategies.py:56` | `czsc._native.{derive_signals_config, derive_signals_freqs, strategy_unique_signals, strategy_save_position, strategy_load_position}`, `czsc._runtime_adapters.{bars_to_dataframe, sort_freqs}`, `czsc.research.{run_research, run_replay}` |
| `CzscJsonStrategy` | 从 JSON 文件加载持仓定义的策略包装器（继承 `CzscStrategyBase`） | `czsc/strategies.py:284` | `CzscStrategyBase.load_positions` |

### CzscStrategyBase 关键方法/属性

| 方法/属性 | 用途 | 内部依赖 |
|-----------|------|----------|
| `positions` (抽象) | 子类必须实现，返回 `list[Position]` | — |
| `unique_signals` | 汇总所有 Position 的信号 key（去重） | `czsc._native.strategy_unique_signals` |
| `signals_config` | 由 `unique_signals` 派生的信号配置列表 | `czsc._native.derive_signals_config` |
| `freqs` | 策略涉及的所有周期（排序去重） | `czsc._native.derive_signals_freqs`, `czsc._runtime_adapters.sort_freqs` |
| `base_freq` | 策略基础周期（最高频） | `freqs` |
| `backtest(bars, **kwargs)` | 内存模式回测 | `czsc.research.run_research` |
| `replay(bars, res_path, **kwargs)` | 回放并落盘 | `czsc.research.run_replay` |
| `save_positions(path)` | 持仓序列化为 JSON（带 sha256 校验） | `czsc._native.strategy_save_position` |
| `load_positions(files, check)` | 从 JSON 加载 Position 列表 | `czsc._native.strategy_load_position` |

---

## 5. 研究 / 回测 / 优化入口

统一入口：`czsc.research`（Python 薄封装）→ Rust 后端。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `run_research` | 内存模式策略研究，返回 Arrow 格式结果 | `czsc/research.py:102` | `czsc._native.run_research`, `czsc._utils._df_convert.pandas_to_arrow_bytes`, `czsc.models.ResearchResult` |
| `run_replay` | 单标的回放，可选落盘 parquet | `czsc/research.py:150` | `czsc._native.run_replay`, `czsc.models.ReplayResult` |
| `run_optimize_batch` | 批量参数优化任务 | `czsc/research.py:192` | `czsc._native.run_optimize_batch`, `czsc._runtime_adapters.normalize_candidate_events`, `czsc.models.OptimizeResult` |
| `build_open_optim_positions` | 构造开仓优化候选仓位（不执行回测） | `czsc/research.py:242` | `czsc._native.build_open_optim_positions` |
| `build_exit_optim_positions` | 构造平仓优化候选仓位（不执行回测） | `czsc/research.py:264` | `czsc._native.build_exit_optim_positions`, `czsc._runtime_adapters.normalize_candidate_events` |

### 优化框架辅助类（`czsc.utils.optimize`）

通过 `czsc.utils` 暴露，非顶层 `__all__`，但属于常用公开 API：

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `OpensOptimize` | 开仓参数批量优化外观类 | `czsc/utils/optimize.py:281` | `run_optimize_batch`, `CzscOpenOptimStrategy`, `czsc._runtime_adapters.bars_to_dataframe` |
| `ExitsOptimize` | 平仓参数批量优化外观类 | `czsc/utils/optimize.py:422` | `run_optimize_batch`, `CzscExitOptimStrategy`, `czsc._runtime_adapters.normalize_candidate_events` |
| `CzscOpenOptimStrategy` | 开仓优化策略（按候选信号展开变体仓位） | `czsc/utils/optimize.py:150` | `CzscStrategyBase`, `Position` |
| `CzscExitOptimStrategy` | 平仓优化策略（按候选事件展开变体仓位） | `czsc/utils/optimize.py:204` | `CzscStrategyBase`, `Position`, `czsc._runtime_adapters.normalize_candidate_event` |

---

## 6. 数据格式转换

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `format_standard_kline` | 将标准 K 线 DataFrame 转换为 `list[RawBar]` | `czsc/_format_standard_kline.py:57` | `czsc._native.{RawBar, Freq}` |
| `resample_bars` | 将基础周期 K 线（`DataFrame` 或 `list[RawBar]`）重采样到目标周期 | `czsc/_resample_bars.py:61` | `czsc._native.{resample_bars, RawBar, Freq}` |

---

## 7. 技术指标（TA）算子

Rust 实现，位于 `crates/czsc-ta/`，通过 `czsc._native.ta.*` 暴露，顶层有别名。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `ema` | 指数移动平均 | `crates/czsc-ta/` → `czsc._native.ema` | 无 |
| `sma` | 简单移动平均 | `crates/czsc-ta/` → `czsc._native.sma` | 无 |
| `rolling_rank` | 滚动排名 | `crates/czsc-ta/` → `czsc._native.rolling_rank` | 无 |
| `boll_positions` | 布林带位置指标 | `crates/czsc-ta/` → `czsc._native.boll_positions` | 无 |
| `ultimate_smoother` | 终极平滑器 | `crates/czsc-ta/` → `czsc._native.ultimate_smoother` | 无 |

---

## 8. 探索性数据分析（EDA）

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `monotonicity` | 单调性分析（等价于 scipy.stats.spearmanr） | `crates/czsc-core/` → `czsc._native.monotonicity` | 无（Rust 实现） |
| `mark_cta_periods` | 【后验】标记 CTA 最容易/最难赚钱的时间段 | `czsc/utils/mark_cta_periods.py:22` | `czsc.{CZSC, Freq, format_standard_kline}` |
| `mark_volatility` | 【后验】标记时序/截面波动率最大/最小的时间段 | `czsc/utils/mark_volatility.py:14` | 无（纯 pandas/numpy） |

---

## 9. 回测与绩效（来自 wbt）

这三个 API 来自硬依赖 `wbt` 包，在 `czsc` 顶层直接 re-export。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `WeightBacktest` | 基于权重序列的回测引擎 | `wbt.WeightBacktest` | wbt 内部 |
| `daily_performance` | 日线绩效指标计算 | `wbt.daily_performance` | wbt 内部 |
| `top_drawdowns` | 最大回撤区间识别 | `wbt.top_drawdowns` | wbt 内部 |

---

## 10. 缓存与数据管理

定义于 `czsc/utils/data/`，通过 `czsc.utils` → `czsc` 顶层暴露。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `home_path` | 缓存根目录（`~/.czsc`，可通过 `CZSC_HOME` 环境变量覆盖） | `czsc/utils/data/cache.py:25` | 无 |
| `get_dir_size` | 获取目录大小（单位：Bytes） | `czsc/utils/data/cache.py:29` | 无 |
| `empty_cache_path` | 清空缓存目录 | `czsc/utils/data/cache.py:41` | `home_path` |
| `DiskCache` | 磁盘缓存类（支持 pkl/json/csv/parquet 等多种格式） | `czsc/utils/data/cache.py:47` | `home_path` |
| `disk_cache` | 磁盘缓存装饰器 | `czsc/utils/data/cache.py:175` | `DiskCache` |
| `clear_cache` | 清空指定缓存文件夹 | `czsc/utils/data/cache.py:230` | 无 |
| `clear_expired_cache` | 清除过期缓存文件 | `czsc/utils/data/cache.py:214` | 无 |
| `DataClient` | 统一数据接口客户端（兼容 Tushare，支持本地缓存） | `czsc/utils/data/client.py:48` | `get_url_token`, `get_dir_size` |
| `set_url_token` | 设置数据接口凭证码 | `czsc/utils/data/client.py:13` | 无 |
| `get_url_token` | 获取数据接口凭证码 | `czsc/utils/data/client.py:29` | 无 |

---

## 11. IO 工具

定义于 `czsc/utils/io.py`，通过 `czsc.utils` → `czsc` 顶层暴露。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `dill_dump` | 使用 dill 序列化对象到文件 | `czsc/utils/io.py:7` | `dill` |
| `dill_load` | 从文件反序列化 dill 对象 | `czsc/utils/io.py:13` | `dill` |
| `save_json` | 将 dict 保存为 JSON 文件（UTF-8） | `czsc/utils/io.py:30` | 无 |
| `read_json` | 从 JSON 文件读取 dict | `czsc/utils/io.py:35` | 无 |

---

## 12. 交易工具

定义于 `czsc/utils/trade.py`，通过 `czsc.utils` → `czsc` 顶层暴露。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `risk_free_returns` | 创建无风险收益率序列 | `czsc/utils/trade.py:17` | `_get_trade_dates`（内部函数） |
| `update_nxb` | 计算并添加后 N 根 bar 的累计收益列 | `czsc/utils/trade.py:33` | 无（纯 pandas） |
| `update_bbars` | 计算并添加前 N 根 bar 的累计收益列 | `czsc/utils/trade.py:67` | 无（纯 pandas） |
| `update_tbars` | 计算带 Event 方向信息的未来收益 | `czsc/utils/trade.py:89` | 无（纯 pandas） |
| `resample_to_daily` | 将非日线数据转换为日线数据 | `czsc/utils/trade.py:110` | `_get_trade_dates`（内部函数） |
| `adjust_holding_weights` | 按固定持仓周期调整权重 | `czsc/utils/trade.py:161` | 无（纯 pandas） |

---

## 13. 通用工具函数

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `import_by_name` | 通过字符串导入模块/类/函数 | `czsc/utils/__init__.py:175` | 无 |
| `freqs_sorted` | K 线周期列表排序并去重 | `czsc/utils/__init__.py:198` | `czsc._runtime_adapters.sort_freqs` |
| `print_df_sample` | 以 reST 表格形式打印 DataFrame 前 N 行 | `czsc/utils/__init__.py:211` | `tabulate` |
| `to_arrow` | 将 DataFrame 转换为 Arrow IPC 字节串 | `czsc/utils/__init__.py:222` | `pyarrow` |
| `get_py_namespace` | 获取 Python 脚本文件中的 namespace | `czsc/utils/__init__.py:128` | 无 |
| `code_namespace` | 获取 Python 代码字符串中的 namespace | `czsc/utils/__init__.py:156` | 无 |
| `cross_sectional_ic` | 计算截面相关性（IC / ICIR） | `czsc/utils/analysis/corr.py:20` | `tqdm`, `pandas` |
| `index_composition` | 按收益率加权合成指数 K 线 | `czsc/utils/index_composition.py:11` | 无（纯 pandas） |

---

## 14. K 线质量检查

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `check_kline_quality` | 综合检查多 symbol K 线数据质量（缺失值/类型/顺序/价格/成交量等） | `czsc/utils/kline_quality.py:267` | `check_missing_values`, `check_data_types`, `check_datetime_order`, `check_price_reasonableness`, `check_volume_amount`, `check_symbol_consistency`, `check_duplicate_records`, `check_extreme_values`（均为同文件内部函数） |

---

## 15. 日志与告警工具

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `log_strategy_info` | 打印策略数据的详细信息（品种、时间范围、权重统计） | `czsc/utils/log.py:5` | `loguru` |
| `capture_warnings` | 上下文管理器，捕获 warning 信息 | `czsc/utils/warning_capture.py:14` | 无 |
| `execute_with_warning_capture` | 执行函数并捕获 warning 信息 | `czsc/utils/warning_capture.py:66` | `capture_warnings` |

---

## 16. 可视化

### lightweight-charts HTML 输出

定义于 `czsc/utils/plotting/lightweight/`，按需导入。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `plot_czsc` | 单周期 CZSC 对象 → lightweight-charts HTML（三 sub-pane：K 线+成交量+MACD） | `czsc/utils/plotting/lightweight/__init__.py:45` | `czsc._native.CZSC`, `_data.build_from_czsc`, `_html_renderer.render`, `_theme` |
| `plot_czsc_trader` | 多周期 CzscTrader/CzscSignals → 多 pane HTML | `czsc/utils/plotting/lightweight/__init__.py:87` | `_data.build_from_trader`, `_html_renderer.render`, `_theme` |
| `plot_czsc_signals` | K 线+信号函数历史触发点叠加 → HTML | `czsc/utils/plotting/lightweight/__init__.py:127` | `generate_czsc_signals`, `get_signals_freqs`, `BarGenerator`, `CzscTrader`, `_signals.build_signal_overlays` |

**使用方式**：
```python
from czsc.utils.plotting.lightweight import plot_czsc, plot_czsc_trader, plot_czsc_signals
```

---

## 17. 飞书集成（fsa）

定义于 `czsc/fsa/`，通过 `czsc.fsa` 子包暴露。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `FeishuApiBase` | 飞书 API 基类（封装鉴权） | `czsc/fsa/base.py` | `requests` |
| `request` | 飞书 API 通用请求函数 | `czsc/fsa/base.py` | `requests` |
| `SpreadSheets` | 飞书电子表格操作类 | `czsc/fsa/spreed_sheets.py` | `FeishuApiBase` |
| `SingleSheet` | 单个工作表操作类 | `czsc/fsa/spreed_sheets.py` | `FeishuApiBase` |
| `IM` | 飞书即时消息操作类 | `czsc/fsa/im.py` | `FeishuApiBase` |
| `BiTable` | 飞书多维表格操作类 | `czsc/fsa/bi_table.py` | `FeishuApiBase` |
| `push_text` | 推送文本消息到飞书群聊 | `czsc/fsa/__init__.py:40` | `requests` |
| `push_card` | 推送卡片消息到飞书群聊 | `czsc/fsa/__init__.py:61` | `requests` |
| `push_message` | 使用飞书 APP 批量推送消息 | `czsc/fsa/__init__.py:131` | `IM` |
| `read_feishu_sheet` | 读取飞书电子表格 | `czsc/fsa/__init__.py:95` | `SpreadSheets` |
| `update_spreadsheet` | 更新飞书电子表格 | `czsc/fsa/__init__.py:168` | `SpreadSheets` |
| `get_feishu_members_by_mobiles` | 根据手机号获取飞书用户 ID | `czsc/fsa/__init__.py:115` | `IM` |
| `push_strategy_latest` | 推送最新策略结果到飞书 | `czsc/fsa/push_strategy_latest.py` | `IM`, `SpreadSheets` |

---

## 18. 数据连接器（connectors）

定义于 `czsc/connectors/`，通过 `czsc.connectors` 子包暴露。

| 模块 | 用途 | 文件位置 |
|------|------|----------|
| `tq_connector` | 天勤量化数据源连接器 | `czsc/connectors/tq_connector.py` |
| `ts_connector` | Tushare 数据源连接器 | `czsc/connectors/ts_connector.py` |
| `ccxt_connector` | 数字货币（CCXT）数据源连接器 | `czsc/connectors/ccxt_connector.py` |
| `local_data` | 投研数据本地缓存读取入口 | `czsc/connectors/local_data.py` |

**使用方式**：
```python
from czsc.connectors import ts_connector
# 或
from czsc.connectors.ts_connector import get_raw_bars
```

---

## 19. 模拟数据（mock）

定义于 `czsc/mock.py`，转发到 `wbt.mock`。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `generate_symbol_kines` | 生成单标的、单周期随机 K 线 DataFrame | `czsc/mock.py:33` → 转发 `wbt.mock.mock_symbol_kline` | `wbt.mock` |
| `generate_klines_with_weights` | 生成带权重列的多标的 K 线（用于 WeightBacktest 打样） | `czsc/mock.py:61` → 转发 `wbt.mock.mock_weights` | `wbt.mock` |

**使用方式**：
```python
from czsc.mock import generate_symbol_kines
df = generate_symbol_kines("000001", "30分钟", "20240101", "20240601")
```

---

## 20. 环境变量（envs）

定义于 `czsc/envs.py`，通过 `czsc.envs` 子模块暴露。

| API | 用途 | 实现位置 | 内部依赖 |
|-----|------|----------|----------|
| `get_verbose` | 获取是否启用详细日志（`CZSC_VERBOSE`） | `czsc/envs.py:35` | 无 |
| `get_min_bi_len` | 获取笔最小长度（`CZSC_MIN_BI_LEN`，默认 6） | `czsc/envs.py:40` | 无 |
| `get_max_bi_num` | 获取最大笔数量（`CZSC_MAX_BI_NUM`，默认 50） | `czsc/envs.py:46` | 无 |

---

## 21. 包元信息

| API | 用途 | 实现位置 |
|-----|------|----------|
| `__version__` | 包版本号（唯一来源：`Cargo.toml [workspace.package].version`） | `czsc/__init__.py:140` |
| `__author__` | 作者 | `czsc/__init__.py:144` |
| `__email__` | 邮箱 | `czsc/__init__.py:145` |
| `__date__` | 发布日期 | `czsc/__init__.py:146` |
| `welcome` | 打印版本号、随机格言、缓存提示 | `czsc/__init__.py:258` |

---

## 附录 A：预加载子包一览

通过 `czsc/__init__.py` 顶层 import 的子包，用户可直接 `czsc.xxx` 访问：

| 子包 | 职责 |
|------|------|
| `czsc.connectors` | 数据源连接器（天勤/Tushare/CCXT/本地缓存） |
| `czsc.envs` | 环境变量读取（verbose/min_bi_len/max_bi_num） |
| `czsc.traders` | 交易器与信号管理 facade |
| `czsc.utils` | 通用工具（缓存/IO/分析/交易/绘图/优化） |
| `czsc.fsa` | 飞书 API 集成 |
| `czsc.aphorism` | 缠中说禅格言（`czsc.aphorism.print_one()`） |
| `czsc.mock` | 模拟数据生成 |

---

## 附录 B：信号函数（`czsc._native.signals`）

信号函数由 Rust 实现，通过 PyO3 暴露为 `czsc._native.signals.*`。Python 端有 7 个子模块：

| 子模块 | 说明 |
|--------|------|
| `czsc._native.signals.bar` | 基于 K 线形态的信号 |
| `czsc._native.signals.cvolp` | 量价关系信号 |
| `czsc._native.signals.cxt` | 基于缠论结构（分型/笔/中枢）的信号 |
| `czsc._native.signals.obv` | OBV 指标信号 |
| `czsc._native.signals.pressure` | 压力/支撑信号 |
| `czsc._native.signals.tas` | 技术分析指标信号（MACD/KDJ/RSI/BOLL 等） |
| `czsc._native.signals.vol` | 成交量信号 |

底层 Rust 源文件位于 `crates/czsc-signals/src/`（22 个 `.rs` 文件），信号通过 `#[signal]` 宏自动注册到 `SIGNAL_REGISTRY`。

**使用方式**：信号函数一般不直接调用，而是通过 `signals_config` 配置交给 `generate_czsc_signals` / `CzscTrader` / `CzscSignals` 使用。查询可用信号请参考 `signal-functions` skill 或执行 `ls crates/czsc-signals/src/`。

---

## 附录 C：数据模型（`czsc.models`）

定义于 `czsc/models.py`，用于策略研究流程的返回值容器。

| 类型 | 用途 | 实现位置 |
|------|------|----------|
| `StrategyConfig` | 策略配置 TypedDict（类型标注用） | `czsc/models.py:22` |
| `ResearchResult` | 研究/回测结果容器（含 Arrow 字节流，提供 `signals_df()` / `pairs_df()` / `holds_df()` 方法） | `czsc/models.py:52` |
| `ReplayResult` | 单标的回放结果容器（结构同 `ResearchResult`） | `czsc/models.py:96` |
| `OptimizeResult` | 参数优化结果容器（含 `message` 字段） | `czsc/models.py:109` |
