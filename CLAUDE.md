# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CZSC（缠中说禅技术分析工具）是基于缠中说禅理论的综合性量化交易Python库，提供技术分析、信号生成、回测和市场分析等功能。本项目专注于实现缠论的分型、笔、线段等核心概念的自动识别，以及基于此的多级别量化交易策略。

## 🏛️ 开发宪法（Constitution）

以下规则是本项目长期演进的**硬约束**，任何 PR、任何重构、任何"为了赶进度的临时变通"都不得违反。与此冲突的代码审查意见、个人偏好、历史代码一律以本节为准；违反本节的代码即便已合入，也按 bug 处理、必须回滚或修复。

### 第一条 · Rust ↔ Python 行为一致

**需要 Rust 实现的部分必须同时满足 Rust crate 与 Python wheel 行为一致（Python 端纯透传，禁止再写适配层）。**

具体含义：

- 同一个名字（如 `monotonicity` / `CzscStrategyBase` / `generate_czsc_signals` / `CZSC`），`cargo add czsc` 的 Rust 用户与 `pip install czsc` 的 Python 用户调用后**行为必须一致**——同样的输入产生同样的输出，默认参数、错误处理、边界条件、字段命名都一致。
- Python 侧**只允许**做下面两类工作：
  1. **纯透传**：`from czsc._native import xxx` 后直接 re-export，不做任何包装；
  2. **不可避免的 PyO3 边界胶水**：DataFrame ↔ Arrow IPC 序列化、`pathlib.Path` ↔ `String` 转换等，PyO3 类型系统无法跨越的边界处理。
- **禁止**在 Python 侧做参数归一化、默认值补齐、返回值字段重命名、错误码翻译、`isinstance` 多态分支等"适配层"工作——这类逻辑必须下沉到 Rust 端实现（修改现有 API 或新增 API）。
- 新增 Python wrapper 之前，PR 描述里必须先回答"为什么不能改成 Rust 实现"，并经过 reviewer 显式批准。

**违反本条的常见信号（在 review 中视为红线）**：

- Python 函数体内出现 `if isinstance(bars, pd.DataFrame): ... elif isinstance(bars, list): ...` 等多态分支；
- Python 函数返回的 dict 字段顺序 / 命名与 Rust 端 `serde` 输出不一致；
- 同一份功能在 Python 测试覆盖完整，但 `cargo test` 没有等价用例；
- CHANGELOG 写 "Python 端默认参数从 X 改为 Y"，但 Rust 端无对应改动；
- `czsc/_runtime_adapters.py` 等"适配层"文件持续膨胀，而不是被逐步搬空到 Rust。

## 常用开发命令

### UV 包管理 (项目使用UV管理依赖)
```bash
# 同步依赖并安装开发工具（仅在 pyproject.toml / uv.lock 变更时跑）
uv sync --extra dev

# 安装所有依赖组合
uv sync --extra all

# 运行测试（日常默认 --no-sync，省去每次 4-5s 的 lockfile/venv 一致性检查）
uv run --no-sync pytest

# 运行指定测试文件
uv run --no-sync pytest tests/test_analyze.py -v

# 运行单个测试函数
uv run --no-sync pytest tests/test_analyze.py::test_czsc_basic -v

# 带覆盖率的测试
uv run --no-sync pytest --cov=czsc

# 跑全套（含 @pytest.mark.slow 标记的耗时测试，CI / 发布前用）
uv run --no-sync pytest --run-slow

# 代码格式化和检查（项目使用 ruff，不使用 black/isort/flake8）
uv run --no-sync ruff format czsc/ tests/
uv run --no-sync ruff check czsc/ tests/
```

> **`--no-sync` 约定**：`uv run` 默认会做 lockfile 解析 + venv 一致性检查（本地稳定 4-5s 固定开销）。日常开发循环里依赖很少变，统一用 `--no-sync` 跳过；仅在 `pyproject.toml` / `uv.lock` 改动后显式跑一次 `uv sync` 即可。

