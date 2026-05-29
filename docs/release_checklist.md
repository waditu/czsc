# 版本发布前的检查清单

> 适用范围：czsc（Python wheel via PyPI + Rust crates via crates.io，共用 git tag `v<X.Y.Z>`）。
> 目的：在 push tag 之前堵住 **CI 覆盖不到的质量风险与隐藏缺陷**。
> CI 已强制项（版本一致性、stub 漂移、ruff/cargo fmt、clippy `-D warnings`、py3.10–3.13 pytest）不在本清单重复。

---

## 1. 代码冻结前（提交期）

- [ ] **所有面向用户的 PR 已合并、关闭或显式延期**；`master` 当前 commit 即是要发布的内容
- [ ] **CHANGELOG 已更新**：列出本次 release 的 breaking changes、新增 API、修复项；Rust 端如有签名变更必须显式标出
- [ ] **公开 API 改名/删除已有迁移说明**：放在 `docs/migration/` 或 CHANGELOG，避免下游升级炸裂

### 代码 vs Markdown 文档一致性（硬性检查）

**原则：以代码为准。**任何不一致都改文档，**不要**反向去改代码迁就文档措辞。

检查范围与方法：

- [ ] **`README.md`**：安装命令、最小示例、API 调用片段、特性列表都能跑通；版本徽章/截图同步
- [ ] **`CLAUDE.md`**：模块路径、已删除/重命名的符号、目录结构描述、引用的环境变量名（如 `CZSC_USE_PYTHON` 等是否已退役）
- [ ] **`docs/examples/*.py`**：每个示例真实可运行（至少 `python -c` import 不报错）；删除的示例同步从 `docs/examples.md` 索引里删掉
- [ ] **`docs/migration/`**：历史迁移说明里引用的旧 API/路径，与当前实际"已删除/已改名"的事实对齐
- [ ] **公开 docstring**：`czsc/` 顶层导出对象、`crates/*/src/lib.rs` 公开 item 的 docstring 中的代码示例可执行
- [ ] **API 文档（飞书 / readthedocs）链接的有效性**：本次若有大规模重构，外链文档需手动确认未误导

快速定位漂移点的命令：

```bash
# 1) 找 md 里引用的 czsc.xxx 符号，对照实际是否存在
rg -n 'czsc\.[a-zA-Z_][a-zA-Z0-9_.]*' README.md CLAUDE.md docs/ \
   | awk -F'czsc\\.' '{print $2}' | awk '{print $1}' | sort -u \
   > /tmp/md_refs.txt
uv run python -c "
import czsc, sys
refs = [l.strip().rstrip('.,)`\"') for l in open('/tmp/md_refs.txt') if l.strip()]
for r in refs:
    root = r.split('.')[0].rstrip('()')
    if root and not hasattr(czsc, root):
        print('MISSING in czsc:', r)
"

# 2) 找 md 里残留的"已被删掉"的关键字（按本仓库历史踩坑点扩充）
rg -n 'czsc\.svc|czsc\.signals\.|streamlit|CZSC_USE_PYTHON|SignalsParser|czsc\.core\b' \
   README.md CLAUDE.md docs/ \
   && echo "::error:: 上述命中均为已删除/已退役项，需从文档中清理"

# 3) 找 md 里引用的文件路径是否仍存在
rg -nIo '[a-zA-Z0-9_/.-]+\.(py|rs|toml|md)\b' README.md CLAUDE.md docs/ \
   | awk -F: '{print $NF}' | sort -u \
   | while read p; do [ -e "$p" ] || echo "MISSING path: $p"; done
