# CZSC 核心功能案例库

> **目的**：让用户在 30 分钟内对 czsc 库的核心能力建立完整的认知，并能围绕"缠论分析 → 信号 → 事件 → 策略 → 回测 → 可视化"这条主线动手实践。
>
> **适用版本**：czsc ≥ 1.0（Rust + PyO3 架构，Python 端不再保留缠论算法回退）。

每个案例都是一个**独立的 Python 脚本**，位于 [`docs/examples/`](./examples)。
所有脚本仅依赖 `czsc` 顶层包（`czsc.mock` 提供模拟 K 线 / 权重数据，无需外部行情源），可以直接：

```bash
# 普通脚本
uv run python docs/examples/01_quick_start.py

# HTML 可视化脚本（生成自包含 HTML，浏览器直接打开）
uv run python docs/examples/13_lightweight_charts_html.py
```

> **统一产物目录**：03/07/08/09 这类有落盘产物的脚本，全部把输出写到
> `docs/examples/_output/`（HTML 报告、parquet、Position JSON 等）。
> 该目录已在仓库 `.gitignore` 中忽略，无需手工清理；要重置只需 `rm -rf docs/examples/_output`。

---

## 0. 系统全貌

```
┌──────────────┐    ┌─────────────────┐    ┌─────────────┐
│  RawBar 列表 │ ─► │  CZSC（缠论分析） │ ─► │  分型/笔/中枢 │
└──────────────┘    └─────────────────┘    └─────────────┘
        │                    │
        │ BarGenerator        │   CzscSignals.update_signals(bar)
        │（多周期合成）        │
        ▼                    ▼
┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   多周期 bg   │ ─► │  signals_config  │ ─► │  信号字典 cs.s   │
└──────────────┘    └─────────────────┘    └─────────────────┘
                             │
                             ▼ Event(signals_all/any/not)
                    ┌─────────────────┐
                    │  Position（仓位）│
                    └─────────────────┘
                             │
                  CzscTrader.update(bar) / CzscStrategyBase.backtest
                             ▼
                    ┌─────────────────────────────────────┐
                    │ pairs / holds / signals (Arrow)     │
                    └─────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       WeightBacktest                 plot_*绘图
       （时序/截面）                    （离线 HTML）
```

---

## 1. 案例索引

### 第一组：缠论核心（必读）

| #  | 文件 | 核心 API | 你将学到 |
|----|------|----------|----------|
| 01 | [`01_quick_start.py`](./examples/01_quick_start.py) | `czsc.mock.generate_symbol_kines` · `format_standard_kline` · `CZSC` | 数据准备、构造分析对象、增量 update 推进 |
| 02 | [`02_chan_structures.py`](./examples/02_chan_structures.py) | `FX` · `BI` · `ZS` · `Mark` · `Direction` | 分型/笔/中枢的属性、力度（power/SNR/slope/angle）、未完成笔（ubi） |
| 03 | [`03_kline_chart.py`](./examples/03_kline_chart.py) | `plot_czsc_chart` · `KlineChart` | 把缠论结构画成离线 HTML 报告（产物：`_output/03_kline_chart.html`） |

### 第二组：多级别与信号

| #  | 文件 | 核心 API | 你将学到 |
|----|------|----------|----------|
| 04 | [`04_bar_generator.py`](./examples/04_bar_generator.py) | `BarGenerator` · `freqs_sorted` | 用低周期 K 线实时合成高周期 K 线，构造多级别 CZSC |
| 05 | [`05_signals.py`](./examples/05_signals.py) | `CzscSignals` · `generate_czsc_signals` · `get_signals_config` | 三种信号生成方式 + 反推信号配置/涉及周期 |

### 第三组：事件驱动策略

| #  | 文件 | 核心 API | 你将学到 |
|----|------|----------|----------|
| 06 | [`06_event_position.py`](./examples/06_event_position.py) | `Event` · `Position` · `Operate` · `Event.is_match` | 信号 → 事件（all/any/not 逻辑组合） → 持仓 |
| 07 | [`07_strategy_backtest.py`](./examples/07_strategy_backtest.py) | `CzscStrategyBase` · `tactic.backtest` · `tactic.replay` · `tactic.save_positions` | 完整的策略类定义 + 内存回测 + 落盘回放 + 持仓序列化（产物：`_output/07_strategy_backtest/`） |

