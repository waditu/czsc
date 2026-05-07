# Rust 实现的 czsc 核心对象迁移 — 设计方案

- 作者：Claude Code (协作设计)
- 日期：2026-05-03（v0.3 — 全局一致性修订 + 迁移流程改 TDD）
- 状态：v0.3 草案（全局一致性修订 + 迁移路径改写为 superpowers TDD 模式，详见 §10）
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
|-|-|-|
| 1 | czsc 内置 Rust 源码（仓库内带 Rust workspace），rs-czsc 仍作为独立项目存在 | 已确认 |
| 2 | 必迁 Rust crate：`czsc-core` + `czsc-signals` + `czsc-trader` + `czsc-utils` + `czsc-ta`（+ 配套 proc-macro / error-support） | 已确认 |
| 3 | Python 端**保留**：`connectors / envs / mock(薄层) / svc / sensors / strategies(临时) / utils(精简)`（`core.py` 不再保留，公共名称由 `czsc/__init__.py` 直接 re-export `czsc._native`） | 已确认 |
| 4 | Python 端**删除**：`py` / `features`（`eda.py` / `aphorism.py` / `fsa/` 暂保留） | 已确认 |
| 5 | 所有面向用户的 API 都通过 `czsc.xxx` 暴露，禁止用户感知 `rs_czsc` 或 `czsc._native` | 已确认 |
| 6 | 构建方式：`maturin + Rust workspace`，扩展模块名 `czsc._native` | 已确认 |
| 7 | rs-czsc **后续不再维护**：czsc 一次性 fork 后独立演进，`MIGRATION_NOTES.md` 仅记录基线 commit；不再做季度同步 / cherry-pick | 已确认 |

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
│   ├── czsc-trader/                  # 回测/权重/优化/CzscTrader/StrategyBase（待迁）
│   ├── czsc-utils/                   # BarGenerator/日历/错误/性能详情
│   ├── czsc-ta/                      # TA 算子（仅保留被 czsc-signals/czsc-trader 实际调用的）
│   ├── czsc-signal-macros/           # proc-macro：#[signal_module] 注册
│   ├── error-macros/                 # proc-macro：错误类型生成
│   ├── error-support/                # 错误基础库
│   └── czsc-python/                  # PyO3 binding 总入口 → 产出 czsc._native（所有暴露对象支持 pickle）
│
├── czsc/                             # Python 包（精简后约 12K 行）
│   ├── __init__.py                   # 重写，统一从 czsc.xxx 暴露
│   ├── _native.pyi                   # type stub（pyo3-stub-gen 生成）
│   ├── envs.py                       # 仅保留 czsc_min_bi_len / czsc_max_bi_num / czsc_verbose
│   ├── mock.py                       # 薄壳：转发 wbt 的 mock 函数（generate_symbol_kines）
│   ├── strategies.py                 # 临时保留：CzscStrategyBase / CzscJsonStrategy（应迁 Rust，迁移完成后删除）
│   ├── aphorism.py                   # 保留
│   ├── eda.py                        # 保留（暂留，后续重构）
│   ├── fsa/                          # 保留
│   ├── connectors/                   # 完整保留（5 个连接器：tushare/tqsdk/ccxt/research/cooperation）
│   ├── sensors/                      # 完整保留（CTAResearch + 工具）
│   ├── svc/                          # 完整保留（Streamlit 可视化组件）
│   ├── signals/                      # 极薄，仅 re-export Rust 信号到 czsc.signals.{bar,cxt,...}
│   ├── traders/                      # 极薄，仅 re-export Rust 对象 + 保留 sig_parse（待评估 Rust 是否已实现）
│   ├── ta/                           # 极薄，re-export Rust ta 算子（czsc.utils.ta 不再保留）
│   └── utils/                        # 大幅精简至 ~3K 行（详见 §3.2）
│
├── test/                             # Python pytest 套件
│   ├── conftest.py                   # 注入 wbt mock fixtures
│   ├── unit/                         # 单元测试（核心对象、信号、TA、pickle 可序列化）
│   ├── integration/                  # 集成测试（trader、回测对接 wbt、connectors）
│   └── compat/                       # API 兼容快照（锁定 czsc.* 公共名称）
│
├── docs/
│   ├── superpowers/specs/            # 本设计文档存放地
│   ├── MIGRATION_NOTES.md            # 仅记录从 rs-czsc 哪个 commit 复制而来（无需后续同步）
│   └── ...
│
└── examples/                         # 保留示例（同步调整 import）
```

**删除**：`czsc/py/`、`czsc/features/`，以及 `czsc/utils/` 中所有可视化/报告生成模块（详见 §3.2）。  
**暂保留待评估/重构**：`czsc/eda.py`（后续重构）、`czsc/strategies.py`（应迁 Rust）、`czsc/traders/sig_parse.py`（待评估 Rust 是否已等价实现）。  
**保留**：`czsc/aphorism.py`、`czsc/fsa/`、`czsc/utils/oss.py`。

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
   │        │          │           │
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
- 业务调用：`czsc-trader` / `czsc-signals` 中对 czsc-ta 的引用保持原样；**未被调用的 ta 算子（如部分仅在 rs-czsc 中孤立保留的指标）随迁移裁剪掉，不进入 czsc 仓库**，控制 Rust crate 体积与编译时长
- PyO3 暴露：`czsc-ta` 启用 `rust-numpy` feature，通过 `czsc-python` 注册为 `czsc._native.ta` 子模块
- Python 端唯一入口：

  - `czsc.ta.*` ← Rust 实现（高性能、向量化、NumPy 互操作）；**不再保留 czsc.utils.ta 的 Python TA-Lib wrapper**（由 Rust 端统一提供）

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
- **pickle 序列化（强制要求）**：所有通过 PyO3 暴露给 Python 的对象（`CZSC`/`BarGenerator`/`Position`/`CzscTrader`/`CzscSignals` 等），**必须实现 `__getstate__` / `__setstate__`**，使其可以被 `pickle.dumps`/`pickle.loads`，并在多进程（Streamlit/Joblib/Dask）和断点续跑场景下保持一致。Rust 侧建议通过 `serde` 序列化为 bincode/JSON，再桥接到 PyO3 的 `__reduce__`。
- **验收**：`test/unit/test_pickle.py` 对每个公开 PyO3 类做 `roundtrip` 测试，禁止新增不可 pickle 的对象

### 2.5 关键调整：Rust 端可见性提升

在 rs-czsc 中以下 4 个函数为 `pub(crate)`，迁移到 czsc 后需提升为 `pub` 并加 PyO3 binding：

| 函数 | rs-czsc 位置 | 当前可见性 | 调整后 |
|-|-|-|-|
| `remove_include` | `czsc-core/src/analyze/utils.rs:32` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_fxs` | `czsc-core/src/analyze/utils.rs:119` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_fx` | `czsc-core/src/analyze/utils.rs:158` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `check_bi` | `czsc-core/src/analyze/utils.rs:198` | `pub(crate)` | `pub` + `#[pyfunction]` |
| `is_trading_time` | **rs-czsc 中尚未实现** | — | 在 `czsc-utils` 中**新增** Rust 实现 + `#[pyfunction]` |

