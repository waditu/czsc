# Rust 实现的 czsc 核心对象迁移 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Each task is a complete RED → GREEN → REFACTOR → COMMIT cycle. **Iron Law**: 没有失败测试就不写实现代码。

**Goal:** 将 rs-czsc 的 Rust + PyO3 核心实现一次性 fork 进 czsc 仓库，重构成 Rust workspace + Python 薄层混合包，按 superpowers TDD 范式分 12 个 Phase 推进，最终用 maturin + Trusted Publishing 发布 czsc 1.0.0。

**Architecture:** czsc 仓库根新增 `Cargo.toml` workspace + `crates/` 9 个 crate，扩展模块名 `czsc._native`。所有面向用户的 API 由 `czsc/__init__.py` re-export，禁止用户感知 `rs_czsc` / `czsc._native`。`WeightBacktest` / `daily_performance` / `top_drawdowns` / `mock` 通过硬依赖 `wbt` 包提供。

**Tech Stack:** Rust (workspace, edition 2024) / PyO3 0.25 (abi3-py310) / maturin / Polars 0.42 / Python 3.10+ / pytest / ruff / basedpyright / criterion / cargo

**关联文档:**
- 设计文档: [docs/superpowers/specs/2026-05-03-rust-czsc-migration-design.md](../specs/2026-05-03-rust-czsc-migration-design.md) (v0.3)
- 迁移记录: [docs/MIGRATION_NOTES.md](../../MIGRATION_NOTES.md)
- rs-czsc 基线: `47ef6efa2b2bac63881a233c01671e8e9860162f` (2026-04-06)

**进度可视化:** 每个 task 标注其会让 Phase A 失败测试基线（A1~A8）由 RED 转 GREEN 的项；CI `scripts/red_green_report.py` 在每次 commit 后输出 `红 X 项 / 绿 Y 项 / 总 N 项`。

---

## 目录

- Phase 0 — Spec 评审 + Plan 产出（本文件 = Phase 0 产出）
- Phase A — 写验收级失败测试基线（8 类，A1~A8 全部 RED）
- Phase B — Rust workspace 9 crate 骨架
- Phase C — czsc-utils 测试驱动迁移（→ A6 GREEN）
- Phase D — czsc-core 测试驱动迁移（→ A2/A3 GREEN）
- Phase E — czsc-ta + czsc-signal-macros（→ A5 GREEN）
- Phase F — czsc-signals 迁移（→ A4 GREEN）
- Phase G — czsc-trader 迁移（含 strategies）
- Phase H — czsc-python 聚合 + Python 包重构（→ A1 GREEN）
- Phase I — wbt 集成（→ A7 GREEN）
- Phase J — Python 删减
- Phase K — CI / Trusted Publishing / finishing（→ A8 GREEN）

---

## Phase 0 — Spec 评审 + Plan 产出（0.5 天）

> 本 phase 仅产出文档，不写代码。

### Task 0.1: Worktree 隔离与基线锁定

**Files:**
- Create: `docs/MIGRATION_NOTES.md`

- [x] **Step 1:** `git worktree add` 至 `refactor/rust-czsc-migration` 分支（手工）
- [x] **Step 2:** `cd /Users/jun/Documents/vscodePro/rs_czsc && git rev-parse HEAD` → `47ef6efa2b2bac63881a233c01671e8e9860162f`
- [x] **Step 3:** 写 `docs/MIGRATION_NOTES.md`，记录基线 commit、czsc-only 改动占位章节
- [x] **Verify:** 文件存在 `docs/MIGRATION_NOTES.md`，包含基线 commit hash
- [x] **Commit:** `docs(migration): record rs-czsc baseline commit 47ef6efa`

### Task 0.2: 同步 v0.1 spec 至 v0.3

**Files:**
- Modify: `docs/superpowers/specs/2026-05-03-rust-czsc-migration-design.md`

- [x] **Step 1:** 从飞书 wiki 拉取 v0.3 内容，完整覆盖本地 spec
- [x] **Verify:** 状态行包含 "v0.3 草案" 字样
- [x] **Commit:** `docs(spec): bump rust-czsc-migration design to v0.3`

### Task 0.3: 产出 plan 文件（本文件）

**Files:**
- Create: `docs/superpowers/plans/2026-05-03-rust-czsc-migration.md`

- [x] **Step 1:** 按 superpowers:writing-plans 规范展开 Phase 0~K 的 task
- [x] **Verify:** plan 自审 checklist：① 无 TBD / placeholder ② 每 task 有 test code + run command + expected output ③ 每 task 以 commit 结尾 ④ 标注对 A1~A8 的 RED→GREEN 影响
- [x] **Commit:** `docs(plan): scaffold superpowers TDD plan for rust-czsc migration`

---

## Phase A — 写验收级失败测试基线（1.5 天）