### 测试规范
- 所有测试文件位于 `tests/` 目录，使用 pytest 格式
- **关键原则**：测试数据统一通过 `czsc.mock` 模块获取，不要在测试中硬编码模拟数据
- 测试文件命名模式：`test_*.py`
- 模拟数据使用 `generate_symbol_kines` 函数生成，支持多品种、多频率、可重现的随机数据
- **慢测试约定**：依赖 `time.sleep` 或子进程冷启动的测试加 `@pytest.mark.slow`，默认跳过；CI / 发布前用 `pytest --run-slow` 跑全套。注册逻辑见 `tests/conftest.py`。


## 代码架构

### 核心组件

1. **`czsc._native`** - PyO3 编译产生的 Rust 扩展模块（缠论核心）：
   - 由 `crates/czsc-python` 通过 `maturin` 打包，扩展模块名 `czsc._native`
   - 暴露 `CZSC / FX / BI / ZS / RawBar / NewBar / Freq / Mark / Direction / Operate / Signal / Event / Position / BarGenerator` 等核心类型
   - 暴露 `check_bi / check_fx / check_fxs / remove_include / freq_end_time / is_trading_time` 等工具函数
   - 暴露 250+ 信号函数（完整分组以 `crates/czsc-signals/src/` 为准，13+ 子模块；可用 `ls crates/czsc-signals/src/` 自查最新清单）
   - 暴露 `czsc._native.ta.*`（Rust TA 算子，供信号函数内部使用；本次清理 起 Python 端不再暴露 `czsc.ta` 顶层 alias）
   - **不存在 Python 回退**：`czsc/py/` 与 `czsc/core.py` 已在 Phase H 删除；`CZSC_USE_PYTHON` 环境变量已退役（spec §3.4）

2. **`crates/`** - Rust workspace（9 个 crate）：
   - `czsc` / `czsc-core` / `czsc-derive` / `czsc-signals` / `czsc-trader` / `czsc-utils` / `czsc-ta`
   - `czsc-signal-macros`（proc-macro，`#[signal]` 注册宏）
   - `czsc-python`（PyO3 binding 总入口，唯一启用 `pyo3/extension-module` 的 crate）

3. **`czsc/traders/`** - 交易执行框架：
   - `__init__.py`：facade，统一 re-export `CzscSignals / CzscTrader / generate_czsc_signals / get_signals_config / get_signals_freqs / derive_signals_config / derive_signals_freqs / get_unique_signals / WeightBacktest`，全部来自 `czsc._native` 或 `wbt`
   - `base.py` / `sig_parse.py` 纯透传文件已于 2026-05-17 PR-C 整文件 git rm，新代码请直接走 `czsc.traders` 或 `czsc._native`
   - `optimize.py` 已于 2026-05-17 PR-C `git mv` 到 `czsc/utils/optimize.py`（职责更贴近 utils）；调用方请用 `from czsc.utils.optimize import OpensOptimize, ExitsOptimize, CzscOpenOptimStrategy, CzscExitOptimStrategy`

4. **`czsc/_native.signals`** - 信号函数（Rust 实现，通过 PyO3 暴露）：
   - 完整分组以 `crates/czsc-signals/src/` 为准（13+ 子模块），自查命令：`ls crates/czsc-signals/src/`
   - 原 `czsc/signals/` Python 命名空间层已在 Phase J **彻底删除**
   - 通过 `czsc.traders.generate_czsc_signals` 等接口调用信号
   - 信号解析 API：`get_signals_config` / `get_signals_freqs`（`czsc.traders`）；`SignalsParser` 类已删除