`freq_end_time` 已在 `czsc-utils/src/freq_data.rs:245` 是 `pub`，仅需补 PyO3 暴露。

### 2.6 与 rs-czsc 的同步策略

- **不用** git submodule / subtree。**复制即 fork，rs-czsc 后续不再维护**，czsc 独立演进。
- 维护 `docs/MIGRATION_NOTES.md` 仅记录基线 commit hash + 迁移日期，作为历史溯源；不再做季度同步。
- czsc 内部对原 rs-czsc 模块所做的改动（如 `pub(crate)` → `pub`、新增/裁剪算子）一律按本仓库的常规 PR 流程合入，无需在 PR 描述中标注 sync 来源。
- czsc-only 的能力（如 `is_trading_time`、被裁剪的 ta 算子清单）在 `MIGRATION_NOTES.md` 的"czsc-only 改动"小节集中列出。

---

## 3. Python 包结构（精简后）

### 3.1 `czsc/__init__.py` 公共 API 表

| 命名空间 | 来源 | 暴露名 |
|-|-|-|
| **顶层核心对象** | `czsc._native` | `CZSC, FX, BI, ZS, RawBar, NewBar, Freq, Mark, Direction, Operate, Signal, Event, Position, BarGenerator, format_standard_kline, freq_end_time, is_trading_time, check_bi, check_fx, check_fxs, remove_include` |
| **顶层交易对象** | `czsc._native` | `CzscTrader, CzscSignals, generate_czsc_signals, get_unique_signals`  <br/>`WeightBacktest`：**czsc 内部 `from wbt import WeightBacktest` 后照常暴露为 `czsc.WeightBacktest`**（czsc 不重新实现，但保持公共 API 名称兼容）；wbt 是硬依赖。 |
| **顶层 TA / 性能函数** | `czsc._native` | `ultimate_smoother, rolling_rank, ema, sma, boll_positions, ...`（25+ 函数完整列表见 stubs，来自 `czsc._native`）  <br/>`daily_performance` / `top_drawdowns`：**czsc 内部 `from wbt import ...` 后照常暴露为 `czsc.daily_performance` / `czsc.top_drawdowns`**，对外保持 czsc.\* 公共 API 兼容；wbt 作为 `pyproject.toml` 中的**硬依赖**（不是 optional） |
| `czsc.ta.*` | `czsc._native.ta` | Rust TA 算子的子模块入口，与顶层重复暴露兼容 |
| `czsc.signals.{bar,cxt,tas,vol,...}` | `czsc._native.signals.*` | 30+ 信号函数按类别分组 |
| `czsc.traders.*` | Python 薄层 + `czsc._native` | `CzscTrader, CzscSignals, generate_czsc_signals, get_unique_signals`；`WeightBacktest`（来自 wbt）；`SignalsParser`（待评估 Rust 是否已等价实现，迁移完成前作 Python 薄层）。**DummyBacktest 已删除**。 |
| `czsc.connectors.*` | 完整保留 | `tushare/tqsdk/ccxt/research/cooperation` |
| `czsc.sensors.*` | 完整保留 | `CTAResearch` 等 |
| `czsc.svc.*` | 完整保留 | Streamlit dashboard 组件 |
| `czsc.mock` | 薄层（转发 wbt） | `generate_symbol_kines, generate_klines_with_weights`（czsc 仍然暴露这两个名称，**实现内部 `from wbt.mock import ...`**，czsc.mock 退化为转发壳，不再维护重复实现） |
| `czsc.envs` | 精简 | `czsc_min_bi_len, czsc_max_bi_num, czsc_verbose` |
| `czsc.strategies` | 保留 | `CzscStrategyBase, CzscJsonStrategy`（**临时保留**，应迁 Rust 端 `czsc-trader`；迁移完成后 `czsc.strategies` 退化为 `from czsc._native import ...` 薄层或直接删除） |
| `czsc.utils.*` | 大幅精简（§3.2） | `cache, io, log, calendar, sig, plot_backtest, plotly_plot, kline_quality, data_client, trade_utils, oss`（不再保留 `ta`，由 `czsc.ta.*` Rust 实现替代） |

`__init__.py` 中**移除**`_LAZY_MODULES` / `_LAZY_ATTRS` 延迟加载机制。Rust 扩展模块加载快（< 50 ms），所有公共 API 在顶层直接 import。删除 `__getattr__` 动态加载逻辑。

### 3.2 `czsc/utils/` 精简清单

| 文件 | 决策 | 说明 |
|-|-|-|
| `cache.py` | **保留** | 磁盘缓存基础设施 |
| `io.py` | **保留** | dill / json 读写 |
| `log.py` | **保留** | loguru 配置 |
| `ta.py` | **删除** | 由 `czsc.ta.*`（Rust 实现，PyO3 暴露）替代，不再保留 Python TA-Lib wrapper |
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
| `oss.py` | **保留** | 阿里云对象存储工具，研究/数据落地场景仍有用 |
| `st_components.py` | **删除** | svc 已包含 Streamlit 组件 |
| `corr.py` | **删除** | 业务代码 |
| `signal_analyzer.py` | **删除** | 业务代码 |