```

- [ ] 以上三段命令均无输出（或所有命中都已修正）
- [ ] **`docs/examples/` 与 `docs/examples.md` 索引一致**：文件删除/新增都同步索引

---

## 2. 版本号（单一版本源 = `Cargo.toml [workspace.package].version`）

- [ ] `Cargo.toml [workspace.package].version` 已 bump 到目标版本
- [ ] **未硬编码** `pyproject.toml` 的 `version`，仍为 `dynamic = ["version"]`（硬编码会被 `crates/czsc-python/build.rs` 编译期拒绝）
- [ ] 计划打的 git tag 是 `v<Cargo.toml version>`（CI 会做三方校验：tag == Cargo == wheel filename）

### 语义化版本（SemVer）规则

格式：`MAJOR.MINOR.PATCH`（如 `1.2.3`），三段含义对应"兼容性合同"：

| 段位 | 何时 +1 | 典型场景 | 同时清零 |
|---|---|---|---|
| **MAJOR** | 破坏向后兼容 | 删除/重命名公开 API、改函数签名、改字段语义、调整信号默认参数、Rust 类型签名变更 | MINOR、PATCH → 0 |
| **MINOR** | 向后兼容地新增 | 新信号函数、新公开 API、新可选参数、新示例 | PATCH → 0 |
| **PATCH** | 向后兼容地修 bug | 算法修正、性能优化、文档/类型提示修正、内部重构（不影响外部行为） | — |

判定决策树：

1. 用户**升级后会报错或行为变化**吗？→ **MAJOR**
2. 用户能**用上新东西**且老代码不动也跑得通吗？→ **MINOR**
3. 只是**修了已有功能的 bug**，外部接口与行为不变？→ **PATCH**

补充约束：

- [ ] **任意 breaking change**（即使再小）必须 bump MAJOR，且在 CHANGELOG 顶部用 `### Breaking Changes` 单独成段
- [ ] **不允许"小版本里夹 breaking"**——这是下游升级最容易翻车的反模式
- [ ] **预发布**用 `1.2.0-rc.1` / `1.2.0-beta.1`（PyPI 与 crates.io 都支持），tag 同步打 `v1.2.0-rc.1`
- [ ] **`0.x.y` 阶段**（如果未来有）：MINOR 段位的语义可视作 MAJOR——即 `0.3.0 → 0.4.0` 允许带 breaking；本项目当前已稳定在 `1.x`，不适用
- [ ] **Rust crates 与 Python wheel 共享同一版本号**（已由 CI 强校验），不允许某一侧单独 bump

---

## 3. 本地 Rust 验证（CI 覆盖盲点）

CI 因 `pyo3/extension-module` 限制，只对 5 个纯 Rust crate 跑 `cargo test`。`czsc-signals` / `czsc-trader` / `czsc-python` 的 Rust 测试**只能本地跑**：

- [ ] `cargo build --workspace --release` 通过
- [ ] `cargo test -p czsc-derive -p czsc-core -p czsc-utils -p czsc-ta -p czsc-signal-macros` 通过（与 CI 同步）
- [ ] `cargo clippy --workspace --all-targets -- -D warnings` 通过
- [ ] `cargo fmt --all -- --check` 通过
- [ ] **stub 已重新生成并 commit**：
  ```bash
  PYO3_PYTHON=$(uv run python -c 'import sys; print(sys.executable)') \
    cargo run --bin stub_gen -p czsc-python --no-default-features --features stub-gen
  git diff --exit-code czsc/_native/__init__.pyi   # 必须无差异
  ```

---

## 4. 本地 Python 验证

- [ ] `uv sync --extra all`（仅在依赖变更后跑一次）+ `uv run maturin develop --release` 构建本地扩展
- [ ] **全量测试含 slow 用例**（CI 默认跳过 `@pytest.mark.slow`，发布前必须显式跑）：
  ```bash
  uv run --no-sync pytest --run-slow
  ```
- [ ] `uv run --no-sync pytest --cov=czsc` 覆盖率无显著回退
- [ ] `uv run --no-sync ruff format --check czsc/ tests/` & `uv run --no-sync ruff check czsc/ tests/` 通过
- [ ] **冒烟 import 顺序无 side-effect**：
  ```bash
  uv run python -c "import czsc; print(czsc.__version__)"
  uv run python -c "from czsc import CZSC, RawBar, Freq, BarGenerator, CzscTrader; print('core OK')"
  uv run python -c "from czsc._native import signals; print(len(dir(signals)))"
  uv run python -c "from czsc._native import ta; print(sorted(dir(ta))[:5])"
  ```
- [ ] `czsc.__version__` 输出 == 目标版本（验证 `importlib.metadata` 注入正确）

---

## 5. 本地 Wheel 验证（覆盖 CI smoke 盲区）

CI smoke 仅覆盖 Linux x86_64 / macOS x86_64 / macOS arm64 / Windows x64。**Linux aarch64 与 musllinux 必须本地验证**：

- [ ] `uv run maturin build --release --strip` 产物可被 `pip install --no-deps` 安装并 `import czsc` 成功
- [ ] 如本次有触及 PyO3 边界（参数 / 返回值序列化、Arrow IPC、GIL release）：用 docker `--platform linux/arm64` 或 alpine 镜像本地拉一遍 wheel 安装 + import
- [ ] Wheel 文件名版本符合 `czsc-<X.Y.Z>-cp310-abi3-<plat>.whl`（abi3 单 wheel 覆盖 3.10–3.13）

---

## 6. 发布动作（按顺序）

> 任何一步失败都**先排查再前进**，不要靠重发覆盖。tag 一旦发布到 PyPI 不可重用。

