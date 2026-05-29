# Changelog

本项目的版本变更记录，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

> 1.0.X 之前的版本变更可在 git 历史与 [GitHub Releases](https://github.com/waditu/czsc/releases) 查看。

---

## [Unreleased]

### Notes

- **1.0.0-rc.8 在纯 Rust 下游不可用（PyPI 用户不受影响）**：发布后验证发现 cargo 用户 `cargo add czsc@=1.0.0-rc.8` 无法编译。两个根因：
  1. **SemVer prerelease 解析坑**：crates.io 上同时存在 `czsc-* 1.0.0` (stable) 与 `1.0.0-rc.*`，workspace 内部 dep 写 `version = "1.0.0-rc.8"`（不带 `=`）会被 cargo 解析到 1.0.0 stable（按 SemVer，stable > prerelease），导致 polars 0.42 与 0.52 双版本冲突。已对 8 个 czsc-* 1.0.0 stable 执行 `cargo yank` 缓解。
  2. **pyo3 / pyo3-stub-gen / numpy 是无条件硬依赖**（不在 feature gate 后），纯 Rust 用户也被强制拉 PyO3 工具链，撞 pyo3-stub-gen 0.22.x ↔ pyo3 0.28.3 的 `PyEncodingWarning` 兼容性 bug。
- **rc.9 计划**：(a) 把 4 个 czsc-* crate 的 pyo3 系列 dep 改 `optional = true` + 引入 `python` feature gate；(b) workspace dep 改 `version = "=1.0.0-rc.9"` 严格锁定 prerelease；(c) `docs/release_checklist.md` §7 已升级"cargo add 可解析" → "cargo check 真编"，下次再踩同样坑被立即拦下。
- **PyPI 1.0.0rc8 完全可用**，Python 用户无需做任何处理。

---

---

## [1.0.0-rc.8] — 2026-05-29

### Added

- **`czsc.resample_bars`**：把基础周期 K 线（`pandas.DataFrame` 或 `list[RawBar]`）聚合到目标周期。Rust 实现位于 `crates/czsc-utils/src/resample.rs`，通过 `czsc._native.resample_bars` 透传；Python 端 `czsc/_resample_bars.py` 仅做 DataFrame ↔ `list[RawBar]` 边界胶水。复用 `BarGenerator` 单桶聚合 + `infer_market_from_bars` 自动推断市场。
- **PyO3 enum 暴露 `.name` getter**（`Freq` / `Mark` / `Direction` / `Operate`）：与 Python 标准库 `enum.Enum.name` 对齐，返回 Rust variant 英文名（如 `Freq.F30.name == "F30"`、`Operate.HL.name == "HL"`），便于在序列化、日志、配置文件里使用语言无关的稳定标识符。`.value`（中文显示串）行为不变。Rust 实现位于 `crates/czsc-core/src/objects/{freq,mark,direction,operate}.rs`。
- **PyO3 enum 全部可哈希**（`Freq` / `Mark` / `Direction` —— `Operate` 此前已可哈希）：显式实现 `__hash__`，让实例可作为 `dict` / `set` 的 key。此前 PyO3 因 `__richcmp__` 存在而把 `__hash__` 强制设为 `None`，即使 Rust 端 `#[derive(Hash)]` 也透不到 Python。`Mark` / `Direction` derive 列表补 `Eq, Hash`；`Operate` derive 补 `Eq`。
- **`Mark` 补齐 `__new__` / `__reduce__` / `__deepcopy__`**：之前不能 pickle、不能从字符串构造（"G" / "顶分型"），是与 `Freq` / `Direction` 不对齐的 pre-existing gap，本次一并补完。`Mark("G") == Mark.G`、`pickle.loads(pickle.dumps(Mark.G)) == Mark.G` 现已可工作。

### Breaking changes

- **`RawBar` 构造拒绝 tz-aware datetime**（`crates/czsc-core/src/utils/common.rs::parse_python_datetime`）：历史上 tz-aware 入参走 `.timestamp()` 静默转 UTC（如 `09:31 Asia/Shanghai → 01:31 UTC`），下游 `freq_end_time` 桶定位全部错位。现改为 `PyValueError`，调用方需先 `df['dt'] = df['dt'].dt.tz_localize(None)`。同时 `parse_python_datetime` 的所有失败路径统一返回 `PyValueError`（历史混用 `PyException` + `PyValueError`），方便 Python 端 `except ValueError` 一次性捕获。
- **`BarGenerator.update_bar` / `init_freq_with_bars` 拒绝 NaN OHLCV**（`crates/czsc-utils/src/bar_generator.rs`）：历史上 `last.vol + bar.vol` 会让 NaN 沿桶传染（与 pandas `sum(skipna=True)` 不一致）。现改为显式 Err，沿 `signals.update_signals` / `trader.update` 等调用链 propagate，避免 trader 路径吞 Err 后用 stale 状态算出"幻象"信号。
- **`CzscTrader.update` / `on_bar` / `update_signals`、`CzscSignals.update_signals`**（`crates/czsc-python/src/trader/`）：PyO3 method 改返回 `PyResult<()>`，NaN / freq mismatch 等硬错 fail-loud 上抛 `ValueError`。Python 端调用方需准备好 `try/except` 或让异常冒泡。

### Fixed

- **`czsc/connectors/tq_connector.py::get_raw_bars`**：调用 `czsc.resample_bars` 时显式传 `base_freq=freq`，修复默认 `Freq.F1` 误标导致的 silent 时间漂移（review finding C5）。
- **`czsc.resample_bars` 边界**：空输入 + `raw_bars=False` 现在返回 8 列 + 与非空一致 dtype 的空 DataFrame（`symbol=object` / `dt=datetime64[ns]` / OHLCV=`float64`），避免 `pd.DataFrame([])` 退化成 0 列 KeyError，以及 dtype 全 `object` 让 `df["dt"].dt` accessor 抛 AttributeError。
- **`PyOperate.__repr__` 一致性**（`crates/czsc-core/src/objects/operate.rs`）：此前返回 `"PyOperate::HL"`，泄漏内部 Rust 结构名；现修正为 `"Operate.HL"`，与三个兄弟 enum（`Freq` / `Mark` / `Direction`）的 `EnumName.Variant` 形式一致，对齐 Python `enum.Enum` 约定。

### Notes

- 本批改动有两项**已知限制**（已 docstring 标注，留单独 PR 处理）：
  - `resample_bars` 的 `drop_unfinished=True` 对非分钟 target（D/W/M/S/Y）实际是 no-op，因 `freq_end_time` 把日级以上桶 dt 归到 `00:00:00`。
  - `BarGenerator::new` 为 base 桶也预分配 `bars.len()+1` 容量，单次大输入（百万级）会有一倍内存浪费。

---

## [1.0.0-rc.5] — 2026-05-18

> **1.0.0-rc.4 的紧急重发**。rc.4 wheel build + smoke 全部 6 平台都成功，但 `publish-to-pypi` step 的 `Verify version consistency` 检查写错了：把 Cargo `1.0.0-rc.4` (SemVer) 与 wheel filename `1.0.0rc4` (PEP 440) 直接字符串对比——maturin 必然要把 SemVer 的 `-rc.N` 翻译成 PEP 440 的 `rcN`，所以这个检查在任何 prerelease tag 上都会必然失败。
> 这个 bug 之前没 surface 是因为前面 4 轮 RC 都没跑到 publish step——一直被前置 step 拦下。
> rc.4 的 wheel 已经成功 build 但**未上传 PyPI**（publish 在 verify 失败时 skip），所以版本号未占名，bump rc.5 安全。

### Fixed

- **`.github/workflows/python-publish.yml::publish-to-pypi::Verify version consistency`**: 比对 wheel filename 之前先把 SemVer prerelease 翻译到 PEP 440 normalized form（`-alpha.N`/`-beta.N`/`-rc.N`/`-dev.N`/`-post.N` → `aN`/`bN`/`rcN`/`.devN`/`.postN`），与 [`packaging.version.canonicalize_version`](https://packaging.pypa.io/en/latest/version.html) 对齐。

---

## [1.0.0-rc.4] — 2026-05-18

> **1.0.0-rc.3 的紧急重发**（未发布——见上方 1.0.0-rc.5 重发说明）。rc.3 wheel build 5/6 平台成功，但卡在 `macos-13` (Intel native) GitHub-hosted runner pool——单 job 排队 1h+ 没分到 runner，让 publish-to-pypi `needs: [build-wheels, smoke-test]` 永远 wait。代码层面 rc.3 已无问题；本版本仅改 CI runner 选择。

### Fixed

- **`.github/workflows/python-publish.yml`**: macOS wheel runner 改用 `macos-latest`（Apple Silicon 池子充裕），x86_64 wheel 走 cross-compile（Apple 工具链原生支持 `-arch x86_64`），不再依赖资源紧张的 `macos-13` Intel runner。同步移除 smoke-test 里的 `macos-13` smoke 项（x86_64 wheel 无法在 Apple Silicon runner 上 import 验证）。dispatch 端到端跑通：sdist 20s / 3 Linux wheels 8-9min / Windows 14m52s / macos-latest x86_64 cross 18m11s / macos-latest aarch64 native + smoke 47s / Linux smoke 25s，全绿。

---

## [1.0.0-rc.3] — 2026-05-18

> **1.0.0-rc.2 的紧急重发**（未发布——见上方 1.0.0-rc.4 重发说明）。rc.2 push tag 后 CI 又踩到两个新坑：
> 1. `crates/czsc-trader/src/strategy.rs` 顶层 `use` 在 PR-G 时删了 `load_position`，但 test 模块 line 466 仍然调它——本地 `cargo build` 不 check tests 没发现，CI 的 `cargo check --workspace --all-targets` 把 tests 也 typecheck 一遍，挂在 E0425；
> 2. `crates/czsc-python/build.rs::check_python_version()` 在 manylinux container 内强制检查 PATH 上 python3 ≥ 3.10，但 maturin cross-compile 时通过 `PYO3_CONFIG_FILE` 精确指定目标解释器，PATH 默认 python3 是容器自带 3.9——4 个 Linux wheel build 全挂；
> 3. `ring 0.17.14` cross-compile 到 aarch64 manylinux2014 时 cross-gcc 没把 `__ARM_ARCH` 宏传给 ASM，sha256-armv8-linux64.S 编译失败；
> 4. workflow `.github/workflows/python-publish.yml` 的 `Build wheel (maturin)` step 没给 manylinux container 注入 cross-compile CFLAGS。
>
> 本版本一次性修齐 1+2+3+4，dispatch 端到端验证 5/6 平台（macOS x86_64 因 GitHub 公开 runner pool 高负载排队 13h 未跑到 build wheel step，但代码层无问题）。

### Fixed

- **`build.rs`**: 在 `PYO3_CONFIG_FILE` 存在时跳过 PATH python3 版本预检（信任 maturin 的精确配置，避免 manylinux container 内 PATH 默认 python3=3.9 误伤 wheel build）。
- **`strategy.rs`**: 在 `#[cfg(test)] mod tests` 的 `use czsc_core::objects::position::{Position, ...}` 中恢复 `load_position` import（PR-G 删主代码 import 时漏看 test 仍调用）。
- **`.github/workflows/python-publish.yml`**: 给 maturin-action `before-script-linux` 加 `export CFLAGS_aarch64_unknown_linux_gnu="-D__ARM_ARCH=8"`，修 ring 0.17.x 在 aarch64 manylinux2014 cross-compile 时的 ASM 编译错。

---

## [1.0.0-rc.2] — 2026-05-17

> **1.0.0-rc.1 的紧急重发**（未发布——见上方 1.0.0-rc.3 重发说明）。1.0.0-rc.1 的 git tag 已 push 到 GitHub，但 CI workflow（`rust-publish.yml` / `python-publish.yml`）的 `Verify version consistency` step 使用了 `awk gsub(/.../, "\\1")` 反向引用——gawk 不支持，导致 `CARGO_VERSION` 被解析为字面量 `\1` 而非 `1.0.0-rc.1`，PyPI / crates.io 发布双双失败。本版本同时修了两个 workflow 文件（改用 `awk -F'"'` 切字段，POSIX 兼容），并按 SemVer 规范 bump 到 rc.2 重发（1.0.0-rc.1 未实际上传到任何 registry，但 RC 失败号不复用是惯例）。

### Fixed

- **CI** `verify_version_consistency` 步骤改用 `awk -F'"' '{print $2}'` 抽取 Cargo.toml 版本号，避免 gawk 的 backreference 限制。

---

## [1.0.0-rc.1] — 2026-05-17

> **1.0.0 候选预发布版本（未发布——见上方 1.0.0-rc.2 重发说明）。** 缠论核心算法（分型、笔、中枢、信号体系）从 Python 迁移到 Rust，
> 通过 PyO3 扩展 `czsc._native` 暴露给 Python 用户；Rust 用户可直接
> `cargo add czsc`（或子 crate）使用。本版本含大量 **breaking changes**，从
> 0.9.X / 0.10.X 升级请阅读下方「迁移指引」。final 1.0.0 在该 RC 通过下游验证后 promote。

### 架构总览

```
czsc (Python 包)
├── czsc._native          ← Rust 扩展（PyO3），缠论核心
│   ├── CZSC / FX / BI / ZS / RawBar / NewBar / BarGenerator
│   ├── Freq / Mark / Direction / Signal / Event / Position / Operate
│   ├── CzscTrader / CzscSignals / generate_czsc_signals
│   ├── signals.*         ← 250+ 信号函数（13+ 子模块）
│   └── ta.*              ← Rust TA 算子（ema/sma/boll 等，仅内部使用）
├── czsc.traders          ← Python 门面，汇聚 Rust 交易 API
├── czsc.utils.plotting   ← Plotly 可视化（kline / weight）+ lightweight_charts HTML
├── czsc.strategies       ← 策略门面（CzscStrategyBase / CzscJsonStrategy，全部走 Rust 透传）
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

#### 清理非缠论核心 API · 二阶段（PR-A/B/C，1.0.0 核心重构延续）

> 上一波清理后，继续删除 17 个无明显业务依赖的工具 / 分析 / 绘图 API。Rust 缠论核心（`czsc._native`）零影响；缠论 K 线可视化统一收敛到 `czsc.utils.plotting.lightweight`。

- **删除 13 个非核心 API + 3 个整删模块**（PR-A）：批量删除入口；旧 `czsc.eda.py`、`czsc.utils.analysis.stats` 等模块整目录下线。
- **拆分 mark_cta_periods / mark_volatility 到 utils 独立文件**（PR-B）：从原 `czsc/eda.py` 搬到 `czsc/utils/`，导出路径保持 `czsc.mark_cta_periods` / `czsc.mark_volatility` 不变。
- **删除 8 个工具 / 分析函数**：
  - `czsc.eda.{cal_yearly_days, weights_simple_ensemble, cal_trade_price, turnover_rate}` —— 一行 pandas 可替代，详见迁移文档。
  - `czsc.utils.{create_grid_params, mac_address}` —— 直接用 `sklearn.ParameterGrid` / `uuid.getnode()`。
  - `czsc.utils.analysis.{holds_performance, rolling_daily_performance}` —— 用 `wbt.WeightBacktest` + `daily_performance`。
- **删除 9 个绘图 API**（PR-C）：
  - `czsc.utils.plotting.kline.{KlineChart, plot_czsc_chart}` —— 改用 `czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}`（离线 HTML，多周期联立）；`kline.plot_nx_graph` 保留。
  - `czsc.utils.plotting.backtest.{plot_cumulative_returns, plot_drawdown_analysis, plot_daily_return_distribution, plot_monthly_heatmap, plot_backtest_stats, plot_colored_table, plot_long_short_comparison}` —— 整文件 `git rm`；HTML 报告改用 `wbt.generate_backtest_report` 或自行 `plotly.express` 直绘。
  - 附带删除 `czsc.utils.plotting.{backtest.py, common.py}` 整文件；`_macd.py` 因 `lightweight/_data.py` 仍 lazy import `compute_macd`，保留为内部模块。
- **PR-C 同步**：`czsc.traders.base` / `czsc.traders.sig_parse` 两个纯透传文件整文件 `git rm`，调用方改为 `from czsc.traders import ...` 直取 facade；`czsc.traders.optimize` 整文件 `git mv` 到 `czsc.utils.optimize`（职责更贴近 utils），调用方用 `from czsc.utils.optimize import OpensOptimize, ExitsOptimize, CzscOpenOptimStrategy, CzscExitOptimStrategy`。
- **测试 / 文档同步**：
  - 新增 `tests/compat/test_drop_secondary_api.py` 双轨防回归（hasattr × 31 组合 + 模块 import × 2）。
  - `tests/compat/test_api_no_streamlit.py` 中 `test_plot_kline_still_importable` / `test_plot_backtest_still_importable` 反转为"必须删除"；INDEPENDENT_FILES 移出已删的 `backtest.py`。
  - `tests/compat/snapshots/api_v1.json` 新增 `removed_v2_batch` 字段（10 个被从 `czsc.*` 顶层移除的 API）。
  - 删除 `tests/test_plotly_plot.py` / `test_plot_colored_table.py` / `test_plot_long_short_comparison.py` 及 `docs/examples/{03,09}.py`。
  - `README.md` / `docs/examples.md` / `docs/migration/cleanup-non-czsc-core.md` 同步精修。

#### 开发宪法第一条收口 · Rust 下沉（PR-D 至 PR-G，1.0.0 核心重构延续）

> 落实 [`CLAUDE.md` 开发宪法第一条](CLAUDE.md#第一条--rust--python-行为一致)："需要 Rust 实现的部分必须同时满足 Rust crate 与 Python wheel 行为一致（Python 端纯透传，禁止再写适配层）"。本批 PR 把 Python 侧 4 处仍残留的"适配层"代码全部下沉到 Rust，Python 顶层 import 路径保持不变。

- **PR-D · `monotonicity` 改为 Rust 实现**：原 `czsc/eda.py` 中基于 `scipy.stats.spearmanr` / `kendalltau` / `pearsonr` 的实现整段下沉到 `crates/czsc-utils` Rust 端（Spearman 自行实现 fractional ranking + tie correction，Kendall O(n²) τ-b，Pearson 标准公式）。`czsc.monotonicity` 现在是 1 行 `_native.*` 透传；运行时不再依赖 `scipy`（数值上与 scipy 在 1e-12 级误差内一致，已在 `tests/unit/test_monotonicity_parity.py` 校验）。
- **PR-E · Rust 端新增 strategy 模块**：在 `crates/czsc-trader/src/strategy.rs` 中新增 `Strategy` trait 与 `JsonStrategy` struct，沉淀策略门面的纯 Rust 数据模型（持仓集合、唯一信号集合、symbol 绑定等），为 PR-F/G 的 Python 端透传提供底座；`cargo test -p czsc-trader::strategy` 全套覆盖。
- **PR-F · `CzscStrategyBase.unique_signals` 走 Rust 纯透传**：Python 端原本基于 `set` + `sorted` 的去重逻辑下沉到 `JsonStrategy::unique_signals`（保序去重，按 positions 输入顺序遍历，与 Python `CzscStrategyBase.unique_signals` 旧实现 byte-for-byte 一致）。Python 侧只剩 1 行 `return self._native.unique_signals()`。
- **PR-G · `save_positions` / `load_positions` 整段下沉 Rust**：
  - 原 Python 端用 `hashlib.md5(json.dumps(...))` 校验文件完整性，且 Python 侧手工剥离 `symbol` 字段。本次全部下沉到 `czsc_trader::strategy::{save_position_to_file, load_position_from_file}`：
    - 文件完整性校验改用 `sha256(canonical JSON)`，可在 Rust / Python 端 byte-for-byte 一致复现，并兼容老文件中遗留的 `md5` 字段（已加迁移路径）。
    - `symbol` 字段在 save 时自动剥离（让配置可复用），load 时由调用方注入。
  - Python 端 `CzscStrategyBase.save_positions` / `load_positions` 现在是纯 `_native.*` 透传；新增源码级 ratchet `tests/unit/test_strategy_save_load_parity.py::test_strategies_module_no_longer_uses_hashlib_or_json` 防止后续 PR 再在 Python 侧引入 `hashlib` / `json` 写文件逻辑。
- **CLAUDE.md 同步**：开发宪法第一条章节补"PR-G 落地参考（2026-05-17）"小节，明确 `unique_signals` / `save_positions` / `load_positions` 已 100% 下沉 Rust，违反本条的新 PR 会被 ratchet 测试拦下。

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

[1.0.0-rc.5]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.5
[1.0.0-rc.5]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.5
[1.0.0-rc.4]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.4
[1.0.0-rc.3]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.3
[1.0.0-rc.2]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.2
[1.0.0-rc.1]: https://github.com/waditu/czsc/releases/tag/v1.0.0-rc.1