精简后 `czsc/utils/` 从 \~10.7K 行降到 \~3K 行（含 oss.py 等保留模块）。

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
    CzscTrader, CzscSignals,
    generate_czsc_signals, get_unique_signals,
)
# WeightBacktest 由 wbt 包提供，czsc 内部 re-export 保持公共 API 兼容（wbt 是 pyproject.toml 中的硬依赖）
from wbt import WeightBacktest
# sig_parse: 待评估 Rust 是否已等价实现；评估完成后改为 from czsc._native import SignalsParser
from czsc.traders.sig_parse import SignalsParser
```

**删除**`czsc/traders/` 中：`base.py`、`cwc.py`、`rwc.py`、`optimize.py`、`weight_backtest.py`、`performance.py`、`dummy.py`（Rust 已实现等价或更优；WeightBacktest 全部改用 wbt 包）。仅 `sig_parse.py` 临时保留待评估。

### 3.4 `czsc.envs` 精简

退役 `CZSC_USE_PYTHON`（不再有 Python fallback）。保留：

```python
czsc_min_bi_len: int = 6      # 最小笔长度
czsc_max_bi_num: int = 50     # 最大笔数量
czsc_verbose: bool = False    # 详细日志
```

通过 `czsc._native.set_envs(min_bi_len=..., max_bi_num=..., verbose=...)` 一次性传给 Rust 端。`czsc/envs.py` 仅是这三个值的 Python 端配置入口。

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
|-|-|-|-|
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

- 所有测试数据**统一通过 `czsc.mock` 模块入口**获取；`czsc.mock` 是 [wbt](https://github.com/zengbin93/wbt) mock 函数的转发壳（czsc 不再维护重复实现），禁止在测试中硬编码模拟数据
- 测试文件命名 `test_*.py`，使用 `pytest` 框架
- 测试 fixtures 通过 `conftest.py` 共享

**Mock 策略**：

- 内部 Rust 调用**不做 mock**（直接用真实实现，保证算法行为正确性）
- 外部资源（HTTP API、数据库、文件系统）使用 `pytest-mock` / `responses` 隔离
- connectors 测试：每个 connector 至少有一个不依赖真实数据源的契约测试

**质量门槛**：

- 公共 API 测试覆盖率 ≥ 90%（`pytest --cov=czsc --cov-report=xml`）
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

<callout emoji="💡">
**本章迁移工作流**采用 [superpowers](https://github.com/anthropics/superpowers) 的 TDD 范式 + plan/execute 工作流。所有迁移步骤遵守 `superpowers:test-driven-development` 的 Iron Law：**没有失败测试就不写实现代码**。涉及的 superpowers skills：`brainstorming`（讨论 spec）→ `writing-plans`（产出 plan）→ `using-git-worktrees`（隔离工作区）→ `executing-plans` / `subagent-driven-development`（执行）→ `test-driven-development`（每个 task 内部的 RGR 循环）→ `finishing-a-development-branch`（合并发布）。
</callout>

### 5.0 总体方法

- **spec → plan → execute** 三段式：本设计文档存放在 `docs/superpowers/specs/2026-05-03-rust-czsc-migration.md`；据此产出 `docs/superpowers/plans/2026-05-03-rust-czsc-migration.md`（按 superpowers:writing-plans 规范写）；plan 中每个 task 都是一个完整的 RED→GREEN→REFACTOR→COMMIT 循环。
- **RED→GREEN→REFACTOR 循环**：每个 task ① 写最小失败测试 ② 跑测试看到失败（必须 fail，不能 error）③ 写最小实现 ④ 跑测试看到通过 ⑤ 必要时重构 ⑥ commit。任意步骤跳过都视为破坏 Iron Law，task 重做。
- **Bite-sized 任务粒度**：每个步骤 2–5 分钟；plan 中每个 task 列出确切文件路径、测试代码、运行命令和预期输出。禁止 placeholder（"TBD" / "implement later" / "类似 Task N"）。
- **Worktree 隔离**：所有迁移工作在 `git worktree add ../czsc-rust-migration refactor/rust-czsc-migration` 中进行；不污染 master 分支。
- **测试驱动顺序**：自上而下——先把验收标准（§6 全表）翻译成失败测试形成"验收基线"，再逐 crate 用 TDD 实现到 GREEN。**不允许**先复制 Rust 源码再补测试。

### 5.1 Phase 0 — Spec 评审 + Plan 产出（0.5 天）

**RED 前提（暂不写代码）**。本 phase 全部产出物为文档：

1. 用 `superpowers:brainstorming` 技能 review 本设计 spec，识别"没说清楚"的点（pickle 协议格式？wbt 版本约束？rs-czsc 基线 commit？）。
2. 用 `superpowers:using-git-worktrees` 创建 worktree `../czsc-rust-migration`，进入。
3. 在 worktree 中执行 `git rev-parse HEAD`（rs-czsc 子目录）锁定基线 commit，写入 `docs/MIGRATION_NOTES.md`。
4. 用 `superpowers:writing-plans` 技能产出 plan 文件 `docs/superpowers/plans/2026-05-03-rust-czsc-migration.md`，按本章 5.2–5.12 展开为 \~80 个 bite-sized task。
5. **验收**：plan 通过自审 checklist（无 TBD / 每 task 有 test code + run command + expected output / 每 task 都以 commit 结尾）。

### 5.2 Phase A — 写验收级失败测试（"测试基线"，1.5 天）

把 §6 验收表 + §3.1 公共 API 表 翻译成可执行测试，跑出全 RED。**这是 superpowers TDD 的关键差异点**：传统 plan 是"先做实现再补测试"，这里反过来。

| Task | RED 测试 | 断言内容 | 预期失败原因（v0.2 当前状态） |
|-|-|-|-|
| A1 | `test/compat/test_public_api.py` | 从 `czsc.__all__` 与 stub 中读出 80+ 公共名称，逐个 `getattr(czsc, name)` 不抛异常；快照存 `test/compat/snapshots/api_v1.json` | czsc 当前 import 路径与本设计 §3.1 不完全一致（DummyBacktest、czsc.utils.ta 等仍在） |
| A2 | `test/unit/test_pickle.py` | 对每个 PyO3 暴露类（CZSC/BarGenerator/Position/CzscTrader/CzscSignals）做 `pickle.loads(pickle.dumps(obj)) == obj` roundtrip | 当前 PyO3 类未实现 `__getstate__` / `__setstate__` |
| A3 | `test/unit/test_core_parity.py` | 固定 seed 的 `wbt.mock.generate_symbol_kines` 输入下，`czsc.CZSC(bars).fxs/bi_list/zs_list` 与 rs-czsc 基线快照逐一相等（容差 0） | czsc 仓库尚未内置 Rust 实现，缺少基线快照对照机制 |
| A4 | `test/unit/test_signals_parity.py` | 30+ 信号函数对 mock 数据逐一比对 rs-czsc 基线输出 | 同 A3 |
| A5 | `test/unit/test_ta_parity.py` | `czsc.ta.{ema,sma,rolling_rank,...}` 相对 Python TA-Lib 容差 ≤ 1e-6 | 当前未暴露 czsc.ta.\*（只有 czsc.utils.ta 的 Python wrapper） |
| A6 | `test/unit/test_trading_time.py` | `is_trading_time` 在 A 股/港股/数字货币 三类日历上的若干典型时间点结果正确 | 该函数 Rust 端尚未实现 |
| A7 | `test/integration/test_weight_backtest.py` | `czsc.WeightBacktest` 等于 `wbt.WeightBacktest`；同一份权重输入产出指定的统计结果 | 当前 czsc.WeightBacktest 来自 czsc.core 的 Python fallback / rs-czsc，非 wbt |
| A8 | `test/smoke/test_install.py` | 在干净 venv 中 `pip install ./dist/czsc-*.whl` 后 `python -c "import czsc; czsc.CZSC(...)"` 成功 | 尚未切到 maturin，wheel 不包含 Rust 扩展 |

- **验收**：`pytest test/ -v` 输出全部为 FAIL（不能是 ERROR / SKIP）；CI 上的 RED 状态被记录到 plan 文件作为 baseline。
- **禁止**在本 phase 写任何 Rust 实现或修改 czsc/\* 业务代码——只写测试。

### 5.3 Phase B — Rust workspace 骨架（GREEN 第一层，1 天）

1. **RED**：写 `tests/rust/test_workspace_layout.sh`（或 cargo metadata 检查），断言存在 `crates/{czsc-core, czsc-utils, czsc-ta, czsc-signals, czsc-trader, czsc-signal-macros, error-macros, error-support, czsc-python}` 9 个成员，且 `cargo build --workspace` 通过。
2. 跑测试看到失败（目录不存在）。
3. **GREEN**：创建 `Cargo.toml`（按 §2.1）、9 个空 crate（每个一个空 `lib.rs` + 最小 `Cargo.toml`）。
4. 跑测试看到通过。
5. Commit: `feat(rust): scaffold workspace with 9 empty crates`。

### 5.4 Phase C — czsc-utils 测试驱动迁移（1 天）

采用"复制即测试"模式：**不**整体复制 src/，而是按 rs-czsc 的测试逐个迁移，每个测试都走 RED → 复制对应 src 文件 → GREEN。

1. **子循环 1（freq_data 模块）**：① 把 rs-czsc 的 `czsc-utils/tests/test_freq_data.rs` 复制到 `crates/czsc-utils/tests/`。② `cargo test -p czsc-utils freq` 看到 RED（src 还空着）。③ 复制 `czsc-utils/src/freq_data.rs`。④ 跑测试通过。⑤ commit。
2. **子循环 2（BarGenerator 模块）**：同样模式。
3. **子循环 3（is_trading_time 新增能力）**：先写测试用例（A 股/港股/数字货币三组），看到 RED；写 Rust 实现；GREEN；commit。
4. **子循环 4（PyO3 binding）**：在 Python 端 `test/unit/test_bar_generator.py` 增加细粒度测试（独立于 A3 parity 测试），断言 `czsc._native.BarGenerator` 行为；用 `maturin develop` 让其失败；在 `czsc-utils/src/python/mod.rs` 加 `#[pymodule]` + 在 `czsc-python` 注册；GREEN；commit。