5. **`czsc/utils/`** - 工具模块（Phase J 精简后）：
   - `data/cache.py` / `io.py` / `log.py` / `kline_quality.py`：缓存、IO、日志、K 线质量校验
   - `analysis/corr.py`（仅剩 `cross_sectional_ic`；`stats.py` 与 `nmi_matrix` / `single_linear` 已于 2026-05-17 PR-A 删除，`daily_performance` / `top_drawdowns` 改由顶层 `czsc.*` 透传 wbt）
   - `data/client.py`：统一数据客户端接口
   - TA 算子由 Rust `czsc._native.ta` 提供（信号内部依赖），顶层别名 `czsc.{ema,sma,rolling_rank,boll_positions,ultimate_smoother}` 保留；仪表盘场景的 MACD（×2 约定）已下沉为 `czsc/utils/plotting/_macd.py` 私有辅助
   - `trade.py`：交易工具
   - `plotting/{kline,weight}.py` + `plotting/lightweight/`：plotly 单周期 K 线 + 权重时序图 / lightweight-charts 自包含 HTML
   - 已删除：`bar_generator.py` / `bi_info.py`（Rust 已实现）、`st_components.py` / `echarts_*` / `pdf_report` / `html_report_builder` / `word_writer` / `signal_analyzer` / `crypto/` / `czsc/svc/` / `plotting/backtest.py` / `plotting/common.py`（本次清理 删除 Streamlit 组件库与回测可视化函数；迁移详见 `docs/migration/cleanup-non-czsc-core.md`）

7. **`czsc/connectors/`** - 数据源连接器：
   - 支持天勤、Tushare、CCXT 等多个数据源
   - 统一的数据接口封装；`local_data.py`（原 `research.py`）提供 CZSC 投研共享数据的本地缓存读取入口

### 信号-事件-交易体系

项目实现了系统化的量化交易方法：
- **信号（Signals）**: 基础技术指标和市场状态
- **事件（Events）**: 信号的逻辑组合，通过 signals_all/signals_any/signals_not 实现 AND/OR/NOT 逻辑
- **交易（Trading）**: 基于事件和风险管理的执行

### 多级别联立分析

CZSC 支持使用 `CzscTrader` 类进行多级别联立分析，可同时分析不同时间周期（如1分钟、5分钟、30分钟、日线）进行全面的市场决策。

## 开发指南

### 代码规范
- 行长度：120字符（在 pyproject.toml 中配置）
- 适当使用类型提示
- 遵循代码库中现有的命名约定
- 信号函数通过 `#[signal]` 宏在 Rust 端自动注册到 `SIGNAL_REGISTRY`，命名遵循 Rust 模块约定，不再使用历史上的 `V<yyMMdd>` 版本后缀
- **代码质量原则**：
  - **DRY（Don't Repeat Yourself）**: 提取重复代码为辅助函数
  - **KISS（Keep It Simple）**: 保持函数简洁，职责单一
  - **使用模块级常量**: 避免魔法值，集中管理配置
  - **类型提示优先**: 使用 `Literal`、`Optional` 等提升代码可读性
  - **向后兼容性**: 公共 API 修改需谨慎，避免破坏现有代码
  - **文档完整**: 所有公共函数必须有完整的 docstring

### 信号函数开发
- 信号函数应遵循飞书文档中的规范说明
- 信号函数由 Rust 实现，位于 `crates/czsc-signals/` 中
- 原 Python 版 `czsc/signals/` 已彻底删除（Phase J）；新增信号需在 Rust 侧开发
- 信号解析公共 API：`get_signals_config(signals_seq)` / `get_signals_freqs(signals_seq)`（来自 `czsc.traders`）
- `SignalsParser` 类已删除，直接使用上述两个函数

### 数据处理最佳实践
- 测试数据统一通过 `czsc.mock.generate_symbol_kines` 生成
- 使用 `format_standard_kline` 将DataFrame转换为RawBar对象列表
- 使用 `BarGenerator` 进行K线合成和多级别分析
- 通过 `DataClient` 统一访问不同数据源
- 注意使用磁盘缓存提高重复计算效率

### 数据格式转换
```python
# 从mock数据生成CZSC对象的正确模式（czsc.core 已删除，全部走顶层 czsc 命名空间）
from czsc import CZSC, Freq, format_standard_kline
from czsc.mock import generate_symbol_kines

# 生成K线数据
df = generate_symbol_kines('000001', '30分钟', '20240101', '20240105')

# 转换为RawBar对象列表
bars = format_standard_kline(df, freq=Freq.F30)

# 创建CZSC分析对象
czsc_obj = CZSC(bars)
```

### 回测可视化

`czsc.utils.plotting.backtest` 模块已在二阶段清理 PR-C 删除。推荐做法：

