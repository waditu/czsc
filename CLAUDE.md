# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CZSC（缠中说禅技术分析工具）是基于缠中说禅理论的综合性量化交易Python库，提供技术分析、信号生成、回测和市场分析等功能。本项目专注于实现缠论的分型、笔、线段等核心概念的自动识别，以及基于此的多级别量化交易策略。

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
   - 暴露 `czsc._native.ta.*`（Rust TA 算子，对应 `czsc.ta.*`）
   - **不存在 Python 回退**：`czsc/py/` 与 `czsc/core.py` 已在 Phase H 删除；`CZSC_USE_PYTHON` 环境变量已退役（spec §3.4）

2. **`crates/`** - Rust workspace（9 个 crate）：
   - `czsc` / `czsc-core` / `czsc-derive` / `czsc-signals` / `czsc-trader` / `czsc-utils` / `czsc-ta`
   - `czsc-signal-macros`（proc-macro，`#[signal]` 注册宏）
   - `czsc-python`（PyO3 binding 总入口，唯一启用 `pyo3/extension-module` 的 crate）

3. **`czsc/traders/`** - 交易执行框架：
   - `base.py`: CzscSignals / CzscTrader / generate_czsc_signals / get_signals_config / get_signals_freqs
   - `optimize.py`: 开仓 / 平仓参数优化（`build_open_optim_positions` / `build_exit_optim_positions` / `run_optimize_batch`）
   - `sig_parse.py`: 信号字符串解析（`parse_signal_doc` / `ParsedSignalDoc`，原 `SignalsParser` 类已删除）

4. **`czsc/_native.signals`** - 信号函数（Rust 实现，通过 PyO3 暴露）：
   - 完整分组以 `crates/czsc-signals/src/` 为准（13+ 子模块），自查命令：`ls crates/czsc-signals/src/`
   - 原 `czsc/signals/` Python 命名空间层已在 Phase J **彻底删除**
   - 通过 `czsc.traders.generate_czsc_signals` 等接口调用信号
   - 信号解析 API：`get_signals_config` / `get_signals_freqs`（`czsc.traders`）；`SignalsParser` 类已删除

5. **`czsc/utils/`** - 工具模块（Phase J 精简后）：
   - `data/cache.py` / `io.py` / `log.py` / `kline_quality.py`：缓存、IO、日志、K 线质量校验
   - `analysis/`（`stats.py` 业绩统计 / `corr.py` 相关性分析）
   - `data/client.py`：统一数据客户端接口
   - TA 算子由 Rust `czsc.ta.*`（`czsc._native.ta`）提供；仪表盘场景的 MACD（×2 约定）已下沉为 `czsc/utils/plotting/_macd.py` 私有辅助
   - `trade.py`：交易工具
   - `plotting/{kline,backtest,weight,common}.py`：Plotly 图表绘制
   - 已删除：`bar_generator.py` / `bi_info.py`（Rust 已实现）、`st_components.py`（迁至 `czsc/svc/`）、`echarts_*` / `pdf_report` / `html_report_builder` / `word_writer` / `signal_analyzer` / `crypto/`（spec §9 完全删除）
   - `plotting/backtest.py` 主要函数：
     - `plot_cumulative_returns()`: 累计收益曲线
     - `plot_drawdown_analysis()`: 回撤分析图
     - `plot_daily_return_distribution()`: 日收益分布
     - `plot_monthly_heatmap()`: 月度收益热力图
     - `plot_backtest_stats()`: 回测统计概览（3图组合）
     - `plot_colored_table()`: 带颜色编码的绩效表格
     - `plot_long_short_comparison()`: 多空收益对比

7. **`czsc/svc/`** - 统计和可视化服务：
   - `backtest.py`: 回测分析工具
   - `factor.py`: 因子分析
   - `correlation.py`: 相关性分析
   - `statistics.py`: 统计分析工具

8. **`czsc/connectors/`** - 数据源连接器：
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

### 回测可视化最佳实践
```python
# 使用 plotting/backtest.py 绘制回测图表（或通过 czsc.utils 懒加载）
from czsc.utils.plotting.backtest import (
    plot_cumulative_returns,
    plot_backtest_stats,
    plot_monthly_heatmap
)

# 准备日收益数据（index为日期，columns为策略收益）
dret = ...  # DataFrame with datetime index and returns columns

# 1. 绘制累计收益曲线
fig = plot_cumulative_returns(
    dret,
    title="策略累计收益",
    template="plotly",  # 或 "plotly_dark"
    to_html=False  # 返回 Figure 对象，True 则返回 HTML 字符串
)
fig.show()

# 2. 绘制综合回测统计图（包含回撤分析、收益分布、月度热力图）
fig = plot_backtest_stats(
    dret,
    ret_col="total",  # 指定收益列
    title="回测统计概览",
    template="plotly"
)
fig.show()

# 3. 单独绘制月度收益热力图
fig = plot_monthly_heatmap(dret, ret_col="total")
fig.show()

# 4. 导出为 HTML（用于报告）
html_str = plot_cumulative_returns(dret, to_html=True)
with open("backtest_report.html", "w", encoding="utf-8") as f:
    f.write(html_str)
```