**本 phase 完成的判定**：`cargo test -p czsc-utils` 全过；Phase A 中 A6（is_trading_time）由 RED 转 GREEN。

### 5.5 Phase D — czsc-core 测试驱动迁移（2 天）

对照 rs-czsc 的 `czsc-core` 模块清单（FX / BI / ZS / CZSC / Direction / Mark / Operate / Signal / Event / Position 等），每个数据类型一个子循环：

1. 子循环命名规则：`test_<type>.rs`（Rust 单元）+ `test_<type>_py.py`（PyO3 binding 行为）。
2. 每个子循环：复制对应 rs-czsc 测试 → RED → 复制对应 src → GREEN → 加 PyO3 binding 测试 → RED → 写 binding → GREEN → 加 pickle roundtrip 断言 → RED → 写 `__getstate__/__setstate__` → GREEN → commit。
3. **关键 4 个 `pub(crate)` → `pub` 的可见性提升**（`check_bi/check_fx/check_fxs/remove_include`）作为独立子循环：先写 Python 测试 `czsc.check_bi(...)`，RED 因为 binding 未注册 → 提升可见性 + 加 PyO3 → GREEN。

**本 phase 完成的判定**：A3（core_parity）由 RED 转 GREEN；A2（pickle）对 czsc-core 涉及的所有类转 GREEN。

### 5.6 Phase E — czsc-ta + czsc-signal-macros（1.5 天）

1. 先按 `czsc-trader` / `czsc-signals` 中的 ta 调用链做**静态分析**，列出实际被引用的算子白名单（写入 plan 的"czsc-ta 裁剪清单"）。
2. 仅迁移白名单内的算子；每个算子一个 RED→GREEN 子循环。被裁剪的算子在 `MIGRATION_NOTES.md` 的"czsc-only 改动"小节列出。
3. czsc-signal-macros：迁移 `#[signal_module]` proc-macro，先写一个最小宏展开测试，RED → 复制 macro 实现 → GREEN。

**本 phase 完成的判定**：A5（ta_parity）转 GREEN，被裁剪算子有书面记录。

### 5.7 Phase F — czsc-signals 迁移（1.5 天）

1. 按子模块（`bar/cxt/tas/vol/pressure/obv/cvolp`）分别迁移；每个子模块一组 RED→GREEN 子循环。
2. 每个信号函数一个 Rust 单元测试 + 一个 Python parity 测试（验证签名兼容旧 Python 实现）。
3. 注册路径：`czsc._native.signals.bar.*` → 在 czsc/signals/bar.py 中 re-export。

**本 phase 完成的判定**：A4（signals_parity）转 GREEN。

### 5.8 Phase G — czsc-trader 迁移（含 strategies）（2 天）

1. 迁移 `CzscTrader` / `CzscSignals` / `generate_czsc_signals` / `get_unique_signals`（每个一个子循环）。
2. **strategies.py 迁移**：先在 Rust 端 `czsc-trader/src/strategies/` 增加 `StrategyBase` / `JsonStrategy` 实现；写 Python 测试 `test/integration/test_strategies.py` 断言 `czsc.CzscStrategyBase` 与原 Python 实现行为一致 → RED → 写 Rust 实现 → GREEN → 删 `czsc/strategies.py` → 验证 GREEN 不变。
3. **WeightBacktest** 不在本 crate 实现：保留 Phase A7 的 RED，等 Phase I 由 wbt 接管转 GREEN。