1. [ ] **TestPyPI 演练**（强烈推荐，尤其是 breaking 版本）：
   - Actions → `Build & Publish Python Package` → `workflow_dispatch` → `publish_to_testpypi=true`
   - 在干净虚拟环境 `pip install -i https://test.pypi.org/simple/ czsc==<X.Y.Z>` 实测
2. [ ] **Rust crates dry-run**（push tag 时自动跑，可提前 workflow_dispatch 验证）：
   - Actions → `Publish Rust crates` → 默认 dry-run；查看日志确认 `cargo publish --workspace --dry-run` 通过
3. [ ] **Push tag** 触发 PyPI 真发：
   ```bash
   git tag v<X.Y.Z>
   git push origin v<X.Y.Z>
   ```
   - CI 自动：build wheels → sdist → smoke-test → 版本三方校验 → PyPI 发布 → GitHub Release + sigstore 签名
4. [ ] **Rust crates 真发**：tag push **不会自动真发**，需手动：
   - Actions → `Publish Rust crates` → `workflow_dispatch` → `do_publish=true`
   - 若中途撞 crates.io rate-limit（新 crate ~1/10min），用 `start_layer` / `end_layer` 断点续发
5. [ ] PyPI 与 crates.io 任一发布失败 → **不要急着 yank**，先在 Issue 记录、修复后 bump 一个 patch 版本重发（已上传不可覆盖）

---

## 7. 发布后验证

- [ ] PyPI 页面可见目标版本，wheel 平台齐全（6 平台 + sdist）：https://pypi.org/project/czsc/
- [ ] crates.io 页面可见目标版本，全部 6 个 crate 都 OK（czsc-derive / czsc-signal-macros / czsc-core / czsc-ta / czsc-utils / czsc-signals / czsc-trader / czsc）
- [ ] GitHub Release 已创建，包含 wheel + sdist + sigstore 签名文件
- [ ] 干净环境冒烟：
  ```bash
  pip install czsc==<X.Y.Z>
  python -c "import czsc; print(czsc.__version__)"
  ```
- [ ] `cargo add czsc@<X.Y.Z>` 在干净 Rust 项目中可解析
- [ ] 至少跑一个最小 CZSC + 信号配置的 demo（如 `docs/examples/13_lightweight_charts_html.py`）确认运行时无回归

---

## 8. 隐藏缺陷雷达（按历史踩坑频度排序）

| 风险 | 触发条件 | 防御 |
|---|---|---|
| Stub 漂移 | 改了 `#[gen_stub_*]` 但忘了重跑 stub_gen | §3 最后一项 + CI `stub-drift` job |
| 版本三方不一致 | 只 bump 了 Cargo 没 push tag、或反之 | §2 + CI `verify_version_consistency` |
| `pyproject.toml` 误改 `version` | 手抖去掉 `dynamic` | `build.rs` 编译期校验 |
| Slow 测试漏跑 | 平时 CI 不跑 `--run-slow` | §4 强制本地跑 |
| `czsc-signals` / `czsc-trader` Rust 端回归 | CI 不能 `cargo test` 这两个 crate | §3 + Python pytest 端到端覆盖 |
| ARM/musllinux wheel 加载失败 | CI smoke 不覆盖 | §5 本地 docker 验证 |
| Rust crates 漏发 | tag push 只触发 dry-run，真发要手动 dispatch | §6 step 4 强提醒 |
| crates.io rate-limit | 新 crate 创建 ~1/10min | `start_layer`/`end_layer` 断点续发 |
| PyPI 已存在版本无法覆盖 | 发布失败后误以为可重发 | §6 step 5：bump patch 重发，不要 yank |
| 下游升级炸裂 | breaking change 没写迁移说明 | §1 CHANGELOG + `docs/migration/` |

---

## 9. 一键自检脚本（可选）

把 §3 + §4 + §5 的本地命令串成一个脚本，在 push tag 前跑一遍：

```bash
set -e
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo build --workspace --release
cargo test -p czsc-derive -p czsc-core -p czsc-utils -p czsc-ta -p czsc-signal-macros
PYO3_PYTHON=$(uv run python -c 'import sys; print(sys.executable)') \
  cargo run --bin stub_gen -p czsc-python --no-default-features --features stub-gen
git diff --exit-code czsc/_native/__init__.pyi
uv run maturin develop --release
uv run --no-sync ruff format --check czsc/ tests/
uv run --no-sync ruff check czsc/ tests/
uv run --no-sync pytest --run-slow
uv run python -c "import czsc; print('version:', czsc.__version__)"
echo "✅ 本地预检全部通过"
```

> 全绿之后再做 §6 的发布动作。