**模块级常量使用：**
```python
from czsc.utils.plotting.common import (
    COLOR_DRAWDOWN,
    COLOR_RETURN,
    SIGMA_LEVELS,
    MONTH_LABELS
)

# 使用预定义常量确保图表风格统一
# 避免硬编码颜色值和配置参数
```

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

## Streamlit 集成

项目在 `czsc/svc/`（Streamlit Visualize Components）中提供完整的可视化组件库，覆盖回测、相关性、因子、统计、策略、权重等场景。`czsc.svc` 在 `czsc/__init__.py` 中按 spec §3.1 改为静态 import，**不再走 lazy loading**——访问 `czsc.svc` 即可，无需任何延迟初始化。

> 注：原 `czsc/utils/st_components.py` 已在 Phase J 删除，所有 Streamlit 组件统一收敛到 `czsc/svc/`。

## Rust/Python 混合架构

项目核心算法用 Rust 实现，通过 PyO3 暴露给 Python：
- **构建方式**：`maturin + Rust workspace`，扩展模块名 `czsc._native`
- **唯一架构**：Rust 是缠论核心算法的唯一实现；Python 端不再保留任何回退（spec §3.1 / §3.4）
- **API 暴露**：所有面向用户的 API 都通过 `czsc.xxx` 顶层命名空间暴露，禁止用户感知 `czsc._native`
- **Python/Rust 分工**：Python 端**不承担**"为 Python 用户做参数适配 / 返回值转换"的职责。这类逻辑统一下沉到 Rust 端实现（修改现有 API 或新增 API），Python 侧仅保留**纯透传**或**不可避免的 PyO3 边界胶水**（如 DataFrame ↔ Arrow IPC 序列化）。**目标**：让 `cargo add czsc` 的 Rust 用户与 `pip install czsc` 的 Python 用户拿到行为一致的接口，避免"两种语言用户调同一个名字但拿到不同结果"。新增 Python wrapper 前必须先评估"能不能改成 Rust 实现"
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

项目维护的示例代码集中在 `docs/examples/` 下（如 `12_streamlit_research.py`、`30分钟笔非多即空.py` 等）；
历史上的 `examples/` / `examples/develop/` / `examples/signals_dev/` / `examples/animotion/`、
`docs/source/` 等目录已不再保留，仅在历史 commit 中可查。

## 项目特色和最佳实践

1. **混合架构设计**: Rust性能优化 + Python灵活性
2. **多级别联立分析**: 支持多时间周期综合决策
3. **系统化信号体系**: 信号→事件→交易的完整流程
4. **丰富的数据源**: 支持A股、期货、数字货币等多市场
5. **完善的测试框架**: 统一的模拟数据生成和测试规范
6. **可视化工具**: Streamlit组件库支持快速分析展示
7. **策略研究工具**: CTA框架、参数优化、回测分析一体化
8. **代码质量优化**: 遵循 DRY、KISS、SOLID 原则
   - 使用模块级常量消除魔法值
   - 提取辅助函数减少代码重复
   - 完善的类型提示（Type Hints）
   - 清晰的函数职责分离
   - 保持向后兼容性的 API 设计

### 代码优化案例（plotting/backtest.py）

`czsc/utils/plotting/backtest.py` 模块展示了代码优化的最佳实践：

**优化前的问题：**
- HTML 转换逻辑重复 8 次
- 年度分隔线添加代码重复 3 次
- 回撤计算逻辑重复 2 次
- 大量魔法值（颜色、分位数等）散落各处
- 函数过于复杂（`plot_backtest_stats` 有 165 行）

**优化措施：**

1. **提取辅助函数**（6 个）：
   ```python
   _figure_to_html()              # 统一 HTML 转换
   _add_year_boundary_lines()     # 统一年度分隔线
   _calculate_drawdown()          # 统一回撤计算
   _create_monthly_heatmap_data() # 统一月度数据准备
   _add_drawdown_annotation()     # 统一回撤标注
   _add_sigma_lines()             # 统一 Sigma 标注
   ```

2. **定义模块级常量**（10 个）：
   ```python
   COLOR_DRAWDOWN = "salmon"
   COLOR_RETURN = "#34a853"
   QUANTILES_DRAWDOWN = [0.05, 0.1, 0.2]
   SIGMA_LEVELS = [-3, -2, -1, 1, 2, 3]
   MONTH_LABELS = ['1月', '2月', ..., '12月']
   ```

3. **完善类型提示**：
   ```python
   TemplateType = Literal['plotly', 'plotly_dark', ...]
   def plot_cumulative_returns(..., template: TemplateType = "plotly", ...)
   ```

**优化效果：**
- ✅ 消除所有 HTML 转换重复代码（8 处 → 1 处）
- ✅ 消除所有年度分隔线重复（3 处 → 1 处）
- ✅ 消除所有回撤计算重复（2 处 → 1 处）
- ✅ 使用模块级常量替代魔法值
- ✅ 函数更简洁易读（165 行 → 129 行）
- ✅ 提升可维护性和可测试性
- ✅ 保持向后兼容性（API 未改变）

**参考文件：** `czsc/utils/plotting/backtest.py`