### 5.9 Phase H — czsc-python 聚合 + Python 包重构（1.5 天）

1. 在 `crates/czsc-python/src/lib.rs` 中聚合所有 `register()`（按 §2.4 模板）。
2. 配置 `pyproject.toml`：`build-system = maturin`、`module-name = "czsc._native"`、加入 `wbt` 硬依赖。
3. 重写 `czsc/__init__.py`：按 §3.1 表逐项 import。每加一项跑 A1（compat），看哪个名称由 RED 转 GREEN，逐步把 80+ 名称变绿。
4. 极薄化 `czsc/signals/` / `czsc/traders/`（按 §3.3）。
5. 新增 `czsc/ta/__init__.py` re-export `czsc._native.ta`。
6. **删除 `czsc/core.py`**（不再保留 Python 端核心入口）。

### 5.10 Phase I — wbt 集成（0.5 天）

1. `uv add wbt` 加入硬依赖。
2. 在 `czsc/__init__.py` / `czsc/traders/__init__.py` 中 `from wbt import WeightBacktest, daily_performance, top_drawdowns`，让 A7（WeightBacktest）转 GREEN。
3. 把 `czsc/mock.py` 改为转发 `wbt.mock.*` 的薄壳（v0.1: 537 行 → \~30 行）；A1 中 mock 相关名称转 GREEN。
4. commit: `feat: wire wbt as the canonical backtest/perf/mock provider`。

### 5.11 Phase J — Python 删减（0.5 天）

1. 按 §3.2 / §9 附录 B 的"完全删除"列表逐文件 `git rm`；每删一组跑 `pytest -q` 确认仍 GREEN。
2. 删除 `czsc/utils/ta.py`（A5 已经由 czsc.ta.\* 接管）。
3. 删除 `czsc/traders/{base,cwc,rwc,optimize,weight_backtest,performance,dummy}.py`。
4. 删除 `czsc/{py,features}/` 目录（保留 `aphorism.py` / `fsa/` / `eda.py`）。
5. **验收**：`find czsc -name '*.py' | xargs wc -l` 总行数落入 \~12K（§6 Q5）。

### 5.12 Phase K — CI / Trusted Publishing / finishing（1 天）

1. 写 GitHub Actions workflow：Rust（fmt/clippy/test）+ Python（maturin build + pytest）+ wheel matrix（linux/macos/windows）+ smoke。
2. 配置 PyPI / TestPyPI 的 **Trusted Publishing（OIDC）** binding（仓库 + workflow + environment 三元组）。
3. 发 RC 到 test.pypi.org，干净 venv 跑 A8（smoke），转 GREEN。
4. 用 `superpowers:finishing-a-development-branch` 完成合并、release notes、tag 1.0.0。

**总工期估算**：14 天（Phase 0–K，比 v0.1 的 10.5 天多约 30%，多出来的时间用于 Phase A 的"验收测试基线"——这是 TDD 范式相比"先实现后补测试"必然多出的成本，但换来的是从第 1 天起就有可量化的进度指标：每个 task 都能清晰回答"这个改动到底让多少 RED 转 GREEN"）。

### 5.13 进度可视化

plan 文件中每个 task 标注其会让哪几条 Phase A 测试由 RED 转 GREEN。CI 中加一个 `scripts/red_green_report.py`：在每次 commit 后输出 `红 X 项 / 绿 Y 项 / 总 N 项`，作为 PR 描述的进度行。

## 6. 验收标准