- **权重回测报告**：`wbt.generate_backtest_report(dfw, ...)` 生成自包含 HTML（参见 `docs/examples/13_event_weight_backtest.py`）
- **缠论 + 多周期联立**：`czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}` 输出 lightweight-charts HTML
- **单周期 K 线 + 缠论结构**：`czsc.utils.plotting.kline.KlineChart` / `plot_czsc_chart`
- **自定义统计图**：直接用 `plotly.express` / `plotly.graph_objects`，迁移示例见 `docs/migration/cleanup-non-czsc-core.md`

### 依赖管理（UV配置）
- 核心运行时依赖定义在 `pyproject.toml` 的 `[project.dependencies]` 中
- 开发依赖在 `[project.optional-dependencies.dev]` 中
- 测试依赖在 `[project.optional-dependencies.test]` 中
- 使用 UV 进行依赖管理和虚拟环境控制
- 项目使用 UV 管理 Python 依赖与虚拟环境（详见根目录 README "开发环境" 章节）

## 关键环境变量和设置

- `CZSC_VERBOSE` / `czsc_verbose`：是否打印详细日志（来自 `czsc.envs`）
- `CZSC_MIN_BI_LEN` / `czsc_min_bi_len`：最小笔长度，默认 6（来自 `czsc.envs`）
- `CZSC_MAX_BI_NUM` / `czsc_max_bi_num`：最大笔数量，默认 50（来自 `czsc.envs`）
- 大小写两种写法都接受，大写优先；构造器显式参数优先级最高
- `CZSC_USE_PYTHON` 已**废弃**（spec §3.4，Python 回退路径已删，所有调用统一走 Rust）
- 缓存目录自动管理，具备大小监控功能

## 缓存管理

项目大量使用磁盘缓存：
- 缓存位置：`czsc.home_path`（顶层）或 `czsc.utils.data.cache.home_path`（实际定义处）
- 清除缓存：`czsc.empty_cache_path()`
- 监控大小：`czsc.get_dir_size(czsc.home_path)`
- 当缓存超过1GB时 `czsc.welcome()` 会显示清理提示

## 可视化（Plotly + HTML）

本次清理 起项目不再依赖 streamlit。所有可视化统一由 plotly 实现，输出方式：

- `czsc.utils.plotting.kline.KlineChart` / `plot_czsc_chart`：单周期 K 线 + 缠论结构（plotly Figure，可 `fig.show()` 或写 HTML）
- `czsc.utils.plotting.weight.*`：权重时序图（plotly）
- `czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}`：lightweight-charts 自包含 HTML，多周期联立 + 信号叠加

如需在 streamlit 中嵌入，调用方自行 `pip install streamlit` 后 `st.components.v1.html(plot_czsc(c, output='html'))` 即可（`czsc.svc` 已删除，参见 `docs/migration/cleanup-non-czsc-core.md`）。

## Rust/Python 混合架构

项目核心算法用 Rust 实现，通过 PyO3 暴露给 Python：
- **构建方式**：`maturin + Rust workspace`，扩展模块名 `czsc._native`
- **唯一架构**：Rust 是缠论核心算法的唯一实现；Python 端不再保留任何回退（spec §3.1 / §3.4）
- **API 暴露**：所有面向用户的 API 都通过 `czsc.xxx` 顶层命名空间暴露，禁止用户感知 `czsc._native`
- **Python/Rust 分工**：见本文件顶部「🏛️ 开发宪法 · 第一条」。该条款是硬约束，与此冲突的任何"局部例外"都不成立。
- **类型 stub**：`czsc/py.typed` 启用 inline 类型注解；扩展模块 stub 已生成于 `czsc/_native/__init__.pyi`，由 `pyo3-stub-gen` 自动维护
- **构建环境约束**：`pyo3-stub-gen` 与 `pyo3` 0.22 都要求 Python ≥ 3.10；通过 `crates/czsc-python/build.rs` 在编译期校验 `PYO3_PYTHON`，低于 3.10 时直接报错
- **版本号锁死**（PR-5）：crates.io 与 PyPI 必须使用同一版本号。**唯一版本源**是 `Cargo.toml [workspace.package].version`；`pyproject.toml` 用 `dynamic = ["version"]`，由 maturin 在打 wheel 时从 Cargo workspace 注入。`crates/czsc-python/build.rs` 会在编译期校验 pyproject.toml 仍然走 dynamic 路径，禁止硬编码 `version = "..."`
- **发版流程**：bump `Cargo.toml [workspace.package].version` 后，同步 publish 到 crates.io（`cargo publish`）与 PyPI（`maturin publish`）；CHANGELOG 必须列出本次 release 的 breaking changes
- **rs-czsc 关系**：czsc 一次性 fork rs-czsc 的 Rust 实现进本仓库，**不再做季度同步**；`tests/parity/` 目录已删除，不再保留 rs-czsc parity 比对测试

