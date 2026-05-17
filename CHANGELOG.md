# Changelog

本项目的版本变更记录，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

> 1.0.X 之前的版本变更可在 git 历史与 [GitHub Releases](https://github.com/waditu/czsc/releases) 查看。

---

## [1.0.0] — 2026-05-16

> **里程碑版本。** 缠论核心算法（分型、笔、中枢、信号体系）从 Python 迁移到 Rust，
> 通过 PyO3 扩展 `czsc._native` 暴露给 Python 用户；Rust 用户可直接
> `cargo add czsc`（或子 crate）使用。本版本含大量 **breaking changes**，从
> 0.9.X / 0.10.X 升级请阅读下方「迁移指引」。

### 架构总览

```
czsc (Python 包)
├── czsc._native          ← Rust 扩展（PyO3），缠论核心
│   ├── CZSC / FX / BI / ZS / RawBar / NewBar / BarGenerator
│   ├── Freq / Mark / Direction / Signal / Event / Position / Operate
│   ├── CzscTrader / CzscSignals / generate_czsc_signals
│   ├── signals.*         ← 250+ 信号函数（13+ 子模块）
│   └── ta.*              ← Rust TA 算子（ema/sma/boll 等）
├── czsc.traders          ← Python 门面，汇聚 Rust 交易 API
├── czsc.svc              ← Streamlit 量化研究组件库（静态 import）
├── czsc.utils.plotting   ← Plotly 可视化 + lightweight_charts
└── czsc.connectors       ← 数据源接入（tq / ts / ccxt / local_data）
```

Rust workspace 同步发布到 crates.io，按依赖层拆分为 7 个 crate：
`czsc-derive` / `czsc-signal-macros` / `czsc-core` / `czsc-ta` / `czsc-utils` /
`czsc-signals` / `czsc-trader`，以及 facade crate `czsc`。

### Breaking changes

#### 核心算法 / 模块结构

- **删除 Python 版缠论核心实现**。`czsc.core` 模块整体删除，所有核心对象
  （`CZSC` / `FX` / `BI` / `ZS` / `RawBar` / `NewBar` / `BarGenerator` 等）改由 Rust
  实现并通过 `czsc._native` 暴露。Python 端不再保留任何回退路径。
- **删除环境变量 `CZSC_USE_PYTHON`**。原用于切换 Python / Rust 实现，
  Python 实现已退役，该变量无意义。
- **删除 `czsc/signals/` Python 命名空间层**。原 Python 版信号函数全部删除，
  改用 Rust 实现（`czsc._native.signals.*`，13+ 子模块、250+ 信号函数，自查
  `ls crates/czsc-signals/src/`）。
- **信号函数命名规则变化**。不再使用 `V<yyMMdd>` 版本后缀，改用 Rust 模块约定，
  由 `#[signal]` 宏自动注册到 `SIGNAL_REGISTRY`。新增信号函数需在 Rust 侧开发。
- **删除 `czsc.SignalsParser` 类**。改用 `czsc.traders.get_signals_config` /
  `czsc.traders.get_signals_freqs` 两个函数；底层调用 Rust 端
  `derive_signals_config` / `derive_signals_freqs`。

#### 工具模块整合

- **删除 `czsc.utils.bar_generator` / `czsc.utils.bi_info`**。Rust 已实现等价能力。
- **删除 `czsc.utils.st_components`**。所有 Streamlit 组件统一收敛到 `czsc.svc/`。
  `czsc.svc` 改为静态 import（不再 lazy loading）。
- **删除 `czsc.utils.ta` 模块**。Plotly 仪表盘场景的 MACD（×2 约定）下沉为
  `czsc/utils/plotting/_macd.py` 私有辅助；通用 TA 算子使用 `czsc.ta.*`
  （Rust 实现，`czsc._native.ta`）。
- **删除 `czsc.utils.crypto` 模块及 `cryptography` 依赖**。
- **删除 `czsc.utils.sig` / `czsc.utils.oss`**。
- **删除 `czsc.utils.echarts_plot` / `pdf_report` / `pdf_report_builder` /
  `html_report_builder` / `word_writer` / `signal_analyzer`**。可视化全面收敛到
  Plotly + lightweight_charts。
- **删除 `czsc.eda` 中 13 个无实质调用的工具函数**（仅保留 README / CLAUDE.md
  中明确列出的入口）。
- **删除 `stoploss_by_direction` / `cross_sectional_strategy`**。
- **删除 `czsc/sensors/`** 目录（原方案中标记为 partial restore 但最终未保留）。

#### 数据源接入

- **`czsc.connectors.research` → `czsc.connectors.local_data`**（评审决议改名）。
  仍提供 CZSC 投研共享数据的本地缓存读取入口。

#### 测试 / 构建

- **测试目录改名 `test/` → `tests/`**。
- **删除 `tests/parity/` 目录**。一次性 fork rs-czsc 的 Rust 实现进本仓库后，
  不再做季度 parity 比对。
- **`rs-czsc` 运行时依赖删除**。本仓库直接通过 maturin 打包 Rust workspace。
- **TA-Lib 切换**。运行时不再依赖 C TA-Lib；`tests/unit/test_ta_parity.py`
  用 `talib-rs`（纯 Rust，drop-in 兼容）与 `czsc._native.ta` 做 parity 校验。
- **代码质量工具切换**。`ruff` + `basedpyright` 取代 `black` / `flake8` /
  `isort` / `mypy`。
- **最低 Python 版本提升到 3.10**（abi3-py310 + `pyo3-stub-gen` 与 `pyo3` 0.28
  的下限要求）。
- **wheel 改用 abi3**。一个 wheel 覆盖 Python 3.10 / 3.11 / 3.12 / 3.13。

#### 清理非缠论核心 API（PR #313，1.0.0 核心重构延续）

> 移除 Streamlit 可视化命名空间 `czsc.svc`、Python 端 `czsc.ta` 顶层别名、streamlit 运行时依赖与 5 个 streamlit 示例。Rust 侧 `czsc._native.ta` 仍保留供信号内部使用；HTML 可视化路径（`czsc.utils.plotting.*` 与 `lightweight.plot_czsc*`）完整保留。

- **删除 `czsc.svc` 子包**。原 60+ 个 `show_*` Streamlit 组件全部移除（`czsc/svc/` 整目录，约 4800 行）。替代方案：用 `czsc.utils.plotting.backtest.plot_*`（plotly + HTML）或 `czsc.utils.plotting.lightweight.*`（lightweight-charts）。
- **删除 `czsc.ta` 顶层 alias**。Rust 实现 `czsc._native.ta` 仍可用；信号函数内部继续依赖。顶层算子别名 `czsc.ema` / `czsc.sma` / `czsc.rolling_rank` / `czsc.boll_positions` / `czsc.ultimate_smoother` 保留（来自 `from czsc._native import ema, sma, ...`）。
- **删除 `streamlit` 核心依赖**。`pyproject.toml` 不再依赖 streamlit；`uv pip install czsc` 后 streamlit **不会**被自动安装。需要 streamlit 集成时调用方自行 `pip install streamlit` 并 `st.components.v1.html(plot_czsc(c, output='html'))`。
- **删除 lightweight 的 `output="streamlit"` 路径**。`czsc.utils.plotting.lightweight._streamlit_renderer` 整文件删除；`plot_czsc` / `plot_czsc_trader` / `plot_czsc_signals` 的 `output` 参数仅接受 `"html"`。
- **删除 streamlit 示例**：`docs/examples/{10,11,12,14,16}_streamlit_*.py` 与 `_streamlit_smoke.py`。HTML 路径示例 `13_lightweight_charts_html.py` / `15_lightweight_signals_html.py` 完整保留。
- **删除 ta 数值等价测试**：`tests/unit/test_ta_parity.py` 整文件删除；数值正确性由 Rust 侧 `cargo test --package czsc-ta` 覆盖。
- 新增 `tests/compat/test_api_no_streamlit.py` 防护测试 + `tests/compat/baselines/` 基线快照；`test_public_api.py` 增 `test_ta_namespace_removed` / `test_svc_subpackage_removed`；snapshot `top_level` 移除 `"svc"` / `"ta"`、`ta` 整组迁入 `removed_ta`。
- 迁移详见 [`docs/migration/cleanup-non-czsc-core.md`](docs/migration/cleanup-non-czsc-core.md)。

### Added

- **Rust workspace 同步发布到 crates.io**：7 个 crate 按依赖图分层串行发布，
  Rust 用户可 `cargo add czsc-core` / `czsc-signals` / `czsc-trader` 等。
  CI 在 `.github/workflows/rust-publish.yml`，支持断点续发（`start_layer` /
  `end_layer`）。
- **单一版本源**。`Cargo.toml [workspace.package].version` 是唯一版本来源，
  `pyproject.toml` 用 `dynamic = ["version"]` 由 maturin 注入；
  `crates/czsc-python/build.rs` 编译期校验。
- **wheel 矩阵**。abi3 wheel 覆盖 Linux x86_64/aarch64/musl + macOS x86_64/arm64
  + Windows x64，含 sdist 与 smoke-test，PyPI 走 Trusted Publishing/OIDC。
- **`czsc._native/__init__.pyi` 类型 stub**。由 `pyo3-stub-gen` 0.22 在
  `crates/czsc-python/src/bin/stub_gen.rs` 中自动生成；CI 有 stub-drift 检查
  强制 Rust 装饰器与 stub 一致。
- **`czsc.utils.plotting.lightweight`**。基于 lightweight-charts 的缠论可视化
  （HTML 与 Streamlit 双输出）；`plot_czsc_signals` 顶层 API 提供信号 overlay、
  Signal Timeline 副 pane、tooltip SIGNALS 段、hover 双向高亮、跨周期联动。
- **`czsc.utils.plotting.backtest`**。回测可视化全套：
  `plot_cumulative_returns` / `plot_drawdown_analysis` /
  `plot_daily_return_distribution` / `plot_monthly_heatmap` /
  `plot_backtest_stats` / `plot_colored_table` / `plot_long_short_comparison`。
- **`docs/examples/`**。12+ 独立可运行案例，覆盖 K 线图、回测、Event 驱动、
  lightweight_charts 信号叠加等场景，`docs/examples.md` 为总目录。

### Changed

- **`czsc.__init__.py` 退役 lazy loading**，按 spec §3.1 改为静态 import；
  顶层 import 时间收敛，LoC 减少 ~54%。
- **`czsc.traders.sig_parse` / `czsc.traders.base`** 改为 `czsc._native` 纯透传，
  不再承担参数适配 / 返回值转换。Python wrapper 的等价逻辑全部下沉到 Rust
  （含 `SignalConfig` 自定义 Deserialize 同时接受嵌套/展平形态、
  `Signal` `FromPyObject` 同时接受 `"k_v"` 字符串与 `{key, value}` 字典等）。
- **`czsc.envs` 精简**：从 117 行降至 49 行（-58%）；保留 `CZSC_VERBOSE` /
  `CZSC_MIN_BI_LEN` / `CZSC_MAX_BI_NUM` 等核心环境变量。

### Dependencies

- 升级 Rust workspace 全部依赖到 2026 年最新版本；`polars` 暂停在 0.52.0
  （等 polars 0.53.x 与 `pyo3-stub-gen` 0.21+ 的 `chrono` 约束冲突解决）。
- `pyo3` 升级到 0.28，`numpy` 0.28；workspace 层不启用 `extension-module`
  feature，只在 `czsc-python` 中启用（让其他 crate 的 cargo test 能正常链接
  libpython）。
- 删除：`cryptography`、`rs-czsc`、C TA-Lib 运行时依赖、其他多个无 import
  的核心依赖。

### Migration guide

下面给出常见使用场景的 0.10.X → 1.0.0 迁移示例。

#### 1. 核心对象导入

```python
# v0.10.X
from czsc.core import CZSC, RawBar, Freq
from czsc.utils.bar_generator import BarGenerator

# v1.0.0
from czsc import CZSC, RawBar, Freq, BarGenerator
```

#### 2. 信号函数导入

```python
# v0.10.X — Python 实现，文件名带版本后缀
from czsc.signals.bar import bar_end_V221111

# v1.0.0 — Rust 实现，无版本后缀
from czsc._native.signals.bar import bar_end          # 直接调用
# 或更常见地，通过 generate_czsc_signals 传配置字符串使用：
from czsc.traders import generate_czsc_signals
signals_seq = ["bar_end_V0", ...]  # 命名以 crates/czsc-signals/src/ 为准
```

#### 3. 信号配置解析

```python
# v0.10.X
from czsc import SignalsParser
parser = SignalsParser()
config = parser.parse(signals_seq)
freqs = parser.get_freqs(signals_seq)

# v1.0.0
from czsc.traders import get_signals_config, get_signals_freqs
config = get_signals_config(signals_seq)
freqs = get_signals_freqs(signals_seq)
```

#### 4. Streamlit 可视化组件

```python
# v0.10.X
from czsc.utils.st_components import show_daily_return, show_weight_backtest

# v1.0.0 — 静态 import，路径变化
from czsc.svc import show_daily_return, show_weight_backtest
# 或直接 import czsc.svc 命名空间使用：
import czsc.svc as svc
svc.show_daily_return(...)
```

#### 5. 投研数据接入

```python
# v0.10.X
from czsc.connectors.research import get_raw_bars

# v1.0.0
from czsc.connectors.local_data import get_raw_bars
```

#### 6. TA 算子

```python
# v0.10.X
from czsc.utils.ta import EMA, SMA, BOLL

# v1.0.0
import czsc._native.ta as ta            # 完整命名空间
ema = ta.ema(values, n=20)
sma = ta.sma(values, n=20)
boll_pos = ta.boll_positions(values)
```

#### 7. 环境变量

```python
# v0.10.X
import os
os.environ["CZSC_USE_PYTHON"] = "1"  # 已退役，删除该行即可

# v1.0.0 — 无 Python 回退，所有调用统一走 Rust
# CZSC_VERBOSE / CZSC_MIN_BI_LEN / CZSC_MAX_BI_NUM 仍可用
```

#### 8. 回测可视化

```python
# v0.10.X — pdf / word / echarts 多套报告
from czsc.utils.pdf_report import generate_pdf_report
from czsc.utils.echarts_plot import KlineChart

# v1.0.0 — 统一 Plotly + lightweight_charts
from czsc.utils.plotting.backtest import plot_backtest_stats, plot_cumulative_returns
fig = plot_backtest_stats(dret, ret_col="total")
fig.show()
```

### Verification log

- pytest 默认套件：**231 passed / 6 skipped**
- pytest `--run-slow`（慢测试）：**5 passed**
- ruff check / ruff format / cargo fmt / clippy / basedpyright：全绿
- stub-drift CI：`czsc/_native/__init__.pyi` 与 Rust 装饰器一致
- wheel 矩阵 smoke-test：Linux x86_64 / macOS x86_64 / macOS arm64 / Windows x64
- 基准（Criterion，spec §6）：`CZSC::new` ≈ 96.585 ms（预算 200 ms）；
  222 个信号 dispatch ≈ 1.1 µs/signal、4.7 ms/10K

### Notes

- 后续版本号策略：crates.io 与 PyPI 共享同一版本号；
  bump `Cargo.toml [workspace.package].version` 即可，pyproject.toml 自动同步。
- 旧 Python 实现可在 `v0.9.69` tag 或 [0.9.X 分支](https://github.com/waditu/czsc/tree/v0.9.69) 查看。

[1.0.0]: https://github.com/waditu/czsc/releases/tag/v1.0.0
