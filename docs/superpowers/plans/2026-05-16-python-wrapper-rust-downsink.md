# Python wrapper 下沉到 Rust 实施计划

> 源自飞书 wiki: https://s0cqcxuy3p.feishu.cn/wiki/WMfuwh5fPiz0cfkUN3hcqX1mn5f

**Goal:** 把 czsc Python 端的"参数适配/返回值转换"逻辑下沉到 Rust，让 `pip install czsc` 与 `cargo add czsc` 行为一致。

**Architecture:** 5 个独立 PR：PR-1 删 ta.py；PR-2 升级 Rust 信号 API；PR-3 Python 改纯透传（依赖 PR-2）；PR-4 Position serde 双形态；PR-5 版本号锁死。

**Tech Stack:** Rust workspace + PyO3 + maturin；Python ≥ 3.10；pytest；uv。

---

## PR-1：删除 czsc.utils.ta

### 改动文件清单
- 新增：`czsc/utils/plotting/_macd.py`（私有 MACD ×2 实现，仅 dashboard 内部使用）
- 修改：`czsc/utils/plotting/kline.py:243`（add_macd 改用 _macd）
- 修改：`czsc/utils/plotting/lightweight/_data.py:117-122`（_macd 改用新位置）
- 修改：`czsc/svc/strategy.py:45`（show_czsc_trader 改用 _macd）
- 修改：`docs/examples/03_kline_chart.py`、`10_streamlit_kline.py`、`11_streamlit_trader.py`：删除 `from czsc.utils.ta import MACD` 调用与 DIFF/DEA/MACD 列预计算（让 add_macd 自动算）
- 修改：`czsc/__init__.py:142`（移除 ta 注释，如还指向 utils.ta）
- 删除：`czsc/utils/ta.py`
- 修改：`tests/unit/test_ta_parity.py`（已是验证 czsc.ta 来自 Rust 的测试，更新过时引用注释）
- 修改：`CLAUDE.md`（去掉 ta.py 的描述）

### 步骤
1. 创建 `czsc/utils/plotting/_macd.py`，把 `EMA` / `MACD` 函数迁入并改为私有
2. 更新 3 个 plotting / svc 文件的 import
3. 更新 3 个 example，删除显式 MACD 调用
4. 删除 `czsc/utils/ta.py`
5. 运行 `uv run --no-sync ruff check czsc/ tests/` 和 `pytest`
6. 提交

---

## PR-2：Rust 信号 API 升级（核心）

### Rust 改动
- `crates/czsc-trader/src/sig_parse.rs`:
  - 新增 `get_signals_config_flat(unique_signals: &[&str]) -> Vec<HashMap<String, Value>>`：内置展平 params + 模块前缀剥离
  - 新增 `get_signals_freqs_from_strings(unique_signals: &[&str]) -> Vec<String>`：从原始字符串数组直接拿 freqs
- `crates/czsc-trader/src/signal_runtime.rs`（如不存在则新增）：`get_unique_signals(bars, signals_config) -> Vec<String>` 入口：对 bars 计算所有信号 → 提取 `<col>_<value>` 三段式 → 去重 → 过滤"其他"
- `crates/czsc-python/src/trader/api.rs`:
  - 升级 `derive_signals_config`：调用新的 `get_signals_config_flat`，返回平铺的 `list[dict]`，每个 dict 含 `name` / `freq` / 平铺参数；其中 `name` 已剥离模块前缀
  - 升级 `derive_signals_freqs`：检测入参类型；若 `list[str]`，调用 `get_signals_freqs_from_strings`；若 `list[dict]`，沿用原路径
  - 新增 `get_unique_signals`：bars + signals_config 入参，返回 `list[str]`；含 bars 长度 < 600 兜底
  - 新增 PyO3 export 在 `lib.rs`
- 重新生成 `czsc/_native/__init__.pyi`

### 验收
- Rust 单元测试：`cargo test -p czsc-trader sig_parse`
- Python 集成测试：`uv run --no-sync pytest tests/`

---

## PR-3：Python wrapper 改为纯透传（依赖 PR-2）

### 改动
- `czsc/traders/sig_parse.py`：删除 `get_signals_config` / `get_signals_freqs` 函数定义，改为 `from czsc._native import get_signals_config, get_signals_freqs` 透传（保留 docstring 简化）
- `czsc/traders/base.py`：删除 `get_unique_signals` 函数定义，改为 `from czsc._native import get_unique_signals`
- `czsc/traders/__init__.py`：保持公共导出不变（用户代码 `from czsc.traders import get_signals_config` 仍可用）

### 验收
- 用户代码 import 路径不变
- 单测 `tests/test_signals_*.py` 全绿

---

## PR-4：Rust Position dump 多形式字段

### Rust 改动
- 修改 `Position` / `Event` serde：让 `signals_all` / `signals_any` / `signals_not` 字段元素支持反序列化为 `String` 或 `{"key": str, "value": str}` 字典（用 `#[serde(untagged)]` enum 或自定义 deserializer）；序列化时统一输出字符串

### Python 改动
- 删除 `czsc/_runtime_adapters.py::position_dump_to_runtime`
- 删除 `czsc/_runtime_adapters.py::signal_config_to_runtime`（已被 PR-2 替代）
- 更新 `czsc/research.py:46-49,142-146,192-196` 删除对这两个函数的调用
- 更新 `czsc/strategies.py:37-40,108,197,244-245` 删除调用
- 更新 `czsc/traders/optimize.py:38-42,408,536` 删除调用
- 保留 `czsc/_runtime_adapters.py` 中 `bars_to_dataframe` / `sort_freqs` / `normalize_candidate_event(s)` / 内部辅助

### 验收
- Position 现有所有 dump/load 测试通过
- 从 JSON 加载策略的用户代码不变

---

## PR-5：版本号锁死

### 改动
- `crates/czsc-python/build.rs`：在编译期读取 `../../pyproject.toml`，校验 `CARGO_PKG_VERSION` 与 `dynamic = ["version"]` 一致（由于 pyproject.toml 用 dynamic version，已经从 Cargo 注入；这里只校验同步配置正确性）
- 当前实际：`pyproject.toml` 已用 `dynamic = ["version"]`，由 maturin 注入 Cargo workspace version；只需校验配置无回归
- 文档化：在 CLAUDE.md 补充"发版需同步 cargo publish + maturin publish"

---

## 最终验证
- `uv run --no-sync pytest` 全套通过
- `cargo test --workspace`
- `docs/examples/*.py` 在合适场景下能正常 import 与基础运行