### 第四组：回测与离线可视化

| #  | 文件 | 核心 API | 你将学到 |
|----|------|----------|----------|
| 08 | [`08_weight_backtest.py`](./examples/08_weight_backtest.py) | `WeightBacktest` · `daily_performance` · `top_drawdowns` · `plot_backtest_stats` | 时序权重回测的完整链路 + 离线 HTML 报告（产物：`_output/08_weight_backtest.html`） |
| 09 | [`09_eda_and_plotting.py`](./examples/09_eda_and_plotting.py) | `mark_cta_periods` · `mark_volatility` · `cal_trade_price` · `turnover_rate` · `weights_simple_ensemble` · `plot_colored_table` · `plot_long_short_comparison` | 探索性分析常用工具 + 多种离线绘图函数（产物：`_output/09_eda_and_plotting.html`） |

### 第五组：lightweight-charts HTML（自包含交互看图）

| #  | 文件 | 关键 API | 你将看到 |
|----|------|----------|----------|
| 13 | [`13_lightweight_charts_html.py`](./examples/13_lightweight_charts_html.py) | `plot_czsc` · `plot_czsc_trader` | 缠论 K 线 + 多周期联立，自包含 HTML（无需服务端） |
| 15 | [`15_lightweight_signals_html.py`](./examples/15_lightweight_signals_html.py) | `plot_czsc_signals` | 信号叠加版本，含 signal timeline + tooltip |

> v2.0.0 起原 streamlit 交互面板 10/11/12/14/16 已删除；如需 streamlit 集成，调用方自行 `pip install streamlit` 后用 `st.components.v1.html(plot_czsc(c, output='html'))` 嵌入 HTML 即可。详见 [`migration/v2-cleanup.md`](./migration/v2-cleanup.md)。

---

## 2. 模块关联速查

| 想做的事 | 应使用的模块 / 函数 | 案例编号 |
|----------|---------------------|----------|
| 拿到模拟 K 线 / 权重数据 | `czsc.mock.generate_symbol_kines` / `generate_klines_with_weights` | 01, 08 |
| 转 DataFrame → RawBar | `czsc.format_standard_kline` | 01 |
| 跑缠论分析 | `czsc.CZSC(bars)` | 01, 02 |
| 多周期 K 线合成 | `czsc.BarGenerator` | 04, 11 |
| 单次批量计算信号 | `czsc.generate_czsc_signals` | 05 |
| 实盘流式信号计算 | `czsc.CzscSignals` + `update_signals(bar)` | 05, 11 |
| 信号字符串 → 配置 | `czsc.get_signals_config` / `get_signals_freqs` | 05, 06 |
| 事件逻辑组合 | `czsc.Event(signals_all/any/not)` | 06 |
| 完整持仓策略 | `czsc.Position` / `czsc.CzscStrategyBase` | 06, 07 |
| 多级别交易决策 | `czsc.CzscTrader` | 11 |
| 内存回测 | `tactic.backtest(bars)` 或 `czsc.run_research` | 07 |
| 落盘回放 | `tactic.replay(bars, res_path)` 或 `czsc.run_replay` | 07 |
| 持仓序列化 | `Position.dump` / `tactic.save_positions` / `CzscJsonStrategy` | 07 |
| 权重回测 | `czsc.WeightBacktest`（来自 wbt） | 08, 12 |
| 绩效指标 | `czsc.daily_performance` / `top_drawdowns` / `holds_performance` | 08 |
| 后验时段标记 | `czsc.mark_cta_periods` / `mark_volatility` | 09 |
| 换手率 / 集成 | `czsc.turnover_rate` / `weights_simple_ensemble` | 09 |
| 离线 K 线绘图 | `czsc.plot_czsc_chart` / `KlineChart` | 03, 10, 11 |
| 离线回测绘图 | `czsc.utils.plotting.backtest.*` | 08, 09 |

---

## 3. 典型工作流