<table><colgroup><col/><col/><col/><col/></colgroup><thead><tr><th vertical-align="top">分类</th><th vertical-align="top">#</th><th vertical-align="top">验收标准</th><th vertical-align="top">验证方式</th></tr></thead><tbody><tr><td rowspan="6" vertical-align="top"><b>功能正确性</b></td><td vertical-align="top">F1</td><td vertical-align="top"><code>from czsc import CZSC, Signal, Event, Position, Direction, Freq, format_standard_kline</code> 等 80+ 公共名称全部成功导入</td><td vertical-align="top"><code>test/compat/test_public_api.py</code> 快照测试</td></tr><tr><td vertical-align="top">F2</td><td vertical-align="top">缠论核心算法（分型、笔、线段、中枢）在固定随机种子的 mock 数据上结果与 rs-czsc 基线一致（容差 0）</td><td vertical-align="top"><code>test/unit/test_core_parity.py</code></td></tr><tr><td vertical-align="top">F3</td><td vertical-align="top">30+ 信号函数在 mock 数据上的输出值与 rs-czsc 基线一致；签名兼容旧 Python 实现</td><td vertical-align="top"><code>test/unit/test_signals_parity.py</code></td></tr><tr><td vertical-align="top">F4</td><td vertical-align="top">TA 算子（ema/sma/rolling_rank/...）相对 Python TA-Lib 数值容差 ≤ 1e-6（除非有文档化的算法差异）</td><td vertical-align="top"><code>test/unit/test_ta_parity.py</code></td></tr><tr><td vertical-align="top">F5</td><td vertical-align="top"><code>WeightBacktest</code> 通过 <code>wbt</code> 包正常工作；czsc 端 example/sensors 接入 wbt 后结果与历史快照一致</td><td vertical-align="top">集成测试 + 历史结果回放</td></tr><tr><td vertical-align="top">F6</td><td vertical-align="top"><code>is_trading_time</code> 等 czsc-only 新增能力在 A 股 / 港股 / 数字货币 三类日历上行为正确</td><td vertical-align="top"><code>test/unit/test_trading_time.py</code></td></tr><tr><td rowspan="3" vertical-align="top"><b>性能</b></td><td vertical-align="top">P1</td><td vertical-align="top">对 10 万根 K 线做完整 CZSC 分析（分型/笔/中枢）≤ 200 ms（M2 Mac，单进程）</td><td vertical-align="top"><code>cargo bench -p czsc-core</code> + Python <code>pytest-benchmark</code></td></tr><tr><td vertical-align="top">P2</td><td vertical-align="top">30+ 信号函数批量执行单根 K 线 ≤ 50 µs P50；批量 1 万根 ≤ 80 ms</td><td vertical-align="top">benchmark CI 阈值</td></tr><tr><td vertical-align="top">P3</td><td vertical-align="top">czsc 包冷启动 import 时间 ≤ 300 ms（含 Rust 扩展加载）</td><td vertical-align="top"><code>python -X importtime -c "import czsc"</code> + CI 阈值</td></tr><tr><td rowspan="5" vertical-align="top"><b>质量</b></td><td vertical-align="top">Q1</td><td vertical-align="top"><code>cargo test --workspace</code> 全过；<code>cargo clippy -D warnings</code> 无 warning；<code>cargo fmt --check</code> 通过</td><td vertical-align="top">CI</td></tr><tr><td vertical-align="top">Q2</td><td vertical-align="top"><code>pytest</code> 全过且公共 API 覆盖率 ≥ 90%；整体行覆盖率 ≥ 70%</td><td vertical-align="top">CI + coverage report（codecov）</td></tr><tr><td vertical-align="top">Q3</td><td vertical-align="top">所有通过 PyO3 暴露的对象（CZSC/BarGenerator/Position/CzscTrader/CzscSignals/...）<b>支持 pickle</b>，可在 Streamlit / Joblib / multiprocessing 中安全传递</td><td vertical-align="top"><code>test/unit/test_pickle.py</code> roundtrip 测试覆盖每个类</td></tr><tr><td vertical-align="top">Q4</td><td vertical-align="top"><code>ruff check</code>（替代 flake8/isort）+ <code>basedpyright</code>（替代 mypy）双向通过；type stub <code>czsc/_native.pyi</code> 自动生成且无人工修改</td><td vertical-align="top">CI</td></tr><tr><td vertical-align="top">Q5</td><td vertical-align="top">删减后 czsc Python 代码量从 ~44K 行降至 ~12K 行（保留 aphorism/eda/fsa 后的目标值）</td><td vertical-align="top"><code>find czsc -name '*.py' | xargs wc -l</code></td></tr><tr><td rowspan="3" vertical-align="top"><b>兼容性</b></td><td vertical-align="top">C1</td><td vertical-align="top">用户代码<b>不需要</b><code>import rs_czsc</code>；<code>examples/</code> 与文档无 <code>rs_czsc</code> 引用</td><td vertical-align="top"><code>grep -r rs_czsc examples/ docs/</code> 应无结果</td></tr><tr><td vertical-align="top">C2</td><td vertical-align="top">不再有 <code>CZSC_USE_PYTHON</code> 环境变量分支</td><td vertical-align="top"><code>grep -r CZSC_USE_PYTHON czsc/</code> 应无结果</td></tr><tr><td vertical-align="top">C3</td><td vertical-align="top">下游用户主要 import 路径（<code>czsc.CZSC</code>、<code>czsc.signals.bar.*</code>、<code>czsc.traders.CzscTrader</code>、<code>czsc.utils.cache</code> 等）保持不破坏；<b>已移除的名称</b>在 <code>MIGRATION_NOTES.md</code> 中给出替代方案</td><td vertical-align="top">API 快照 + 文档检查</td></tr><tr><td rowspan="4" vertical-align="top"><b>发布</b></td><td vertical-align="top">R1</td><td vertical-align="top"><code>maturin build --release</code> 在 linux（manylinux_2_28）/ macos（universal2）/ windows 三平台产出 wheel</td><td vertical-align="top">CI matrix</td></tr><tr><td vertical-align="top">R2</td><td vertical-align="top">使用 <b>PyPI Trusted Publishing（OIDC）</b> 发布，不在 GitHub Actions 中存放任何 PyPI token / secrets</td><td vertical-align="top">CI workflow 配置 + PyPI 项目设置截图</td></tr><tr><td vertical-align="top">R3</td><td vertical-align="top">Test PyPI（test.pypi.org）发布 <code>czsc-1.0.0rc1</code>，在干净环境 <code>pip install --index-url https://test.pypi.org/simple/ czsc</code> 后 smoke test 全过</td><td vertical-align="top">CI smoke job</td></tr><tr><td vertical-align="top">R4</td><td vertical-align="top">正式 PyPI 发布后 <code>pip install czsc</code> 即可使用，<b>无需用户手动安装 rs-czsc</b>；<code>python -c "import czsc; czsc.CZSC"</code> 成功</td><td vertical-align="top">CI 安装后 smoke job</td></tr><tr><td rowspan="2" vertical-align="top"><b>追溯</b></td><td vertical-align="top">T1</td><td vertical-align="top"><code>docs/MIGRATION_NOTES.md</code> 记录从 rs-czsc 迁移的基线 commit hash、迁移日期、czsc-only 改动清单（含被裁剪的 ta 算子列表）</td><td vertical-align="top">文档存在性检查</td></tr><tr><td vertical-align="top">T2</td><td vertical-align="top">每个删除/重命名的旧公共 API 在 <code>MIGRATION_NOTES.md</code> 与 release notes 中列出替代方案；major 版本号升至 <code>1.0.0</code> 表明破坏性变更</td><td vertical-align="top">release notes review</td></tr></tbody></table>

---

## 7. 风险与缓解

| 风险 | 等级 | 缓解策略 |
|-|-|-|
| **czsc-only 公开化的函数**（`check_bi/check_fx/check_fxs/remove_include` 等 `pub(crate)`→`pub`）形成 czsc 仓库专属约定，与原 rs-czsc 不再回流互通 | 低 | 已在 `MIGRATION_NOTES.md` 的"czsc-only 改动"小节集中记录；rs-czsc 不再维护后无 cherry-pick 需求，长期看是**独立演进**而非"同步困难" |
| **`is_trading_time` 在 Rust 端是新增实现，可能与 Python 旧逻辑行为不一致** | 中 | 增加专门的对比测试 `test_unit/test_trading_time.py`，跑历史数据集验证 |
| **`czsc-ta` 的 `mixed/` 子模块依赖 NumPy 0.25.0 + abi3-py310，少数 Linux 环境下 wheel 构建失败** | 低 | CI 多平台 matrix 提早暴露；保留 `manylinux_2_28` build profile |
| **公共 API 移除后下游用户代码报错（`from czsc import xxx` 失败）** | 高 | `test/compat/` 锁定 `__all__`；`docs/MIGRATION_NOTES.md` 列出所有删除的名称 + 替代方案；major 版本号升至 `1.0.0` 表明破坏性变更 |
| **svc / sensors 隐式依赖被删除的模块（如 eda.py / features/）** | 中 | Phase 4 完成后立即跑 `python -c "import czsc.svc; import czsc.sensors"` 检查；如有断链，按需补 thin re-import 或迁移到保留模块 |
| **rs-czsc 已停止维护，未来上游 bugfix 无法回流** | 低 | czsc 一次性 fork 后独立演进；Phase 0 锁定基线 commit；后续按本仓库常规流程修 bug，不再 cherry-pick 上游 |
| **构建工具切换（hatchling → maturin）破坏现有发布流程** | 中 | 采用 **PyPI Trusted Publishing（OIDC）**，不在 GitHub 存任何 PyPI token；先在 test.pypi.org 验证 wheel + 安装路径再切正式 PyPI；旧 hatchling 配置保留在 git 历史可回滚 |
| **测试体系重构丢失对原有边界场景的覆盖** | 中 | 删除测试文件前先 review 内含的 corner case，把仍有效的断言迁移到新结构 |

