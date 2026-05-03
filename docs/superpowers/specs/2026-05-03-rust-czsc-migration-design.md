# Rust 实现的 czsc 核心对象迁移 — 设计方案

- 作者：Claude Code (协作设计)
- 日期：2026-05-03
- 状态：草案，待评审
- 关联需求：[飞书需求文档](https://s0cqcxuy3p.feishu.cn/wiki/OZ3dwY68oiJhTdk7HRCcXNPRnCh)
- 关联仓库：`czsc`（本仓库）、`rs-czsc`（参考实现，路径 `../offline/rs_czsc`）

---

## 0. 目标与已确认决策

### 0.1 需求摘要

1. 把整个 `czsc` 库改造成 Rust + PyO3 + Python 混合结构（参考 rs-czsc）
2. 从 rs-czsc 迁移缠论核心 Rust 实现到 czsc 库
3. 重构 czsc 库，仅保留缠论分析/研究必须的工具，大幅删减多余代码，保留 connectors
4. 重构测试体系：Rust 源码测试与 Python 库测试分别遵守对应规则

### 0.2 已确认的设计原则

| # | 决策 | 状态 |
|---|---|---|
| 1 | czsc 内置 Rust 源码（仓库内带 Rust workspace），rs-czsc 仍作为独立项目存在 | 已确认 |
| 2 | 必迁 Rust crate：`czsc-core` + `czsc-signals` + `czsc-trader` + `czsc-utils` + `czsc-ta`（+ 配套 proc-macro / error-support） | 已确认 |
| 3 | Python 端**保留**：`connectors / envs / core / mock / svc / sensors / strategies / utils(精简)` | 已确认 |
| 4 | Python 端**删除**：`py / eda.py / aphorism.py / features / fsa` | 已确认 |
| 5 | 所有面向用户的 API 都通过 `czsc.xxx` 暴露，禁止用户感知 `rs_czsc` 或 `czsc._native` | 已确认 |
| 6 | 构建方式：`maturin + Rust workspace`，扩展模块名 `czsc._native` | 已确认 |
| 7 | rs-czsc 同步策略：复制即 fork，后续靠 cherry-pick + `MIGRATION_NOTES.md` 记录 | 已确认 |

---

## 1. 仓库结构

```
czsc/
├── Cargo.toml                        # workspace 根
├── pyproject.toml                    # build-system = maturin
├── rust-toolchain.toml               # stable
├── .cargo/config.toml                # release: lto=true, opt-level=3, codegen-units=1
│
├── crates/                           # ← 新增：Rust workspace 成员（9 个 crate）
│   ├── czsc-core/                    # 缠论核心算法（CZSC/FX/BI/ZS/...）
│   ├── czsc-signals/                 # 30+ 信号函数（macro 注册）
│   ├── czsc-trader/                  # 回测/权重/优化/CzscTrader
│   ├── czsc-utils/                   # BarGenerator/日历/错误/性能详情
│   ├── czsc-ta/                      # 25+ 技术分析算子（pure + mixed）
│   ├── czsc-signal-macros/           # proc-macro：#[signal_module] 注册
│   ├── error-macros/                 # proc-macro：错误类型生成
│   ├── error-support/                # 错误基础库
│   └── czsc-python/                  # PyO3 binding 总入口 → 产出 czsc._native
│
├── czsc/                             # Python 包（精简后约 8K 行）
│   ├── __init__.py                   # 重写，统一从 czsc.xxx 暴露
│   ├── _native.pyi                   # type stub（pyo3-stub-gen 生成）
│   ├── envs.py                       # 仅保留 czsc_min_bi_len / czsc_max_bi_num / czsc_verbose
│   ├── core.py                       # 极简：from czsc._native import *
│   ├── mock.py                       # 测试数据生成（保留）
│   ├── strategies.py                 # 保留（svc/sensors 依赖的 CzscStrategyBase / CzscJsonStrategy）
│   ├── connectors/                   # 完整保留（5 个连接器：tushare/tqsdk/ccxt/research/cooperation）
│   ├── sensors/                      # 完整保留（CTAResearch + 工具）
│   ├── svc/                          # 完整保留（Streamlit 可视化组件）
│   ├── signals/                      # 极薄，仅 re-export Rust 信号到 czsc.signals.{bar,cxt,...}
│   ├── traders/                      # 极薄，仅 re-export Rust 对象 + 保留 dummy/sig_parse
│   ├── ta/                           # 极薄，re-export Rust ta 算子（与 utils/ta.py 命名空间分离）
│   └── utils/                        # 大幅精简至 ~2.5K 行（详见 §3.2）
│
├── test/                             # Python pytest 套件
│   ├── conftest.py                   # 注入 czsc.mock fixtures
│   ├── unit/                         # 单元测试（核心对象、信号、TA）
│   ├── integration/                  # 集成测试（trader、回测、connectors）
│   └── compat/                       # API 兼容快照（锁定 czsc.* 公共名称）
│
├── docs/
│   ├── superpowers/specs/            # 本设计文档存放地
│   ├── MIGRATION_NOTES.md            # 记录从 rs-czsc 哪个 commit 复制而来
│   └── ...
│
└── examples/                         # 保留示例（同步调整 import）
```

**删除**：`czsc/py/`、`czsc/eda.py`、`czsc/aphorism.py`、`czsc/features/`、`czsc/fsa/`，以及 `czsc/utils/` 中所有可视化/报告生成模块（详见 §3.2）。

---

## 2. Rust workspace 与 PyO3 binding

### 2.1 workspace 配置（顶层 `Cargo.toml`）

```toml
[workspace]
resolver = "2"
members  = ["crates/*"]

[workspace.package]
version    = "1.0.0"
edition    = "2024"
license    = "MIT"
repository = "https://github.com/waditu/czsc"

[workspace.dependencies]
polars         = { version = "0.42.0", features = ["..."] }
chrono         = "0.4"
pyo3           = { version = "0.25", features = ["extension-module", "abi3-py310"] }
numpy          = "0.25"
rayon          = "1"
hashbrown      = "0.14"
serde          = { version = "1", features = ["derive"] }
ordered-float  = "5.0"

[profile.release]
lto           = true
opt-level     = 3
codegen-units = 1
```

### 2.2 crate 依赖图

```
       error-macros (proc-macro)
              │
       error-support
              │
   ┌──────────┼──────────┬───────────┐
czsc-utils  czsc-core  czsc-ta  czsc-signal-macros (proc-macro)
   │          │          │           │
   └─────┬────┴──────────┴───────────┘
         │
   czsc-signals
         │
   czsc-trader
         │
   czsc-python  ← 唯一启用 pyo3/extension-module 的 crate
```

**关键约束**：业务 crate 默认**不直接**依赖 `pyo3`，通过 `feature = "python"` 可选启用。`czsc-python` 是唯一聚合所有 `#[pyclass]` / `#[pyfunction]` 暴露的 crate。这与 rs-czsc 现状一致，便于业务 crate 单独被其它 Rust 项目引用。

### 2.3 czsc-ta 集成方式

- crate 完整复制到 `crates/czsc-ta/`
- 业务调用：`czsc-trader / czsc-signals` 中对 czsc-ta 的引用保持原样
- PyO3 暴露：`czsc-ta` 启用 `rust-numpy` feature，通过 `czsc-python` 注册为 `czsc._native.ta` 子模块
- Python 端命名空间分离：
  - `czsc.ta.*` ← Rust 实现（高性能、向量化、NumPy 互操作）
  - `czsc.utils.ta.*` ← Python TA-Lib wrapper（保持向后兼容）

### 2.4 PyO3 binding 层（`crates/czsc-python`）

```rust
// crates/czsc-python/src/lib.rs
use pyo3::prelude::*;

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    czsc_core::python::register(py, m)?;     // CZSC/FX/BI/ZS/RawBar/NewBar/Freq/Mark/Direction/...
    czsc_utils::python::register(py, m)?;    // BarGenerator/freq_end_time/is_trading_time
    czsc_ta::python::register(py, m)?;       // 25+ TA 算子
    czsc_signals::python::register(py, m)?;  // generate_czsc_signals + 30+ 信号
    czsc_trader::python::register(py, m)?;   // CzscTrader/CzscSignals/WeightBacktest/Position/...
    Ok(())
}
```

- **扩展模块名**：`czsc._native`（`pyproject.toml` 中 `tool.maturin.module-name = "czsc._native"`）
- **type stubs**：`czsc/_native.pyi` 由 `pyo3-stub-gen` 自动生成（沿用 rs-czsc 现有做法）
- **ABI 策略**：`abi3-py310`，一次构建多 Python 版本通用，简化发布矩阵

### 2.5 关键调整：Rust 端可见性提升

在 rs-czsc 中以下 4 个函数为 `pub(crate)`，迁移到 czsc 后需提升为 `pub` 并加 PyO3 binding：

| 函数 | rs-czsc 位置 | 当前可见性 | 调整后 |
|---|---|---|---|
| `remove_include` | `czsc-core/src/analyze/utils.rs:32` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_fxs` | `czsc-core/src/analyze/utils.rs:119` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_fx` | `czsc-core/src/analyze/utils.rs:158` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_bi` | `czsc-core/src/analyze/utils.rs:198` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `is_trading_time` | **rs-czsc 中尚未实现** | — | 在 `czsc-utils` 中**新增** Rust 实现 + `#[pyfunction]` |

`freq_end_time` 已在 `czsc-utils/src/freq_data.rs:245` 是 `pub`，仅需补 PyO3 暴露。

### 2.6 与 rs-czsc 的同步策略

- **不用** git submodule / subtree。**复制即 fork**。
- 维护 `docs/MIGRATION_NOTES.md` 记录基线 commit hash 和迁移日期。
- 后续 rs-czsc 有 bugfix 通过手动 cherry-pick 同步，PR 描述中标注 `[sync from rs-czsc <sha>]`。
- 如果 czsc 端做了独立改动（如新增 `is_trading_time`），同样在 `MIGRATION_NOTES.md` 中标记为 "czsc-only"。

---

## 3. Python 包结构（精简后）

### 3.1 `czsc/__init__.py` 公共 API 表

| 命名空间 | 来源 | 暴露名 |
|---|---|---|
| **顶层核心对象** | `czsc._native` | `CZSC, FX, BI, ZS, RawBar, NewBar, Freq, Mark, Direction, Operate, Signal, Event, Position, BarGenerator, format_standard_kline, freq_end_time, is_trading_time, check_bi, check_fx, check_fxs, remove_include` |
| **顶层交易对象** | `czsc._native` | `CzscTrader, CzscSignals, WeightBacktest, generate_czsc_signals, get_unique_signals` |
| **顶层 TA / 性能函数** | `czsc._native` | `daily_performance, top_drawdowns, ultimate_smoother, rolling_rank, ema, sma, boll_positions, ...`（25+ 函数完整列表见 stubs） |
| `czsc.ta.*` | `czsc._native.ta` | Rust TA 算子的子模块入口，与顶层重复暴露兼容 |
| `czsc.signals.{bar,cxt,tas,vol,...}` | `czsc._native.signals.*` | 30+ 信号函数按类别分组 |
| `czsc.traders.*` | Python 薄层 + `czsc._native` | `CzscTrader, CzscSignals, WeightBacktest, DummyBacktest, SignalsParser` |
| `czsc.connectors.*` | 完整保留 | `tushare/tqsdk/ccxt/research/cooperation` |
| `czsc.sensors.*` | 完整保留 | `CTAResearch` 等 |
| `czsc.svc.*` | 完整保留 | Streamlit dashboard 组件 |
| `czsc.mock` | 完整保留 | `generate_symbol_kines, generate_klines_with_weights` |
| `czsc.envs` | 精简 | `czsc_min_bi_len, czsc_max_bi_num, czsc_verbose` |
| `czsc.strategies` | 保留 | `CzscStrategyBase, CzscJsonStrategy` |
| `czsc.utils.*` | 大幅精简（§3.2） | `cache, io, log, ta, calendar, sig, plot_backtest, plotly_plot, kline_quality, data_client, trade_utils` |

`__init__.py` 中**移除** `_LAZY_MODULES` / `_LAZY_ATTRS` 延迟加载机制。Rust 扩展模块加载快（< 50 ms），所有公共 API 在顶层直接 import。删除 `__getattr__` 动态加载逻辑。

### 3.2 `czsc/utils/` 精简清单

| 文件 | 决策 | 说明 |
|---|---|---|
| `cache.py` | **保留** | 磁盘缓存基础设施 |
| `io.py` | **保留** | dill / json 读写 |
| `log.py` | **保留** | loguru 配置 |
| `ta.py` | **保留** | TA-Lib Python wrapper（与 Rust ta 互补） |
| `calendar.py` | **保留** | 交易日历薄层（核心算法已迁 Rust） |
| `sig.py` | **保留**（精简） | 信号工具函数 `unique_signals` 等 |
| `kline_quality.py` | **保留** | 数据质量校验 |
| `plot_backtest.py` | **保留** | CLAUDE.md 中已重点优化 |
| `plotly_plot.py` | **保留** | svc 依赖 |
| `data_client.py` | **保留** | connectors 依赖的统一接口 |
| `trade.py` / `trade_utils.py` | **保留** | sensors 依赖的辅助函数 |
| `bar_generator.py` | **删除** | Rust 已实现 |
| `bi_info.py` | **删除** | Rust 已实现 |
| `analysis/` | **删除** | 转交 Rust trader |
| `echarts_*.py` | **删除** | 高度专业化、维护成本大 |
| `pdf_report.py` | **删除** | 报告生成超出研究范围 |
| `html_report_builder.py` | **删除** | 同上 |
| `word_writer.py` | **删除** | 同上 |
| `features.py` | **删除** | 与 czsc/features/ 同删 |
| `oss.py` | **删除** | 阿里云对象存储,业务代码 |
| `st_components.py` | **删除** | svc 已包含 Streamlit 组件 |
| `corr.py` | **删除** | 业务代码 |
| `signal_analyzer.py` | **删除** | 业务代码 |

精简后 `czsc/utils/` 从 ~10.7K 行降到 ~2.5K 行。

### 3.3 `czsc/signals/` 与 `czsc/traders/` 极薄化

**信号子包**：

```python
# czsc/signals/__init__.py
from czsc._native.signals import bar, cxt, tas, vol, pressure, obv, cvolp  # 等 ...
__all__ = ["bar", "cxt", "tas", "vol", "pressure", "obv", "cvolp", ...]

# czsc/signals/bar.py
from czsc._native.signals.bar import *  # noqa: F401,F403
```

不再有 Python 实现的信号函数（rs-czsc 已经实现了 30+ 个）。

**交易子包**：

```python
# czsc/traders/__init__.py
from czsc._native import (
    CzscTrader, CzscSignals, WeightBacktest,
    generate_czsc_signals, get_unique_signals,
)
from czsc.traders.dummy import DummyBacktest          # 保留 Python 端
from czsc.traders.sig_parse import SignalsParser      # 保留 Python 端
```

**删除** `czsc/traders/` 中：`base.py`, `cwc.py`, `rwc.py`, `optimize.py`, `weight_backtest.py`, `performance.py`（Rust 已实现等价或更优实现）。

### 3.4 `czsc.envs` 精简

退役 `CZSC_USE_PYTHON`（不再有 Python fallback）。保留：

```python
czsc_min_bi_len: int = 6      # 最小笔长度
czsc_max_bi_num: int = 50     # 最大笔数量
czsc_verbose: bool = False    # 详细日志
```

通过 `czsc._native.set_envs(min_bi_len=..., max_bi_num=..., verbose=...)` 一次性传给 Rust 端。`czsc/envs.py` 仅是这三个值的 Python 端配置入口。

### 3.5 `czsc/core.py` 极简化

```python
# czsc/core.py
"""向后兼容入口：所有名称从 czsc._native 直接导入。"""
from czsc._native import *  # noqa: F401,F403
```

整个文件从 134 行降到 < 5 行。原有的 `if os.getenv("CZSC_USE_PYTHON")` 双路由逻辑彻底删除。

---

## 4. 测试体系

### 4.1 整体原则

- **Rust 测试**和 **Python 测试**完全分离，分别遵守各自语言的最佳实践
- Rust 测试不调用 Python；Python 测试通过 PyO3 绑定使用 Rust 实现
- 共用一份"测试数据语义"（K 线生成器），但 Rust 端用 polars / Vec，Python 端用 `czsc.mock`

### 4.2 Rust 端测试

**目录布局**：

```
crates/<crate-name>/
├── src/
│   └── ...
│   └── mod.rs          # #[cfg(test)] 单元测试
└── tests/              # 集成测试（每个文件一个 binary）
    ├── analyze_tests.rs
    └── benchmarks.rs   # criterion benchmark
```

**规则**：

| 类别 | 位置 | 工具 | 触发 |
|---|---|---|---|
| 单元测试 | `src/**/*.rs` 内 `#[cfg(test)] mod tests` | 标准 `cargo test` | `cargo test -p <crate>` |
| 集成测试 | `crates/<crate>/tests/` | 标准 `cargo test` | `cargo test --test <name>` |
| Benchmark | `crates/<crate>/tests/benchmarks.rs` | `criterion` | `cargo bench` |
| 跨 crate 端到端 | `crates/czsc-trader/tests/` | 标准 `cargo test` | `cargo test --workspace` |

**质量门槛**：

- 公开 API（`pub fn` / `pub struct` 的 `impl`）覆盖率目标 ≥ 80%
- 所有 `#[pyclass]` / `#[pyfunction]` 必须在 Rust 端有对应单元测试（验证算法正确性，与 PyO3 解耦）
- CI 中执行 `cargo clippy --all-targets -- -D warnings`、`cargo fmt --check`

### 4.3 Python 端测试

**目录布局**：

```
test/
├── conftest.py                # 全局 fixtures（注入 czsc.mock 数据）
├── unit/                      # 单元测试
│   ├── test_core.py           # CZSC/FX/BI/ZS 公共行为
│   ├── test_bar_generator.py  # BarGenerator
│   ├── test_signals.py        # czsc.signals.* 调用是否符合 Python 接口契约
│   ├── test_ta.py             # czsc.ta.* 算子结果对比 Python TA-Lib（容差校验）
│   └── test_envs.py           # 环境变量传递
├── integration/               # 集成测试
│   ├── test_trader.py         # CzscTrader / CzscSignals 端到端
│   ├── test_weight_backtest.py
│   ├── test_strategies.py     # CzscStrategyBase / CzscJsonStrategy
│   └── test_connectors.py     # connectors 接口（不依赖真实数据源）
├── compat/                    # 公共 API 快照
│   ├── test_public_api.py     # 导入 czsc.* 应包含的所有名称
│   └── snapshots/             # 期望的 dir(czsc) 输出
└── smoke/                     # 安装后冒烟测试
    └── test_install.py        # pip install czsc 后能 import 并跑通主流程
```

**关键约束（沿用 czsc CLAUDE.md 规范）**：

- 所有测试数据**统一通过** `czsc.mock` 模块获取，禁止硬编码模拟数据
- 测试文件命名 `test_*.py`，使用 `pytest` 框架
- 测试 fixtures 通过 `conftest.py` 共享
- 模拟数据使用 `generate_symbol_kines` 生成，支持多品种、多频率、可重现的随机数据

**Mock 策略**：

- 内部 Rust 调用**不做 mock**（直接用真实实现，保证算法行为正确性）
- 外部资源（HTTP API、数据库、文件系统）使用 `pytest-mock` / `responses` 隔离
- connectors 测试：每个 connector 至少有一个不依赖真实数据源的契约测试

**质量门槛**：

- 公共 API 测试覆盖率 ≥ 70%（`pytest --cov=czsc --cov-report=xml`）
- 所有 `czsc.__all__` 中的名称必须在 `test/compat/test_public_api.py` 中有快照
- 安装冒烟测试 `test/smoke/` 在 CI 的 wheel 包发布前必跑

### 4.4 测试运行命令（与 CLAUDE.md 同步更新）

```bash
# Rust 端
cargo test --workspace                # 所有 Rust 测试
cargo test -p czsc-core               # 单个 crate
cargo bench                           # benchmark

# Python 端
uv run pytest                         # 全部 Python 测试
uv run pytest test/unit/ -v           # 单元测试
uv run pytest test/compat/ -v         # API 兼容快照
uv run pytest --cov=czsc              # 覆盖率
uv run maturin develop --release      # 本地构建 Rust 扩展并安装到当前环境
```

---

## 5. 迁移路径与步骤

按 8 个 Phase 推进，每个 Phase 是一个可独立 commit / PR 的工作单元。

### Phase 0 — 准备（0.5 天）

- 创建迁移分支 `refactor/rust-czsc-migration`
- 在 `docs/MIGRATION_NOTES.md` 记录 rs-czsc 基线 commit hash
- 在 CI 中暂时关闭"必须通过测试"门槛（避免迁移过程中持续红状态）
- 备份当前 czsc/ 全部 Python 模块到 `_legacy/` 临时目录（不入版本库，便于对比）

### Phase 1 — 搭建 Rust workspace 骨架（1 天）

- 在 czsc 仓库根目录新增 `Cargo.toml`、`rust-toolchain.toml`、`.cargo/config.toml`
- 创建空的 `crates/{czsc-core,czsc-signals,czsc-trader,czsc-utils,czsc-ta,czsc-signal-macros,error-macros,error-support,czsc-python}/` 目录
- 每个 crate 一个空 `Cargo.toml` + `src/lib.rs`，先验证 `cargo build --workspace` 能通过
- 验收：`cargo build --workspace` 成功

### Phase 2 — 复制 Rust 源码（1 天）

按依赖顺序从 rs-czsc 复制 crate 内容（不含 PyO3 binding）：

1. `error-macros` → `error-support`
2. `czsc-utils`
3. `czsc-core`、`czsc-ta`、`czsc-signal-macros`
4. `czsc-signals`
5. `czsc-trader`

操作约束：
- 仅复制 `src/`、`tests/`、`Cargo.toml`、`README.md`（如有）
- `Cargo.toml` 中 `version.workspace = true` 等继承配置保持不变
- **不**复制 `python/` 子目录（rs-czsc 中 PyO3 binding 散落各业务 crate，本次重组到 `czsc-python` 单独 crate）
- 验收：`cargo test --workspace` 通过（仅 Rust 测试）

### Phase 3 — 实现 czsc-python binding 层（2 天）

- 在每个业务 crate 中新增 `src/python/mod.rs`，把原来散落各 crate 的 `#[pyclass]` / `#[pyfunction]` 集中到这里，并提供 `pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()>` 入口
- 把 `check_bi / check_fx / check_fxs / remove_include` 提为 `pub` 并补 `#[pyfunction]`
- 在 `czsc-utils` 中新增 `is_trading_time` Rust 实现 + `#[pyfunction]`
- 在 `crates/czsc-python/src/lib.rs` 中聚合所有 `register()` 调用
- 配置 `pyproject.toml`：`build-system = maturin`，`tool.maturin.module-name = "czsc._native"`
- 验收：`maturin develop` 后 Python 端 `from czsc._native import CZSC` 可成功

### Phase 4 — Python 包重构（2 天）

- 重写 `czsc/__init__.py`（按 §3.1 表格）
- 极简 `czsc/core.py`、`czsc/envs.py`
- 极薄化 `czsc/signals/`、`czsc/traders/`
- 新增 `czsc/ta/__init__.py`（re-export `czsc._native.ta`）
- 验收：`python -c "import czsc; czsc.CZSC"` 等所有顶层 API 可用

### Phase 5 — Python 删减（1 天）

- 删除 `czsc/py/`、`czsc/eda.py`、`czsc/aphorism.py`、`czsc/features/`、`czsc/fsa/`
- 删除 `czsc/utils/` 中按 §3.2 标记为"删除"的文件
- 删除 `czsc/traders/` 中除 `dummy.py` / `sig_parse.py` / `__init__.py` 之外的所有文件
- 删除 `czsc/signals/` 中所有 Python 实现的信号文件（仅留 re-export）
- 验收：`python -m compileall czsc/` 通过；`python -c "import czsc"` 不报 import 错误

### Phase 6 — 测试体系重构（2 天）

- 按 §4.3 重组 `test/` 目录
- 删除已无对应实现的测试（如 `test_eda.py`、`test_features.py`）
- 重写 `conftest.py`，注入 `czsc.mock` fixtures
- 新增 `test/compat/test_public_api.py` 锁定公共 API
- 新增 `test/smoke/` 冒烟测试
- 验收：`pytest test/unit test/integration` 全绿

### Phase 7 — examples 与文档同步（1 天）

- 调整 `examples/` 中的 import 路径（移除已删除的模块引用）
- 更新 `CLAUDE.md`：构建命令改为 `maturin develop`、测试命令同步更新
- 更新 `README.md`：标注新架构、安装方式
- 撰写 `docs/MIGRATION_NOTES.md`：从旧版 czsc 升级的破坏性变更清单
- 验收：所有保留的 examples 可在新环境中跑通

### Phase 8 — CI / 发布验证（1 天）

- GitHub Actions 配置三阶段：
  1. Rust：`cargo fmt --check` + `cargo clippy -D warnings` + `cargo test --workspace`
  2. Python：`maturin build --release` + `pytest`
  3. Wheel 构建：`maturin build` 多平台（linux/macos/windows）+ smoke test
- 在测试 PyPI（test.pypi.org）发布 `czsc-1.0.0rc1` 验证 pip 安装
- 验收：测试 PyPI 上 `pip install czsc` 后 smoke test 全过

**总工期估算：10.5 天**（不含评审和迭代）。

---

## 6. 验收标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | `from czsc import CZSC, Signal, Event, Position, Direction, Freq, format_standard_kline` 全部成功 | `test/compat/test_public_api.py` |
| 2 | 用户代码中**不需要** `import rs_czsc` | grep `examples/` 与文档无 `rs_czsc` 引用 |
| 3 | `cargo test --workspace` 全过 | CI |
| 4 | `pytest` 全过且覆盖率 ≥ 70% | CI + coverage report |
| 5 | `maturin build --release` 可在 linux/macos/windows 三平台产出 wheel | CI matrix |
| 6 | 删减后 czsc Python 代码量从 ~44K 行降至 ~8K 行 | `find czsc -name '*.py' \| xargs wc -l` |
| 7 | 安装 wheel 后 `python -c "import czsc; czsc.CZSC"` 可用，无需用户手动安装 rs-czsc | smoke test |
| 8 | examples/ 中保留的全部示例可跑通 | 手动验证 + CI 选择性执行 |
| 9 | 不再有 `CZSC_USE_PYTHON` 环境变量分支 | `grep -r CZSC_USE_PYTHON czsc/` 应无结果 |
| 10 | rs-czsc 代码同步追溯：`docs/MIGRATION_NOTES.md` 记录基线 commit + 后续 cherry-pick 列表 | 文档存在性检查 |

---

## 7. 风险与缓解

| 风险 | 等级 | 缓解策略 |
|---|---|---|
| **`pub(crate)` → `pub` 提升后 rs-czsc 上游同步困难** | 中 | 在 `MIGRATION_NOTES.md` 标注哪些函数已"czsc-only 公开化"；cherry-pick 时手动适配 |
| **`is_trading_time` 在 Rust 端是新增实现，可能与 Python 旧逻辑行为不一致** | 中 | 增加专门的对比测试 `test_unit/test_trading_time.py`，跑历史数据集验证 |
| **`czsc-ta` 的 `mixed/` 子模块依赖 NumPy 0.25.0 + abi3-py310，少数 Linux 环境下 wheel 构建失败** | 低 | CI 多平台 matrix 提早暴露；保留 `manylinux_2_28` build profile |
| **公共 API 移除后下游用户代码报错（`from czsc import xxx` 失败）** | 高 | `test/compat/` 锁定 `__all__`；`docs/MIGRATION_NOTES.md` 列出所有删除的名称 + 替代方案；major 版本号升至 `1.0.0` 表明破坏性变更 |
| **svc / sensors 隐式依赖被删除的模块（如 eda.py / features/）** | 中 | Phase 4 完成后立即跑 `python -c "import czsc.svc; import czsc.sensors"` 检查；如有断链，按需补 thin re-import 或迁移到保留模块 |
| **rs-czsc 自身仍在演进（version 0.1.27），迁移基线很快过时** | 中 | 在 Phase 0 锁定一个明确 commit；建立"季度同步"机制 cherry-pick 上游 fix |
| **构建工具切换（hatchling → maturin）破坏现有发布流程** | 中 | Phase 8 在 test.pypi.org 充分验证再切正式 PyPI；保留旧 hatchling 配置在 git 历史中可回滚 |
| **测试体系重构丢失对原有边界场景的覆盖** | 中 | 删除测试文件前先 review 内含的 corner case，把仍有效的断言迁移到新结构 |

---

## 8. 附录 A — Rust crate ↔ Python 命名空间映射

| Rust 对象（来源） | Python 暴露路径 |
|---|---|
| `czsc_core::CZSC` | `czsc.CZSC` |
| `czsc_core::objects::FX` | `czsc.FX` |
| `czsc_core::objects::BI` | `czsc.BI` |
| `czsc_core::objects::ZS` | `czsc.ZS` |
| `czsc_core::objects::RawBar` | `czsc.RawBar` |
| `czsc_core::objects::NewBar` | `czsc.NewBar` |
| `czsc_core::objects::Freq` | `czsc.Freq` |
| `czsc_core::objects::Mark` | `czsc.Mark` |
| `czsc_core::objects::Direction` | `czsc.Direction` |
| `czsc_core::objects::Operate` | `czsc.Operate` |
| `czsc_core::objects::Signal` | `czsc.Signal` |
| `czsc_core::objects::Event` | `czsc.Event` |
| `czsc_core::objects::Position` | `czsc.Position` |
| `czsc_core::analyze::utils::{check_bi,check_fx,check_fxs,remove_include}` | `czsc.{check_bi,check_fx,check_fxs,remove_include}` |
| `czsc_utils::BarGenerator` | `czsc.BarGenerator` |
| `czsc_utils::freq_data::freq_end_time` | `czsc.freq_end_time` |
| `czsc_utils::is_trading_time`（新增） | `czsc.is_trading_time` |
| `czsc_ta::pure::*` | `czsc.ta.*`（也在 `czsc.*` 顶层重复暴露） |
| `czsc_ta::mixed::*` | `czsc.ta.*` |
| `czsc_signals::bar::*` | `czsc.signals.bar.*` |
| `czsc_signals::cxt::*` | `czsc.signals.cxt.*` |
| `czsc_signals::tas::*` | `czsc.signals.tas.*` |
| `czsc_signals::vol::*` | `czsc.signals.vol.*` |
| `czsc_signals::pressure::*` | `czsc.signals.pressure.*` |
| `czsc_signals::obv::*` | `czsc.signals.obv.*` |
| `czsc_signals::cvolp::*` | `czsc.signals.cvolp.*` |
| `czsc_trader::CzscTrader` | `czsc.CzscTrader`、`czsc.traders.CzscTrader` |
| `czsc_trader::CzscSignals` | `czsc.CzscSignals`、`czsc.traders.CzscSignals` |
| `czsc_trader::WeightBacktest` | `czsc.WeightBacktest`、`czsc.traders.WeightBacktest` |
| `czsc_trader::generate_czsc_signals` | `czsc.generate_czsc_signals` |
| `czsc_trader::get_unique_signals` | `czsc.get_unique_signals` |
| `czsc_trader::daily_performance` | `czsc.daily_performance` |
| `czsc_trader::top_drawdowns` | `czsc.top_drawdowns` |

---

## 9. 附录 B — 删除/保留/精简清单

### 完整保留

- `czsc/connectors/`（5 文件，1177 行）
- `czsc/sensors/`（3 文件，301 行）
- `czsc/svc/`（11 文件，4375 行）
- `czsc/mock.py`（537 行）
- `czsc/strategies.py`（410 行）

### 大幅精简

- `czsc/utils/` 从 ~10.7K 行降到 ~2.5K 行（保留：cache, io, log, ta, calendar, sig, kline_quality, plot_backtest, plotly_plot, data_client, trade*；删除其它）
- `czsc/__init__.py` 从 331 行降到 ~150 行（删除延迟加载机制）
- `czsc/core.py` 从 134 行降到 < 5 行
- `czsc/envs.py` 从 50 行降到 ~20 行（移除 `CZSC_USE_PYTHON`）

### 极薄化

- `czsc/signals/` 从 12 文件 / 15K 行降到 ~12 文件 / ~200 行（仅 re-export）
- `czsc/traders/` 从 9 文件 / 3.5K 行降到 ~3 文件 / ~150 行（保留 dummy.py / sig_parse.py + re-export）

### 完全删除

- `czsc/py/`（6 文件，2148 行 — Rust 已实现）
- `czsc/eda.py`（1213 行）
- `czsc/aphorism.py`（853 行）
- `czsc/features/`（9 文件，777 行）
- `czsc/fsa/`（8 文件，2078 行）
- `czsc/utils/` 中：bar_generator, bi_info, analysis/, echarts_*, pdf_report, html_report_builder, word_writer, features, oss, st_components, corr, signal_analyzer

### 量化总结

| 指标 | 迁移前 | 迁移后 |
|---|---|---|
| Python 文件数 | 89 | ~35 |
| Python 代码行数 | ~44K | ~8K |
| Rust crate 数 | 0 | 9 |
| 构建工具 | hatchling | maturin |
| 外部 PyPI 依赖 `rs-czsc` | 是 | 否（自带 Rust） |
| `CZSC_USE_PYTHON` 双路由 | 是 | 否 |
| 公共 API 数量 | ~80 | ~80（保持兼容） |