> 把 §6 验收标准 + §3.1 公共 API 表翻译成可执行测试，跑出全 RED。**禁止**在本 phase 写任何 Rust 实现或修改 czsc/* 业务代码。

### Task A.1: 公共 API 快照测试（→ A1 RED 基线）

**Files:**
- Create: `test/compat/__init__.py`
- Create: `test/compat/test_public_api.py`
- Create: `test/compat/snapshots/api_v1.json`

- [ ] **Step 1: 写失败测试** —— 从 spec §3.1 抓取 80+ 公共名称（顶层 + `czsc.ta.*` + `czsc.signals.{bar,cxt,...}` + `czsc.traders.*`），逐项 `getattr(czsc, name)`：

```python
# test/compat/test_public_api.py
import importlib
import json
from pathlib import Path

import pytest

SNAPSHOT = Path(__file__).parent / "snapshots" / "api_v1.json"


def _load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_top_level_names_importable():
    czsc = importlib.import_module("czsc")
    snap = _load_snapshot()
    missing = [n for n in snap["top_level"] if not hasattr(czsc, n)]
    assert not missing, f"Missing czsc.* names: {missing}"


@pytest.mark.parametrize("subpkg", ["bar", "cxt", "tas", "vol", "pressure", "obv", "cvolp"])
def test_signal_subpackages_present(subpkg):
    mod = importlib.import_module(f"czsc.signals.{subpkg}")
    assert mod is not None


def test_traders_namespace_complete():
    traders = importlib.import_module("czsc.traders")
    snap = _load_snapshot()
    missing = [n for n in snap["traders"] if not hasattr(traders, n)]
    assert not missing, f"Missing czsc.traders.* names: {missing}"


def test_ta_namespace_complete():
    ta = importlib.import_module("czsc.ta")
    snap = _load_snapshot()
    missing = [n for n in snap["ta"] if not hasattr(ta, n)]
    assert not missing, f"Missing czsc.ta.* names: {missing}"


def test_no_legacy_dummy_backtest():
    czsc = importlib.import_module("czsc")
    assert not hasattr(czsc, "DummyBacktest"), "DummyBacktest must be removed"


def test_no_czsc_use_python_branch():
    import czsc.envs as envs
    assert not hasattr(envs, "CZSC_USE_PYTHON")
```

`api_v1.json` 内容（按 §3.1 公共 API 表填，不少于 80 条）：

```json
{
  "top_level": [
    "CZSC", "FX", "BI", "ZS", "RawBar", "NewBar",
    "Freq", "Mark", "Direction", "Operate",
    "Signal", "Event", "Position",
    "BarGenerator", "format_standard_kline",
    "freq_end_time", "is_trading_time",
    "check_bi", "check_fx", "check_fxs", "remove_include",
    "CzscTrader", "CzscSignals",
    "generate_czsc_signals", "get_unique_signals",
    "WeightBacktest", "daily_performance", "top_drawdowns",
    "ultimate_smoother", "rolling_rank", "ema", "sma", "boll_positions",
    "mock", "envs", "signals", "traders", "ta", "utils",
    "connectors", "sensors", "svc"
  ],
  "traders": [
    "CzscTrader", "CzscSignals",
    "generate_czsc_signals", "get_unique_signals",
    "WeightBacktest", "SignalsParser"
  ],
  "ta": [
    "ultimate_smoother", "rolling_rank", "ema", "sma", "boll_positions"
  ]
}
```

- [ ] **Step 2: 跑测试看 RED**

```bash
uv run pytest test/compat/test_public_api.py -v
```

预期 5 个测试 FAIL（`Missing czsc.* names: [...]`），不能是 ERROR / SKIP。

- [ ] **Commit:** `test(compat): add public API snapshot test (RED baseline for A1)`

### Task A.2: PyO3 类 pickle 协议测试（→ A2 RED 基线）

**Files:**
- Create: `test/unit/__init__.py`
- Create: `test/unit/test_pickle.py`

- [ ] **Step 1: 写失败测试**

```python
# test/unit/test_pickle.py
import pickle

import pytest


@pytest.fixture(scope="module")
def small_bars():
    from czsc.mock import generate_symbol_kines  # 来自 wbt 转发
    from czsc import format_standard_kline, Freq

    df = generate_symbol_kines("000001", "30分钟", "20240101", "20240105", seed=42)
    return format_standard_kline(df, freq=Freq.F30)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda b: __import__("czsc").CZSC(b), id="CZSC"),
        pytest.param(lambda _: __import__("czsc").BarGenerator(base_freq="30分钟", freqs=["日线"]), id="BarGenerator"),
        pytest.param(lambda _: __import__("czsc").Position(symbol="000001", name="t", opens=[], exits=[]), id="Position"),
        pytest.param(lambda b: __import__("czsc").CzscSignals(b), id="CzscSignals"),
        pytest.param(lambda b: __import__("czsc").CzscTrader(b), id="CzscTrader"),
    ],
)
def test_pickle_roundtrip(factory, small_bars):
    obj = factory(small_bars)
    blob = pickle.dumps(obj)
    restored = pickle.loads(blob)
    assert type(restored) is type(obj)
    if hasattr(obj, "__getstate__"):
        assert restored.__getstate__() == obj.__getstate__()
```

- [ ] **Step 2: 跑测试看 RED** —— `uv run pytest test/unit/test_pickle.py -v`，预期 5 个 FAIL（pickle 抛异常或 fixture 失败）。
- [ ] **Commit:** `test(unit): add pickle roundtrip test for PyO3 classes (RED baseline for A2)`

### Task A.3: 缠论核心对象 parity 测试（→ A3 RED 基线）

**Files:**
- Create: `test/unit/test_core_parity.py`
- Create: `test/unit/snapshots/core_parity_seed42.json`

- [ ] **Step 1:** 用固定 seed `wbt.mock.generate_symbol_kines("000001", "30分钟", "20240101", "20240301", seed=42)` 生成 K 线，跑外部 `rs_czsc.CZSC(bars)`，把 `len(fxs) / len(bi_list) / len(zs_list) / 关键 fx mark 序列` 写入快照 JSON。
- [ ] **Step 2: 写失败测试**

```python
# test/unit/test_core_parity.py
import json
from pathlib import Path

import pytest

SNAP = Path(__file__).parent / "snapshots" / "core_parity_seed42.json"


@pytest.fixture(scope="module")
def baseline_snapshot():
    return json.loads(SNAP.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def czsc_obj():
    import czsc
    from wbt.mock import generate_symbol_kines

    df = generate_symbol_kines("000001", "30分钟", "20240101", "20240301", seed=42)
    bars = czsc.format_standard_kline(df, freq=czsc.Freq.F30)
    return czsc.CZSC(bars)


def test_fxs_count(czsc_obj, baseline_snapshot):
    assert len(czsc_obj.fxs) == baseline_snapshot["fxs_count"]


def test_bi_list_count(czsc_obj, baseline_snapshot):
    assert len(czsc_obj.bi_list) == baseline_snapshot["bi_count"]


def test_fxs_marks_sequence(czsc_obj, baseline_snapshot):
    marks = [str(fx.mark) for fx in czsc_obj.fxs]
    assert marks == baseline_snapshot["fxs_marks"]


def test_bi_directions_sequence(czsc_obj, baseline_snapshot):
    dirs = [str(bi.direction) for bi in czsc_obj.bi_list]
    assert dirs == baseline_snapshot["bi_directions"]
```

- [ ] **Step 3: 跑测试看 RED** —— `uv run pytest test/unit/test_core_parity.py -v`，预期 4 个 FAIL（czsc.CZSC 来源是 Python fallback 或 rs_czsc，与本仓库未来 Rust 实现不一致）。
- [ ] **Commit:** `test(unit): lock core parity snapshot at seed 42 (RED baseline for A3)`

### Task A.4: 信号函数 parity 测试（→ A4 RED 基线）

**Files:**
- Create: `test/unit/test_signals_parity.py`
- Create: `test/unit/snapshots/signals_parity_seed42.json`

- [ ] **Step 1:** 选定 30 个核心信号（按 spec §8 附录 A 的 `czsc.signals.*` 列表），固定 seed 跑 `rs_czsc` 收集签名输出 → 写快照。
- [ ] **Step 2: 写失败测试** 形式为 `parametrize(signal_name, expected_dict)`，逐一对比。
- [ ] **Step 3:** `uv run pytest test/unit/test_signals_parity.py -v` → 30 个 FAIL（czsc.signals 子包尚未指向 czsc._native）。
- [ ] **Commit:** `test(unit): lock 30 signal functions parity (RED baseline for A4)`

### Task A.5: TA 算子 parity 测试（→ A5 RED 基线）

**Files:**
- Create: `test/unit/test_ta_parity.py`

- [ ] **Step 1:** 对 `czsc.ta.{ema, sma, rolling_rank, boll_positions, ultimate_smoother}` 5 个核心算子，与 `talib.{EMA, SMA}` 结果对比，容差 ≤ 1e-6。

```python
# test/unit/test_ta_parity.py
import numpy as np
import pytest


@pytest.fixture
def series():
    rng = np.random.default_rng(42)
    return rng.standard_normal(1024).astype(np.float64)


def test_ema_matches_talib(series):
    import czsc.ta as ta
    import talib

    expected = talib.EMA(series, timeperiod=14)
    actual = ta.ema(series, length=14)
    np.testing.assert_allclose(actual[20:], expected[20:], rtol=1e-6, atol=1e-6)


def test_sma_matches_talib(series):
    import czsc.ta as ta
    import talib

    expected = talib.SMA(series, timeperiod=20)
    actual = ta.sma(series, length=20)
    np.testing.assert_allclose(actual[20:], expected[20:], rtol=1e-6, atol=1e-6)


def test_rolling_rank_returns_finite(series):
    import czsc.ta as ta

    out = ta.rolling_rank(series, window=20)
    assert np.isfinite(out[20:]).all()
```

- [ ] **Step 2:** `uv run pytest test/unit/test_ta_parity.py -v` → 3 个 FAIL（`czsc.ta` 模块当前不存在）。
- [ ] **Commit:** `test(unit): add TA parity vs TA-Lib (RED baseline for A5)`

### Task A.6: is_trading_time 行为测试（→ A6 RED 基线）

**Files:**
- Create: `test/unit/test_trading_time.py`

- [ ] **Step 1:** 列出 A 股 / 港股 / 数字货币 三类日历共 ~12 个典型时间点，断言 `czsc.is_trading_time(dt, market="...")` 返回值。

```python
# test/unit/test_trading_time.py
from datetime import datetime

import pytest


@pytest.mark.parametrize(
    "market, dt, expected",
    [
        ("astock", datetime(2024, 1, 8, 9, 30), True),    # 周一 9:30
        ("astock", datetime(2024, 1, 8, 11, 30), True),   # 上午收盘前
        ("astock", datetime(2024, 1, 8, 12, 30), False),  # 午休
        ("astock", datetime(2024, 1, 8, 15, 0), True),    # 下午收盘
        ("astock", datetime(2024, 1, 6, 10, 0), False),   # 周六
        ("hk", datetime(2024, 1, 8, 9, 30), True),
        ("hk", datetime(2024, 1, 8, 12, 0), False),       # 午休
        ("hk", datetime(2024, 1, 8, 16, 0), True),        # 收盘前
        ("crypto", datetime(2024, 1, 6, 3, 0), True),     # 24x7
        ("crypto", datetime(2024, 12, 25, 0, 0), True),
    ],
)
def test_is_trading_time(market, dt, expected):
    import czsc

    assert czsc.is_trading_time(dt, market=market) is expected
```

- [ ] **Step 2:** `uv run pytest test/unit/test_trading_time.py -v` → 10 个 FAIL（函数不存在）。
- [ ] **Commit:** `test(unit): add is_trading_time behavior test (RED baseline for A6)`

### Task A.7: WeightBacktest 通过 wbt 集成（→ A7 RED 基线）

**Files:**
- Create: `test/integration/__init__.py`
- Create: `test/integration/test_weight_backtest.py`

- [ ] **Step 1: 写失败测试**

```python
# test/integration/test_weight_backtest.py
def test_czsc_weight_backtest_is_wbt():
    import czsc
    import wbt

    assert czsc.WeightBacktest is wbt.WeightBacktest


def test_czsc_daily_performance_is_wbt():
    import czsc
    import wbt

    assert czsc.daily_performance is wbt.daily_performance


def test_czsc_top_drawdowns_is_wbt():
    import czsc
    import wbt

    assert czsc.top_drawdowns is wbt.top_drawdowns
```

- [ ] **Step 2:** `uv run pytest test/integration/test_weight_backtest.py -v` → 3 个 FAIL（当前 `czsc.WeightBacktest` 不是 `wbt.WeightBacktest`）。
- [ ] **Commit:** `test(integration): assert czsc.WeightBacktest is wbt.WeightBacktest (RED baseline for A7)`

### Task A.8: 安装冒烟测试（→ A8 RED 基线）

**Files:**
- Create: `test/smoke/__init__.py`
- Create: `test/smoke/test_install.py`

- [ ] **Step 1: 写失败测试**

```python
# test/smoke/test_install.py
import subprocess
import sys
from pathlib import Path


def test_wheel_install_and_import(tmp_path):
    """构建 wheel → 干净 venv → import czsc → 主流程跑通"""
    repo = Path(__file__).resolve().parents[2]
    dist = repo / "dist"
    venv = tmp_path / "venv"

    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    py = venv / "bin" / "python"

    # 假定 maturin build 已产出 wheel 到 dist/
    wheels = sorted(dist.glob("czsc-*.whl"))
    assert wheels, "No wheel found in dist/ — run `maturin build --release` first"

    subprocess.run([str(pip), "install", str(wheels[-1])], check=True)
    out = subprocess.run(
        [str(py), "-c", "import czsc; print(czsc.CZSC.__module__)"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "czsc" in out.stdout
```

- [ ] **Step 2:** `uv run pytest test/smoke/test_install.py -v` → 1 个 FAIL（`dist/czsc-*.whl` 不存在）。
- [ ] **Commit:** `test(smoke): add wheel install smoke test (RED baseline for A8)`

### Task A.verify: RED 基线全量校验

- [ ] **Step 1:** `uv run pytest test/compat test/unit test/integration test/smoke --tb=no -q`
- [ ] **Verify:** 输出含 56+ FAIL，0 ERROR，0 SKIP（与设计文档 §5.2 一致）
- [ ] **Verify:** 把数字写入 `docs/MIGRATION_NOTES.md` 第 4 节"Phase A 基线统计"
- [ ] **Commit:** `docs(migration): record Phase A RED baseline counts`

---

## Phase B — Rust workspace 9 crate 骨架（1 天）

### Task B.1: workspace 根 Cargo.toml + 9 个空 crate

**Files:**
- Create: `Cargo.toml`
- Create: `rust-toolchain.toml`
- Create: `.cargo/config.toml`
- Create: `crates/{czsc-core,czsc-utils,czsc-ta,czsc-signals,czsc-trader,czsc-signal-macros,error-macros,error-support,czsc-python}/Cargo.toml`
- Create: `crates/{czsc-core,czsc-utils,czsc-ta,czsc-signals,czsc-trader,czsc-signal-macros,error-macros,error-support,czsc-python}/src/lib.rs`
- Create: `tests/test_workspace_layout.sh`

- [ ] **Step 1: 写失败测试** —— `tests/test_workspace_layout.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
required=( czsc-core czsc-utils czsc-ta czsc-signals czsc-trader czsc-signal-macros error-macros error-support czsc-python )
for c in "${required[@]}"; do
  test -f "crates/$c/Cargo.toml" || { echo "missing crates/$c/Cargo.toml"; exit 1; }
  test -f "crates/$c/src/lib.rs" || { echo "missing crates/$c/src/lib.rs"; exit 1; }
done
cargo metadata --format-version 1 --no-deps | python3 -c "
import json, sys
data = json.load(sys.stdin)
members = {pkg['name'] for pkg in data['packages']}
required = set('${required[*]}'.split())
missing = required - members
assert not missing, f'cargo workspace missing: {missing}'
print(f'OK: {len(required)} crates registered')
"
cargo build --workspace --quiet
```

- [ ] **Step 2: 跑测试看 RED** —— `bash tests/test_workspace_layout.sh` → 失败（目录不存在）
- [ ] **Step 3: GREEN** —— 创建 9 个空 crate（每个 `lib.rs` 仅含 `pub fn placeholder() {}`），写顶层 `Cargo.toml`：

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
polars         = { version = "0.42.0" }
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

`rust-toolchain.toml`：

```toml
[toolchain]
channel = "stable"
```

`.cargo/config.toml`：

```toml
[build]
incremental = true

[profile.release]
lto = true
opt-level = 3
codegen-units = 1
```

每个子 crate 的 `Cargo.toml` 形如：

```toml
[package]
name        = "czsc-core"
version.workspace    = true
edition.workspace    = true
license.workspace    = true
repository.workspace = true
description = "CZSC core analyzer (FX/BI/ZS/CZSC) — placeholder, to be migrated from rs-czsc"

[lib]
name = "czsc_core"
path = "src/lib.rs"
```

`czsc-signal-macros` / `error-macros` 是 proc-macro：

```toml
[package]
name        = "czsc-signal-macros"
version.workspace    = true
edition.workspace    = true
license.workspace    = true

[lib]
proc-macro = true
path       = "src/lib.rs"
```

`czsc-python` 启用 pyo3 extension-module：

```toml
[package]
name        = "czsc-python"
version.workspace    = true
edition.workspace    = true
license.workspace    = true

[lib]
name       = "czsc_python"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { workspace = true }
```

- [ ] **Step 4: 跑测试看 GREEN** —— `bash tests/test_workspace_layout.sh` → `OK: 9 crates registered` + `cargo build --workspace` 成功
- [ ] **Verify:** `cargo metadata --no-deps | jq '.packages | length'` → `9`
- [ ] **Commit:** `feat(rust): scaffold workspace with 9 empty crates`

---

## Phase C — czsc-utils 测试驱动迁移（1 天）

> **模式：** "复制即测试"。**不**整体复制 `src/`，按 rs-czsc 测试逐个迁移。

### Task C.1: freq_data 模块

**Files:**
- Copy: `crates/czsc-utils/tests/test_freq_data.rs` ← rs-czsc 同名文件
- Copy: `crates/czsc-utils/src/freq_data.rs` ← rs-czsc 同名文件

- [ ] **Step 1 (RED):** 复制测试到 `crates/czsc-utils/tests/`，跑 `cargo test -p czsc-utils freq` → 失败（src 还空）
- [ ] **Step 2 (GREEN):** 复制 `czsc-utils/src/freq_data.rs`，更新 `lib.rs` 导出 `pub mod freq_data;`
- [ ] **Step 3:** 跑同样命令 → PASS
- [ ] **Commit:** `feat(utils): migrate freq_data module (TDD)`

### Task C.2: BarGenerator 模块

**Files:**
- Copy: `crates/czsc-utils/tests/test_bar_generator.rs`
- Copy: `crates/czsc-utils/src/bar_generator.rs`

- [ ] 同 Task C.1 模式
- [ ] **Commit:** `feat(utils): migrate BarGenerator module (TDD)`

### Task C.3: is_trading_time 新增（czsc-only）

**Files:**
- Create: `crates/czsc-utils/tests/test_trading_time.rs`
- Create: `crates/czsc-utils/src/trading_time.rs`

- [ ] **Step 1 (RED):** 写 Rust 单元测试，覆盖三类日历的 ~12 个时间点
- [ ] **Step 2 (GREEN):** 写 Rust 实现（A 股：9:30-11:30 / 13:00-15:00 weekday；港股：9:30-12:00 / 13:00-16:00；crypto：always）
- [ ] **Step 3:** PyO3 binding (`crates/czsc-utils/src/python/mod.rs`) — 暴露 `is_trading_time` 为 `#[pyfunction]`
- [ ] **Step 4 (RED → GREEN):** Python 端 `test/unit/test_trading_time.py`（Phase A 已写）由 RED 转 GREEN —— **A6 标志**
- [ ] **Commit:** `feat(utils): add is_trading_time with PyO3 binding (czsc-only)` + 更新 `MIGRATION_NOTES.md` §2.2

### Task C.4: PyO3 binding 注册

**Files:**
- Create: `crates/czsc-utils/src/python/mod.rs`

- [ ] 暴露 `BarGenerator` / `freq_end_time` / `is_trading_time`，提供 `pub fn register(py, m) -> PyResult<()>`
- [ ] **Commit:** `feat(utils): register python bindings for utils crate`

**Phase C 验证:**
- [ ] `cargo test -p czsc-utils` 全过
- [ ] Phase A 中 A6 由 RED 转 GREEN

---

## Phase D — czsc-core 测试驱动迁移（2 天）

> 对照 rs-czsc 的 `czsc-core` 模块清单（FX / BI / ZS / CZSC / Direction / Mark / Operate / Signal / Event / Position 等），每个数据类型一个子循环。

### Task D.1 ~ D.10: 每个 type 一个子循环

每个子循环统一模板：

1. **RED (Rust):** 复制 `crates/czsc-core/tests/test_<type>.rs`，跑 `cargo test -p czsc-core <type>` 失败
2. **GREEN (Rust):** 复制对应 `src/objects/<type>.rs` + `lib.rs` 导出，cargo test PASS
3. **RED (PyO3):** Python 端 `test/unit/test_<type>_py.py` 写 binding 行为断言，pytest 失败
4. **GREEN (PyO3):** 在 `crates/czsc-core/src/python/<type>.rs` 暴露 `#[pyclass]`，注册到 `czsc-python`
5. **RED (pickle):** 在 Phase A.2 中预先注入 `<type>` 的 pickle roundtrip case，pytest 失败
6. **GREEN (pickle):** 实现 `__getstate__` / `__setstate__`（serde + bincode），pytest PASS
7. **Commit:** `feat(core): migrate <type> with PyO3 + pickle support`

| Task | 类型 | rs-czsc 路径 | 影响 A 项 |
|-|-|-|-|
| D.1 | `Freq` (enum) | `czsc-core/src/objects/freq.rs` | A2/A3 |
| D.2 | `Mark` / `Direction` / `Operate` (enum) | `czsc-core/src/objects/enums.rs` | A2/A3 |
| D.3 | `RawBar` / `NewBar` | `czsc-core/src/objects/bar.rs` | A2/A3 |
| D.4 | `FX` | `czsc-core/src/objects/fx.rs` | A3 |
| D.5 | `BI` | `czsc-core/src/objects/bi.rs` | A3 |
| D.6 | `ZS` | `czsc-core/src/objects/zs.rs` | A3 |
| D.7 | `Signal` / `Event` | `czsc-core/src/objects/signal.rs` | A3 |
| D.8 | `Position` | `czsc-core/src/objects/position.rs` | A2 |
| D.9 | `CZSC` analyzer | `czsc-core/src/analyze/mod.rs` | A2/A3 |
| D.10 | `check_bi/check_fx/check_fxs/remove_include` 可见性提升 | `czsc-core/src/analyze/utils.rs` | A1 |

### Task D.10 特别说明

- **RED:** Python 端 `test/compat/test_public_api.py` 中 `check_bi/check_fx/check_fxs/remove_include` 4 项断言失败
- **GREEN:** 把 4 个函数从 `pub(crate)` 改为 `pub`，加 `#[pyfunction]`
- **MIGRATION_NOTES.md:** 写入 §2.1 表
- **Commit:** `feat(core): expose check_bi/check_fx/check_fxs/remove_include (czsc-only public)`

**Phase D 验证:**
- [ ] `cargo test -p czsc-core` 全过
- [ ] Phase A 中 A2 + A3 由 RED 转 GREEN（公共 API 涉及部分对应转 GREEN）

---

## Phase E — czsc-ta + czsc-signal-macros（1.5 天）

### Task E.1: czsc-ta 调用图静态分析

**Files:**
- Create: `MIGRATION_NOTES.md` §2.3 czsc-ta 算子裁剪清单

- [ ] **Step 1:** `rg "use czsc_ta" rs_czsc/crates/czsc-{trader,signals}/ --no-heading -o | sort -u` → 实际被引用的算子列表
- [ ] **Step 2:** 把白名单写入 `MIGRATION_NOTES.md` §2.3，未上榜的算子记入"被裁剪"
- [ ] **Commit:** `docs(migration): record czsc-ta operator whitelist`

### Task E.2 ~ E.N: 白名单算子逐个迁移

每个算子一个 RED→GREEN 子循环（参考 Phase C 模式），形如 `ema/sma/rolling_rank/boll_positions/ultimate_smoother/...`。

- [ ] PyO3 binding：启用 `rust-numpy` feature，`czsc-python` 注册为 `czsc._native.ta` 子模块

### Task E.last: czsc-signal-macros

- [ ] **RED:** 写最小宏展开测试 `crates/czsc-signal-macros/tests/test_signal_module.rs`
- [ ] **GREEN:** 复制 macro 实现，cargo test PASS
- [ ] **Commit:** `feat(macros): migrate signal_module proc-macro`

**Phase E 验证:**
- [ ] Phase A 中 A5 由 RED 转 GREEN

---

## Phase F — czsc-signals 迁移（1.5 天）

每个子模块（`bar / cxt / tas / vol / pressure / obv / cvolp`）一组 RED→GREEN 子循环：

### Task F.{bar,cxt,tas,vol,pressure,obv,cvolp}

1. **RED:** 复制 `crates/czsc-signals/tests/test_<sub>.rs`，cargo test 失败
2. **GREEN:** 复制 `src/<sub>/`，更新 `lib.rs`
3. **RED (Python):** `test/unit/test_signals_parity.py` 中该子模块的 case 失败（A4 的部分）
4. **GREEN:** PyO3 binding 注册 `czsc._native.signals.<sub>`，并 `czsc/signals/<sub>.py` re-export
5. **Commit:** `feat(signals): migrate <sub> module`

**Phase F 验证:**
- [ ] Phase A 中 A4 由 RED 转 GREEN

---

## Phase G — czsc-trader 迁移（含 strategies）（2 天）

### Task G.1 ~ G.4: 核心对象

| Task | 对象 | rs-czsc 路径 |
|-|-|-|
| G.1 | `CzscTrader` | `czsc-trader/src/trader.rs` |
| G.2 | `CzscSignals` | `czsc-trader/src/signals_holder.rs` |
| G.3 | `generate_czsc_signals` | `czsc-trader/src/generators.rs` |
| G.4 | `get_unique_signals` | `czsc-trader/src/utils.rs` |

每个一个 RED→GREEN 子循环。

### Task G.5: strategies 迁移到 Rust

**Files:**
- Create: `crates/czsc-trader/src/strategies/{base,json}.rs`
- Modify: `czsc/strategies.py` → 删除

- [ ] **Step 1 (RED):** Python 端 `test/integration/test_strategies.py` 断言 `czsc.CzscStrategyBase` 与原行为一致
- [ ] **Step 2 (GREEN):** Rust 端实现 `StrategyBase` / `JsonStrategy`，PyO3 暴露
- [ ] **Step 3:** 删 `czsc/strategies.py`，pytest 仍 GREEN
- [ ] **Commit:** `refactor(trader): migrate strategies from Python to Rust`

### Task G.6: WeightBacktest 暂保持 RED

- 本 phase 不实现，由 Phase I 由 wbt 接管

**Phase G 验证:**
- [ ] `cargo test -p czsc-trader` 全过
- [ ] A2/A3 中 trader 相关 case 转 GREEN
- [ ] A1 中 `CzscTrader/CzscSignals/generate_czsc_signals/get_unique_signals` 转 GREEN

---

## Phase H — czsc-python 聚合 + Python 包重构（1.5 天）

### Task H.1: czsc-python 聚合 register()

**Files:**
- Modify: `crates/czsc-python/src/lib.rs`

```rust
use pyo3::prelude::*;

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    czsc_core::python::register(py, m)?;
    czsc_utils::python::register(py, m)?;
    czsc_ta::python::register(py, m)?;
    czsc_signals::python::register(py, m)?;
    czsc_trader::python::register(py, m)?;
    Ok(())
}
```

- [ ] **Commit:** `feat(python): aggregate all crate registers in czsc._native`

### Task H.2: pyproject.toml 切换至 maturin

**Files:**
- Modify: `pyproject.toml`

- [ ] `[build-system]` → `maturin`
- [ ] `[tool.maturin]` → `module-name = "czsc._native"`、`features = ["pyo3/extension-module"]`、`manifest-path = "crates/czsc-python/Cargo.toml"`
- [ ] `[project.dependencies]` 加入 `wbt`
- [ ] 移除 `rs-czsc` PyPI 依赖（如有）
- [ ] **Commit:** `build: switch from hatchling to maturin`

### Task H.3: 重写 czsc/__init__.py

**Files:**
- Modify: `czsc/__init__.py`
- Delete: `czsc/core.py`

- [ ] 按 §3.1 表逐项 import；移除 `_LAZY_MODULES` / `_LAZY_ATTRS` / `__getattr__`
- [ ] 每加一项跑 `pytest test/compat/test_public_api.py -v`，记录 RED → GREEN 转换
- [ ] **Commit:** `refactor(init): rewrite czsc/__init__.py to re-export from czsc._native`

### Task H.4: 极薄化 czsc/signals/ + czsc/traders/ + czsc/ta/

- [ ] `czsc/signals/{bar,cxt,...}.py` 仅 `from czsc._native.signals.<sub> import *`
- [ ] `czsc/traders/__init__.py` 仅 import + re-export（保留 `sig_parse.py` 待评估）
- [ ] 新增 `czsc/ta/__init__.py` re-export `czsc._native.ta`
- [ ] **Commit:** `refactor: thin shells for czsc.signals/traders/ta`

**Phase H 验证:**
- [ ] Phase A 中 A1 由 RED 转 GREEN（80+ 公共名称全部可导入）

---

## Phase I — wbt 集成（0.5 天）

### Task I.1: 加 wbt 硬依赖

- [ ] `uv add wbt` → `pyproject.toml`
- [ ] **Commit:** `build: add wbt as hard dependency`

### Task I.2: re-export wbt 公共 API

**Files:**
- Modify: `czsc/__init__.py`、`czsc/traders/__init__.py`

- [ ] `from wbt import WeightBacktest, daily_performance, top_drawdowns`
- [ ] **Verify:** `pytest test/integration/test_weight_backtest.py -v` 全 GREEN（A7）
- [ ] **Commit:** `feat: wire wbt as the canonical backtest/perf provider`

### Task I.3: czsc/mock.py 退化为薄壳

**Files:**
- Modify: `czsc/mock.py`（537 行 → ~30 行）

- [ ] 仅保留 `from wbt.mock import generate_symbol_kines, generate_klines_with_weights` 等转发
- [ ] **Commit:** `refactor(mock): degrade to thin shell forwarding wbt.mock`

**Phase I 验证:**
- [ ] Phase A 中 A7 由 RED 转 GREEN

---

## Phase J — Python 删减（0.5 天）

按 §3.2 / §9 附录 B 的"完全删除"列表逐文件 `git rm`，每删一组跑 `pytest -q` 确认 GREEN 不变。

### Task J.1 ~ J.5

| Task | 删除目标 | 验证 |
|-|-|-|
| J.1 | `czsc/utils/ta.py` | `pytest test/unit/test_ta_parity.py` 仍 GREEN |
| J.2 | `czsc/traders/{base,cwc,rwc,optimize,weight_backtest,performance,dummy}.py` | `pytest test/` 仍 GREEN |
| J.3 | `czsc/py/` 目录 | `pytest test/` 仍 GREEN |
| J.4 | `czsc/features/` 目录 | `pytest test/` 仍 GREEN |
| J.5 | `czsc/utils/{bar_generator,bi_info,echarts_*,pdf_report,html_report_builder,word_writer,features,st_components,corr,signal_analyzer}.py` + `analysis/` 目录 | `pytest test/` 仍 GREEN |

每个 task 都 `Commit: chore: remove <files> (replaced by <equivalent>)`。

**Phase J 验证:**
- [ ] `find czsc -name '*.py' | xargs wc -l` 总行数 ≤ 12500（Q5 目标 ~12K）
- [ ] `pytest test/` 全过

---

## Phase K — CI / Trusted Publishing / finishing（1 天）

### Task K.1: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`

- [ ] CI: Rust（fmt / clippy -D warnings / test --workspace）+ Python（maturin develop + pytest + ruff + basedpyright）
- [ ] Release: maturin build wheel matrix（manylinux_2_28 linux + universal2 macos + windows）+ smoke + Trusted Publishing
- [ ] **Commit:** `ci: add Rust + Python pipelines and release workflow`

### Task K.2: Trusted Publishing OIDC binding

- [ ] 在 PyPI / TestPyPI 项目设置中绑定（仓库 + workflow + environment 三元组）
- [ ] 不在 GitHub Actions secrets 中存任何 PyPI token
- [ ] **Verify:** workflow 包含 `permissions: id-token: write` + `pypa/gh-action-pypi-publish@release/v1`（不带 token）

### Task K.3: 发 RC 至 test.pypi.org

- [ ] tag `1.0.0rc1`，触发 release workflow
- [ ] 干净 venv: `pip install --index-url https://test.pypi.org/simple/ czsc==1.0.0rc1`
- [ ] **Verify:** `pytest test/smoke/test_install.py -v` GREEN（A8）
- [ ] **Commit:** `chore: publish 1.0.0rc1 to test.pypi.org`

### Task K.4: finishing

- [ ] 用 `superpowers:finishing-a-development-branch` 合并 worktree → master
- [ ] 写 release notes（含 §6.T2 列出的所有破坏性变更 + 替代方案）
- [ ] tag `1.0.0`
- [ ] **Verify:** `pip install czsc` 后 `python -c "import czsc; czsc.CZSC"` 成功
- [ ] **Commit:** `release: 1.0.0 — Rust + PyO3 unified package`

**Phase K 验证:**
- [ ] Phase A 中 A8 由 RED 转 GREEN
- [ ] 全部 A1~A8 GREEN，pytest 100% PASS，cargo test 100% PASS

---

## 进度可视化

每次 commit 后，CI 跑 `scripts/red_green_report.py` 输出：

```
Phase A 基线: 56 项断言
当前: 红 X 项 / 绿 Y 项 / 总 56 项
本次 commit 影响: A3 +4 GREEN, A4 +2 GREEN
```

并写入 PR 描述的进度行，作为 plan 完成度的客观依据。

---

## 验收闭环

最终全部 task 完成后，要求满足：

- [ ] `cargo test --workspace` 100% PASS
- [ ] `pytest test/` 100% PASS
- [ ] `cargo clippy --all-targets -- -D warnings` 无 warning
- [ ] `cargo fmt --check` 通过
- [ ] `ruff check czsc test` 无 issue
- [ ] `basedpyright czsc` 无 error
- [ ] `pytest --cov=czsc` 公共 API 覆盖率 ≥ 90%，整体 ≥ 70%
- [ ] `find czsc -name '*.py' | xargs wc -l` ≤ 12500
- [ ] `grep -r "rs_czsc" examples/ docs/` 无结果
- [ ] `grep -r "CZSC_USE_PYTHON" czsc/` 无结果
- [ ] `pip install czsc==1.0.0` 后 `python -X importtime -c "import czsc"` import 时间 ≤ 300ms
- [ ] 10 万根 K 线 CZSC 完整分析 ≤ 200ms（M2 Mac）
- [ ] `MIGRATION_NOTES.md` §2.1 / §2.2 / §2.3 / §2.4 全部填好