---

## 8. 附录 A — Rust crate ↔ Python 命名空间映射

| Rust 对象（来源） | Python 暴露路径 |
|-|-|
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
| `wbt::WeightBacktest`（外部包） | `czsc.WeightBacktest`、`czsc.traders.WeightBacktest` |
| `czsc_trader::generate_czsc_signals` | `czsc.generate_czsc_signals` |
| `czsc_trader::get_unique_signals` | `czsc.get_unique_signals` |
| `wbt.daily_performance`（外部包） | `czsc.daily_performance` |
| `wbt.top_drawdowns`（外部包） | `czsc.top_drawdowns` |

---

<callout emoji="💡">
**来源标识说明**：表中"来源"列为 `wbt::*` 的项表示来自 [wbt](https://github.com/zengbin93/wbt) 外部包，czsc 通过 `from wbt import ...` 进行 re-export 以保持公共 API 兼容；其余 `czsc_*` 来源均为本仓库 Rust workspace 的内部 crate。
</callout>

## 9. 附录 B — 删除/保留/精简清单

### 完整保留

- `czsc/connectors/`（5 文件，1177 行）
- `czsc/sensors/`（3 文件，301 行）
- `czsc/svc/`（11 文件，4375 行）
- `czsc/mock.py`（v0.1: 537 行 → 迁移后 **\~30 行**，仅转发 wbt 的 mock 函数）
- `czsc/strategies.py`（v0.1: 410 行 — **临时保留待迁 Rust**，迁移到 `czsc-trader` 后删除）
- `czsc/aphorism.py`（853 行）
- `czsc/fsa/`（8 文件，2078 行）
- `czsc/eda.py`（1213 行 — 暂保留待重构）
- `czsc/utils/oss.py`（阿里云对象存储工具）

### 大幅精简

- `czsc/utils/` 从 \~10.7K 行降到 \~3K 行（保留：cache, io, log, calendar, sig, kline_quality, plot_backtest, plotly_plot, data_client, trade\*, oss；不再保留 ta，由 Rust 端 czsc.ta.\* 替代；删除其它）
- `czsc/__init__.py` 从 331 行降到 \~150 行（删除延迟加载机制）
- `czsc/envs.py` 从 50 行降到 \~20 行（移除 `CZSC_USE_PYTHON`）

### 极薄化

- `czsc/signals/` 从 12 文件 / 15K 行降到 \~12 文件 / \~200 行（仅 re-export）
- `czsc/traders/` 从 9 文件 / 3.5K 行降到 \~2 文件 / \~80 行（仅保留 sig_parse.py 待评估 + \_\_init\_\_.py re-export；DummyBacktest 已删除，WeightBacktest 改用 wbt 包）

### 完全删除

- `czsc/py/`（6 文件，2148 行 — Rust 已实现）
- `czsc/features/`（9 文件，777 行）
- `czsc/utils/` 中：bar_generator, bi_info, analysis/, echarts\_\*, pdf_report, html_report_builder, word_writer, features, st_components, corr, signal_analyzer, ta（不再保留 oss）

### 量化总结

| 指标 | 迁移前 | 迁移后 |
|-|-|-|
| Python 文件数 | 89 | \~50 |
| Python 代码行数 | \~44K | \~12K |
| Rust crate 数 | 0 | 9 |
| 构建工具 | hatchling | maturin |
| 外部 PyPI 依赖 `rs-czsc` | 是 | 否（自带 Rust） |
| `CZSC_USE_PYTHON` 双路由 | 是 | 否 |
| 公共 API 数量 | \~80 | \~80（保持兼容） |

## 10. 附录 C — 评审反馈处理记录（v0.1 → v0.2）

<callout emoji="💡">
本节记录针对 v0.1 草案 19 条评审意见的处理结果，仅作为评审跟进证据，不影响主体设计。
</callout>

| # | 评审意见摘要 | 本次调整 | 位置 |
|-|-|-|-|
| 1 | `core.py` 多余 / 3.5 节不需要 | 删除整节 3.5；仓库结构图与附录 B 移除 core.py | §1 / §3.5 / §9 |
| 2 | CzscStrategyBase / CzscJsonStrategy 应有 Rust 实现 | strategies.py 标记"临时保留，应迁 Rust"，公共 API 表加备注；后续在 czsc-trader 内补实现 | §1 / §3.1 |
| 3 | czsc-ta 中无人调用的指标可删 | §2.3 增加"未被调用的算子随迁移裁剪"说明，czsc-only 改动汇总到 MIGRATION_NOTES.md | §2.3 / §2.6 |
| 4 | 不再保留 czsc.utils.ta 兼容层 | §2.3 命名空间项调整；§3.2 表格 ta.py 改"删除"；§3.1 公共 API 表 utils 行去掉 ta；附录 B 删除清单加 ta | §2.3 / §3.1 / §3.2 / §9 |
| 5 | daily_performance / top_drawdowns 用 wbt 引入 | §3.1 顶层 TA / 性能函数行明确"czsc 内部 `from wbt import ...` 后保持 `czsc.daily_performance` / `czsc.top_drawdowns` 的公共 API 暴露"；§8 附录 A 的来源列改为 `wbt.*` | §3.1 |
| 6 / 7 | WeightBacktest 优先用 wbt | §3.1 / §3.3 / 验收 F5 / 附录 B 全部改为引用 wbt；过渡期可在 czsc 内做 re-export | §3.1 / §3.3 / §6 / §9 |
| 8 | oss.py 留在 utils | §3.2 表 oss.py 改"保留"；附录 B 完全删除清单移除 oss | §3.2 / §9 |
| 9 | DummyBacktest 删除 | §3.1 / §3.3 / 附录 B 全部移除 | §3.1 / §3.3 / §9 |
| 10 | SignalsParser 看 Rust 是否已等价实现 | 标记"待评估 Rust 是否已等价实现"，迁移完成前作 Python 薄层 | §3.1 / §3.3 |
| 12 | K 线 mock 用 wbt | §3.1 czsc.mock 行 / §4.3 测试条目 改为转发 wbt mock | §3.1 / §4.3 |
| 13 | 验收标准需更详尽 | §6 重写为五大类（功能/性能/质量/兼容/发布）+ 追溯，扩充至 \~24 条具体验收 | §6 |
| 14 | rs-czsc 后续不再维护 | §0.2 决策 7、§2.6、§7 风险表对应行改为"一次性 fork 后独立演进，无 cherry-pick" | §0.2 / §2.6 / §7 |
| 15 | PyPI 用最新推荐方式（OIDC，无 secrets） | Phase 8 改为 Trusted Publishing；§7 风险表对应行同步；§6 R2 验收 | §5 / §6 / §7 |
| 16 / 17 / 18 | aphorism / fsa / eda 保留 | §0.2 决策 4、§1 仓库结构图、§9 附录 B 调整为保留（eda 标注"待重构"） | §0.2 / §1 / §9 |
| 19 | Rust Python 对象支持 pickle | §2.4 增加强制 pickle 序列化要求；§6 验收 Q3 增加 roundtrip 测试条款 | §2.4 / §6 |

### 不在本次范围内的反馈

- 评论 #11 与 #1 重复（均针对 core.py），按 #1 一并处理。

### 仓库已落地的相关变更（参考）

本设计草案 v0.1（commit `534eed8`）提交后，主线已合入若干前置改动，可作为本设计的实施基底：

- `3f4cf2b` — 移除 Python 端 WeightBacktest fallback，独占使用 Rust 版（与本设计 §3.1 / §3.3 一致）
- `1325433` — 为所有 czsc 子模块新增 .pyi stub（符合 §2.4 type stub 自动生成方向）
- `79bdf5e` — 用 ruff + basedpyright 替代 black/flake8/isort/mypy（与本设计 §6 Q4 验收一致）
- `7dcadaa` / `a63965b` — 删除已不再使用的函数与文件，对接 §3.2 / §3.3 的精简方向

### v0.3 修订记录（一致性 + TDD）

**触发原因**：v0.2 提交后审阅发现两类问题——① 全局一致性：v0.2 的若干跨章节修改在细节上互相冲突；② 迁移流程是"先做实现后补测试"的传统模式，与项目使用的 superpowers 工作流不符。

#### 1. 一致性修订清单（13 项）

| # | 原冲突 | 修订 |
|-|-|-|
| C1 | §0.2 决策 3 仍含 `core` | 去除；明确"`core.py` 不再保留，名称由 `__init__.py` 直接 re-export" |
| C2 | §3.1 顶层 TA / 性能函数写"**不再暴露** daily_performance / top_drawdowns" | 更正为"czsc 内部 `from wbt import ...` 后照常暴露 `czsc.daily_performance` / `czsc.top_drawdowns`"，与 §8 附录 A 对齐 |
| C3 | §8 附录 A 把 `WeightBacktest` 标为 `czsc_trader::*` 来源 | 更正为 `wbt::WeightBacktest`（外部包）；`daily_performance` / `top_drawdowns` 同步改 `wbt.*`，并加 callout 说明"`wbt::*` = re-export 自外部包" |
| C4 | §3.1 czsc.mock 来源 cell 写"完整保留"但暴露名写"转发自 wbt" | 来源改为"薄层（转发 wbt）" |
| C5 | §3.3 traders \_\_init\_\_ 代码块用 `type: ignore[import-not-found]` 暗示 wbt 可选 | 去掉 type:ignore；明确 wbt 是 pyproject.toml 中的硬依赖 |
| C6 | §4.3 测试约束有两条互相重复的 mock 描述 | 合并为一条："统一通过 czsc.mock 入口（czsc.mock 是 wbt mock 的转发壳）" |
| C7 | 原 Phase 4 写"极简 czsc/core.py"，与 §3.5 已删冲突 | v0.3 整章重写为 TDD（见下），core.py 的处置改为"删除" |
| C8 | 原 Phase 5 删除清单含 eda / aphorism / fsa | 整章重写后纠正 |
| C9 | 原 Phase 5 traders 删除排除 dummy.py | 整章重写后纠正（dummy.py 也删） |
| C10 | §7 风险表"pub(crate)→pub 上游同步困难"含"cherry-pick 时手动适配"，与"rs-czsc 不再维护"冲突 | 风险等级降为低；缓解策略改为"czsc-only 公开化已记录于 MIGRATION_NOTES.md，rs-czsc 不再维护后无 cherry-pick 需求" |
| C11 | §9 完整保留 `czsc/mock.py（537 行）` 与"薄壳转发"决策矛盾 | 改为"v0.1: 537 行 → 迁移后 \~30 行（仅转发 wbt）" |
| C12 | §9 完整保留 `czsc/strategies.py（410 行）` 与"应迁 Rust 后删除"矛盾 | 改为"v0.1: 410 行 — 临时保留待迁 Rust，迁移完成后删除" |
| C13 | §10 评审 #5 调整描述写"不再 re-export"误读评论原意 | 更正为"czsc 内部 `from wbt import ...` 后保持公共 API 暴露" |

#### 2. 迁移流程改造（§5 整章重写）

v0.2 的 §5 是传统的 8 阶段"先实现后补测试"路径。v0.3 改写为 **superpowers TDD 模式**的 12 个 Phase（5.0–5.12）+ 进度可视化（5.13）：

- 引入 `spec → plan → execute` 三段式工作流；spec 存 `docs/superpowers/specs/`，plan 存 `docs/superpowers/plans/`。
- 遵守 `superpowers:test-driven-development` 的 Iron Law：**没有失败测试就不写实现代码**。每个 task 都是完整的 RED→GREEN→REFACTOR→COMMIT 循环。
- 引入 Phase A "测试基线"——**把 §6 验收标准翻译成可执行的失败测试**（compat / pickle / parity / smoke 共 8 类），第 1 天就跑出全 RED；之后每个 task 都能量化"让多少 RED 转 GREEN"。
- 每个 crate（utils / core / ta / signals / trader）按"复制即测试"模式逐个迁移，不允许整体复制 src/。
- 采用 `using-git-worktrees` 保证 master 分支隔离；最后用 `finishing-a-development-branch` 完成合并。
- 总工期从 v0.2 的 10.5 天调整为 14 天（多出来的 \~30% 用于 Phase A 验收测试基线，但换来全程可量化进度）。