## 数据连接器支持

项目集成多个数据源连接器（见 `czsc/connectors/`）：
- `tq_connector.py`: 天勤数据源
- `ts_connector.py`: Tushare 数据源
- `ccxt_connector.py`: 数字货币数据源
- `local_data.py`: 投研数据本地缓存接口（原 `research.py`，已于评审决议中改名）

## 回测和策略研究框架

### 策略开发基础（`czsc/strategies.py`）
- `CzscStrategyBase`: 策略开发的抽象基类
- `CzscJsonStrategy`: JSON 配置化的策略实现
- 策略要素：品种参数、K线周期、信号配置、持仓策略
- 支持策略序列化和反序列化
- 研究入口统一指向 `czsc.research.run_research / run_replay / run_optimize_batch`（Rust 后端）

### 信号函数体系（`czsc._native.signals`）
- 信号函数由 Rust 实现，通过 PyO3 暴露为 `czsc._native.signals.*`
- 完整分组以 `crates/czsc-signals/src/` 为准（13+ 子模块）；自查命令：`ls crates/czsc-signals/src/`
- 注册机制：`#[signal]` 宏自动注册到 `SIGNAL_REGISTRY`，不再使用 `V<yyMMdd>` 版本后缀
- 原 Python `czsc/signals/` 目录已彻底删除（Phase J）
- 信号配置解析：`get_signals_config` / `get_signals_freqs`（`czsc.traders`），底层调用 Rust 端 `derive_signals_config` / `derive_signals_freqs`

### 探索性数据分析（`czsc/eda.py`）
- `monotonicity`: 单调性分析
- `weights_simple_ensemble`: 多策略权重集成
- `cal_trade_price`: 交易价格表计算
- `mark_cta_periods`: 标记CTA最易/最难赚钱时间段
- `mark_volatility`: 标记高/低波动率时间段
- `cal_yearly_days`: 年度交易日数量
- `turnover_rate`: 换手率计算

## 重要文档和资源

- [项目文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)
- [信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)
- [API文档](https://czsc.readthedocs.io/en/latest/modules.html)
- [B站视频教程](https://space.bilibili.com/243682308/channel/series)

## 示例代码和用例

项目维护的示例代码集中在 `docs/examples/` 下（如 `08_weight_backtest.py`、`13_lightweight_charts_html.py`、`15_lightweight_signals_html.py` 等）；历史上的 streamlit 示例（10/11/12/14/16）已在 本次清理 删除，HTML 路径示例（13/15）完整保留。

## 项目特色和最佳实践

1. **混合架构设计**: Rust性能优化 + Python灵活性
2. **多级别联立分析**: 支持多时间周期综合决策
3. **系统化信号体系**: 信号→事件→交易的完整流程
4. **丰富的数据源**: 支持A股、期货、数字货币等多市场
5. **完善的测试框架**: 统一的模拟数据生成和测试规范
6. **可视化工具**: Plotly + lightweight-charts HTML 输出，无 streamlit 强依赖
7. **策略研究工具**: CTA框架、参数优化、回测分析一体化
8. **代码质量优化**: 遵循 DRY、KISS、SOLID 原则
   - 使用模块级常量消除魔法值
   - 提取辅助函数减少代码重复
   - 完善的类型提示（Type Hints）
   - 清晰的函数职责分离
   - 保持向后兼容性的 API 设计