### 3.1 "策略研究 → 回测 → 可视化" 完整流水线

```
[01] 准备数据
   ↓
[02] 看 CZSC 缠论结构（确认笔/分型识别正常）
   ↓
[04] 决定使用哪些周期，构造 BarGenerator
   ↓
[05] 设计信号配置（哪些信号 × 哪些周期）
   ↓
[06] 把信号组装成 Event；多个 Event 组装成 Position
   ↓
[07] 用 CzscStrategyBase 子类化 + 跑 backtest/replay
   ↓
[08] 把 trader / replay 输出的权重做 WeightBacktest 精细回测
   ↓
[09] 配合 EDA 工具（如 mark_cta_periods）做切片分析
   ↓
[13/15] 生成自包含 HTML 报告分享给协作者
```

### 3.2 "看盘 / Demo" 工作流

```
[01] 跑通 mock 数据 → CZSC
   ↓
[03] 离线生成一份 HTML 看图（plotly）
   ↓
[13/15] lightweight-charts 自包含 HTML，浏览器直接打开
```

---

## 4. 必须知道的几件事

### 4.1 数据格式约定

- **K 线 DataFrame** 必须包含列：`dt / symbol / open / close / high / low / vol / amount`
  （`czsc.mock.generate_symbol_kines` 返回的就是该 schema）。
- **权重 DataFrame** 必须包含列：`dt / symbol / weight / price`，`weight ∈ [-1, 1]`
  （>0 多头，<0 空头，0 空仓）；用于 `WeightBacktest`。
- **信号字符串** 格式：`"{freq}_{key2}_{key3}_{v1}_{v2}_{v3}_{score}"`
  （前 3 段是 key，后 4 段是 value），例：
  `"30分钟_D1_表里关系V230101_向上_任意_任意_0"`。

### 4.2 信号函数命名

- Rust 端注册的信号函数名是简短形式（**不带** `czsc.signals.` 前缀，版本号大写 V），
  例如：`cxt_bi_status_V230101`、`bar_zdt_V230331`、`tas_ma_base_V221101`。
- 完整列表：`czsc._native.signals.bar.list_signal_names()`
  （`bar / cxt / tas / vol / pressure / obv / cvolp` 七个子模块入口都返回**全集**）。
- 每个信号的 key 模板：`czsc._native.signals.bar.get_signal_template(name)`。

### 4.3 RawBar → DataFrame

- `pd.DataFrame(c.bars_raw)` 在新版 RawBar 上**不能**正确识别字段；
  请使用 `c.bars_raw_df`（CZSC 自带属性）或 `pd.DataFrame([b.to_dict() for b in bars])`。

### 4.4 Position.operates 的时间字段

- `Position.operates` 是 list of dict，其中 `dt` 是 **unix 时间戳（秒）**，
  画图时需要 `pd.to_datetime(value, unit="s")` 转成 datetime。

### 4.5 环境变量（`czsc.envs`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `CZSC_VERBOSE` | False | 是否打印详细日志 |
| `CZSC_MIN_BI_LEN` | 6 | 笔最小长度 |
| `CZSC_MAX_BI_NUM` | 50 | 单个 CZSC 实例保留的最大笔数 |

### 4.6 缓存

- 默认缓存目录：`czsc.home_path`
- 查看大小：`czsc.get_dir_size(czsc.home_path)`
- 清空：`czsc.empty_cache_path()`

---

## 5. 已知兼容性提示

> v2.0.0 后已删除 `czsc.svc` 与 streamlit 依赖，相关示例与组件提示一并移除；如需可视化请直接使用 `czsc.utils.plotting.*`（plotly + HTML）或 `czsc.utils.plotting.lightweight.*`（lightweight-charts）。

---

## 6. 进一步阅读

- 顶层 API 列表：`czsc/__init__.py` 的 `__all__`
- 类型 stub：`czsc/_native/__init__.pyi`（Rust 扩展的完整类型声明）
- 信号开发规范：[飞书文档 - 信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)
- WeightBacktest 工具集：见 [czsc-weight-backtest skill](../../) 与 wbt 包文档
- CLAUDE.md：项目整体设计与最佳实践
