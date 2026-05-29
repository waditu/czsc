---
name: czsc-release
description: 规范 czsc 库（混合 Rust + Python，PyO3 + maturin）的版本发布流程。当用户说"发版/发布/release/publish czsc"、"bump 版本"、"出 rc.N+1"、"准备 1.0.0 stable"、要把 Rust crate 推 crates.io 或 wheel 推 PyPI 时使用。本 skill 半自动执行预检 / bump / CHANGELOG / commit，遇 push tag / push master / 真 publish 等不可逆动作时停下来要授权。
---

# CZSC Release Workflow

## 📋 Mandatory References（必读，且必须逐项核完才能进 Phase 3）

| 文件 | 角色 | 何时读 |
|---|---|---|
| **`docs/release_checklist.md`**（项目根目录，权威 214 行清单） | 9 节硬性检查清单 —— 含代码/文档一致性、SemVer 决策、本地 Rust/Python/Wheel 三层验证、发布动作顺序、发布后验证、隐藏缺陷雷达、一键自检脚本 | **Phase 0 一次性 Read 全文**；Phase 2 按 §3/§4/§5/§9 跑命令 |
| `references/release_checklist.md`（本目录） | 上述文件的 pointer（不存内容，避免漂移） | 仅供路径定位 |

**ratchet 规则**：本 skill 的 Phase 2 预检是 `docs/release_checklist.md` 的最小子集。完整清单**必须全部 ✅ 通过**才能进 Phase 3 bump 版本。任何一项 fail / 跳过 → 停下问用户，不要自己决定"这条不重要"。

## Overview

czsc 是 **Rust + Python 混合包**：

- crates.io 上发 6 个业务 crate（`czsc-derive`/`czsc-signal-macros` → `czsc-core` → `czsc-ta`/`czsc-utils` → `czsc-signals` → `czsc-trader` → `czsc` facade）
- PyPI 上发 1 个 wheel（`czsc`，扩展模块 `czsc._native` 由 `crates/czsc-python` 通过 maturin 编译）

两边**版本号必须严格一致**（宪法第一条 + PR-5）。**唯一版本源是 `Cargo.toml [workspace.package].version`**，pyproject.toml 用 `dynamic = ["version"]` 由 maturin 注入，`crates/czsc-python/build.rs` 在编译期 ratchet 禁止 pyproject.toml 硬编码 version。

发版**完全靠 GitHub Actions 自动化**：

| 触发 | Workflow | 行为 |
|---|---|---|
| `git push origin vX.Y.Z` | `.github/workflows/python-publish.yml` | 自动 build wheels + smoke + 推 PyPI（OIDC Trusted Publishing） |
| `git push origin vX.Y.Z` | `.github/workflows/rust-publish.yml` | 默认 **dry-run**；真 publish 需 workflow_dispatch + `do_publish=true` |

本 skill 的责任是**人手动做才不会错**的部分：版本决策、CHANGELOG 落档、预检、tag/push 时机、CI 监控、出错重发。

## What this skill does / doesn't do

| ✅ skill 替你做 | ❌ skill 不做 |
|---|---|
| 跑全套预检（fmt / clippy / pytest / maturin / stub） | 真按 PyPI 上传按钮（CI 干） |
| 推下一版本号（基于 CHANGELOG 推 SemVer） | 真按 crates.io publish（CI workflow_dispatch 干） |
| Bump `Cargo.toml` workspace version | 给 OIDC trusted publishing / CRATES_IO_TOKEN 配凭证（一次性人工事） |
| 把 CHANGELOG `[Unreleased]` 落档成 `[X.Y.Z] — YYYY-MM-DD` | `git push origin master`、`git tag`、`git push --tags`——这些都要**先停下来明确征求授权**，不可逆 |
| 提 `chore(release): bump X.Y.Z` commit | 跨语言 reviewer 工作（PR 评审走 requesting-code-review skill） |
| 监控 publish workflow 跑完，失败时进入重发剧本 | |

## Decision Tree

```
1. 当前在 master 上？working tree 干净？
   └─ 否：先 commit 完手头改动，merge 进 master 再 release。
        发版必须在 master 头部，避免分支漂移。

2. 现在该发什么版本号？
   ├─ 当前 rc 阶段（X.Y.Z-rc.N）
   │   ├─ 上轮 RC 已经 publish 到 PyPI/crates.io？
   │   │   ├─ 是：bump rc.N+1（哪怕只改了 docs，PyPI 版本号已占名不能复用）
   │   │   └─ 否（rc.N wheel 未上传 / crate 未发）：可以在 rc.N 上修问题、复用 rc.N
   │   └─ rc 期间累积满意，准备出第一个 stable：bump 到 X.Y.Z（去掉 -rc.N）
   ├─ stable 阶段（X.Y.Z）
   │   ├─ [Unreleased] 含 Breaking changes → bump X+1.0.0
   │   ├─ 仅 Added/Changed（无 breaking） → bump X.Y+1.0
   │   └─ 仅 Fixed/docs/internal     → bump X.Y.Z+1
   └─ 不确定 → 让 skill 推荐并问用户确认（永远先问，别猜）

3. 这次只发 Python 还是 Python + Rust 都发？
   ├─ 改了 Rust crate 公共 API → 两边都发
   ├─ 只改了 Python 端 facade / docs → 两边都发（版本号必须同步，不能 PyPI 走 1.0.1 而 crates.io 停 1.0.0）
   └─ 默认：两边都发（除非用户明确说 "skip rust" / "skip python"）
```

## Workflow

### Phase 0 — 准备（必做）

**0.0 强制读 release checklist 全文**：

```
Read /Users/lifanngzhou/git-repo/czsc/docs/release_checklist.md
```

读完后**列出 9 节标题**给用户看，明确告知"以下每一节都必须 ✅ 通过才能发版；本 skill 的 Phase 2 是 §3+§4+§5+§9 的最小子集，§1（代码/文档一致性）、§5（Linux aarch64/musllinux wheel 验证）、§7（发布后验证）等节本 skill 不能替代，你需要手动核完并告诉我结果"。

```bash
# 0.1 切到 master + pull 最新
git checkout master
git pull --ff-only origin master

# 0.2 working tree 干净
git status   # 必须 nothing to commit

# 0.3 距上一个 tag 至少有 1 个 commit（否则没东西可发）
git describe --tags --abbrev=0
git log $(git describe --tags --abbrev=0)..HEAD --oneline | wc -l   # > 0

# 0.4 CHANGELOG.md 的 [Unreleased] 非空
grep -A50 '^## \[Unreleased\]' CHANGELOG.md

# 0.5 release_checklist.md §1 代码/文档一致性（含 3 段 rg 命令）
#     —— 这一节本 skill 没复述，必须按 docs/release_checklist.md 跑
```

如果 [Unreleased] 是空的 → **停**，告诉用户："上一个 release 后没人写 CHANGELOG，发版前先补"，让用户决定补还是放弃。

如果 §1 的 `rg czsc.svc|czsc.signals.|streamlit|CZSC_USE_PYTHON|SignalsParser` 命中（说明 markdown 引用了已删除的 API）→ **停**，让用户先清理文档。

### Phase 1 — 推荐下一版本号

读 `Cargo.toml [workspace.package].version` 拿当前版本，读 CHANGELOG.md 的 `[Unreleased]` 块。

按 [Decision Tree](#decision-tree) 第 2 步推荐下一个版本号，并**用 AskUserQuestion 让用户确认**，给出推荐理由：

> 当前版本 1.0.0-rc.7。CHANGELOG [Unreleased] 含 Breaking changes（X 项）+ Added（Y 项）+ Fixed（Z 项）。
> 推荐 bump 到 **1.0.0-rc.8**（仍在 rc 阶段，rc.7 已发 PyPI 不能复用号）。
> 是否同意？

### Phase 2 — Pre-flight 预检（必跑全套）

这一节的 ratchet 都是 CHANGELOG 历史教训留下的，**不要跳任何一项**。

> **本节与 `docs/release_checklist.md` 的对应关系**：
> - 2.1 ↔ checklist §3（Rust 验证 + clippy）
> - 2.2 ↔ checklist §3（cargo test 的 5 crate 子集）
> - 2.3-2.4 ↔ checklist §3 最后一项（stub_gen + git diff ratchet）
> - 2.5-2.6 ↔ checklist §4（Python 验证 + `--run-slow`）
> - **未覆盖**：checklist §5（本地 wheel + Linux aarch64/musllinux docker 验证）—— 必须额外手跑
>
> 想一键跑完？用 checklist §9 的 bash 一键脚本（已串好 §3+§4 的全部命令）。

```bash
# 2.1 Rust 端格式 + clippy + 全 target typecheck（rc.3 教训：cargo check 不带 --all-targets 漏 test 模块）
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo check --workspace --all-targets

# 2.2 Rust 单元测试（不带 python feature，绕开 pyo3-stub-gen 上游兼容性问题）
cargo test --release -p czsc-core --lib

# 2.3 重编 .so 与最新源对齐
uv run --no-sync maturin develop --release

# 2.4 重生成 stub 并校验无 drift
PYO3_PYTHON=$(pwd)/.venv/bin/python3 cargo run --release --bin stub_gen -p czsc-python --no-default-features --features stub-gen
git diff --exit-code czsc/_native/__init__.pyi   # 必须 0 — stub 必须与 Rust 源一致

# 2.5 Python 端测试 + lint
uv run --no-sync pytest tests/unit tests/compat -q
uv run --no-sync ruff format --check czsc tests
uv run --no-sync ruff check czsc tests

# 2.6 慢测试（发版必跑，平时不跑）
uv run --no-sync pytest --run-slow -q
```

任何一步 fail → **停**，把失败摘要给用户，让用户决定修还是放弃发版。**不要在 fail 状态下继续 bump 版本号**——历史上 rc.2/3/4/5 重发都是因为预检不严，把已知错带上 CI。

### Phase 3 — Bump 版本 + 落 CHANGELOG（可逆，skill 直接做）

```bash
NEW_VER="1.0.0-rc.8"     # ← 来自 Phase 1 用户确认值
TODAY=$(date +%Y-%m-%d)
```

1. **改 `Cargo.toml`** 的 `[workspace.package] version = "..."`，**同时**把 `[workspace.dependencies]` 里所有 `czsc-* = { path = "...", version = "..." }` 的 version 字段都同步成新值（grep 出来一并改，否则 `cargo publish` 会拒绝）。
2. **跑一次 `cargo check --workspace`** 让 `crates/czsc-python/build.rs` 的 ratchet 重新校验 pyproject.toml 仍走 dynamic。
3. **CHANGELOG.md**：把 `## [Unreleased]` 改成 `## [NEW_VER] — TODAY`，并在它**上方插一个新的空 `[Unreleased]`** 块，结构如下：
   ```markdown
   ## [Unreleased]

   _（待填）_

   ---

   ## [1.0.0-rc.8] — 2026-05-29

   ### Added
   ...（搬下来的内容）
   ```
4. **再跑一次 maturin develop + 烟测**确认 bump 后 .so 还能装、`__version__` 正确：
   ```bash
   uv run --no-sync maturin develop --release
   uv run --no-sync python -c "import czsc; print(czsc.__version__)"   # 必须等于 NEW_VER 的 PEP440 形式
   ```
5. **提 commit**：
   ```bash
   git add Cargo.toml CHANGELOG.md
   # 如果 step 1 改到了 workspace.dependencies，那些也加
   git commit -m "chore(release): bump ${NEW_VER}"
   ```

### Phase 4 — 打 tag + push（不可逆，**必须先停下来征求授权**）

`git tag` 在本地是可逆的，但 `git push origin tag` **触发 CI** 是不可逆的（CI 会真上传 PyPI / 发 crates.io 真 publish）。所以：

**先用 AskUserQuestion 确认**，比如：

> Phase 3 完成。即将执行：
> 1. `git tag v1.0.0-rc.8` （本地）
> 2. `git push origin master` （推 release commit）
> 3. `git push origin v1.0.0-rc.8` （触发 python-publish 真上传 PyPI；rust-publish 默认 dry-run）
>
> 一旦推 tag 就**不能撤回**：PyPI 上的版本号占名后永远不能复用，要修问题只能 bump rc.9。
> 继续吗？

用户确认后：

```bash
git tag "v${NEW_VER}"           # SemVer 前缀必须是 v，CI 监听 v*
git push origin master           # 先推 commit 再推 tag，避免 CI checkout 不到 commit
git push origin "v${NEW_VER}"    # 这一行触发 python-publish + rust-publish
```

### Phase 4.5 — Push 之前最后一道 ratchet：checklist §1 / §5 / §6 是否手核完？

Phase 0 强制读了 `docs/release_checklist.md`。Phase 2 自动跑了 §3/§4/§9。但下面这些**本 skill 不能替你自动核**，push tag 之前必须确认用户已经手动完成：

- [ ] checklist **§1**（代码/文档一致性 —— 3 段 rg 命令均无输出 / `czsc.xxx` 引用都还存在 / 已退役关键字没残留）
- [ ] checklist **§5**（本地 wheel 构建 + 用 docker `--platform linux/arm64` 或 alpine 镜像验证 ARM/musllinux 加载成功）
- [ ] checklist **§6 step 1**（TestPyPI 演练 —— breaking 版本强烈建议）

**用 AskUserQuestion 把这三项列出来，明确询问"全部已完成？是 / 否 / 跳过 + 理由"**。任一项"否" → 拦下，告诉用户先核完再回来；"跳过" → 把理由记录在 release commit message 的 trailer 里（`Skipped-checklist-items: §5 (理由)`），future 复盘时能 trace。

### Phase 5 — 监控 CI（直到 publish 成功或失败）

```bash
gh run list --workflow=python-publish.yml --limit 3
gh run watch <run-id>     # 跟到 publish-to-pypi job 跑完
gh run list --workflow=rust-publish.yml --limit 3
```

需要看到：
- ✅ `python-publish.yml` 全绿 → PyPI 已发
- ✅ `rust-publish.yml` 在 tag push 触发下**只是 dry-run**（这是设计；要真 publish crates.io 需手动 workflow_dispatch）

如果 python-publish 失败 → 进入 [Phase 6 重发剧本](#phase-6--重发剧本)。

如果 python-publish 成功 → **告诉用户去手动触发 rust-publish.yml**：

```bash
gh workflow run rust-publish.yml -f do_publish=true -f start_layer=0 -f end_layer=5
gh run watch <run-id>
```

注意 crates.io rate-limit ≈ 1 个新 crate / 10 分钟。第一次发 czsc 系列新 crate 时，常常 layer 0/1 成功、layer 2 后被 rate-limit 拒；用 `start_layer` 参数从失败 layer 续发。

### Phase 5.5 — 发布后验证（checklist §7）

发布成功后**必须按 `docs/release_checklist.md` §7 逐项核完**：

- [ ] PyPI 页面 6 平台 + sdist 齐全
- [ ] crates.io 6 个 crate 都 OK（czsc-derive / czsc-signal-macros / czsc-core / czsc-ta / czsc-utils / czsc-signals / czsc-trader / czsc）
- [ ] GitHub Release 包含 wheel + sdist + sigstore 签名
- [ ] **干净环境冒烟（Python）**：用 `uv venv --seed`（带 pip）创建 tmp venv 后 `pip install czsc==<X.Y.Z>` + `python -c "import czsc; print(czsc.__version__)"`。⚠️ 不要在 czsc 仓库根目录跑 —— python path 会优先加载本地 czsc/ 路径而不是 PyPI wheel，给假阳性
- [ ] **`cargo add czsc@=<X.Y.Z>` 在干净项目 `cargo check` 真编通过**（不只是"可解析"！1.0.0-rc.8 实战教训：解析成功但 cargo check 失败）：
  ```bash
  TMPD=$(mktemp -d); cd "$TMPD"
  cargo init --name release_smoke --quiet
  cargo add 'czsc@=<X.Y.Z>' --quiet
  cargo check 2>&1 | tail -20      # 必须无 error
  cargo tree -i polars-core 2>&1   # 必须单一版本
  cd - && rm -rf "$TMPD"
  ```
  常见两类失败 → 见 [Phase 6 重发剧本](#phase-6--重发剧本) 后两行
- [ ] 至少跑一个 `docs/examples/` demo 确认无运行时回归

任一项失败 → 立刻在 GitHub Issue 记录、按 [Phase 6 重发剧本](#phase-6--重发剧本) 处理。**不要 yank 已上传的 X.Y.Z 版本本身**——版本号永久占名，必须 bump 下一个 patch/rc 重发。但**误发的混淆版本可以也应该 yank**（如 1.0.0 stable 与 1.0.0-rc.* 并存时 yank stable，避免 SemVer 解析坑）。

### Phase 6 — 重发剧本（出错后）

CHANGELOG 里 rc.2 → rc.3 → rc.4 → rc.5 是连续 4 次重发，写得很细。**主要坑**：

| 症状 | 根因 | 修法 |
|---|---|---|
| `python-publish` 在 "Verify version consistency" 失败 | SemVer 与 PEP440 不一致（如 `1.0.0-rc.4` ↔ `1.0.0rc4`），workflow 拿字符串硬比 | 这个 bug 已在 rc.5 修；新出现就检查 `packaging.version.canonicalize_version` 翻译是否还在 |
| build-wheels macOS 卡 1h+ | `macos-13` Intel runner pool 紧张 | 已切到 `macos-latest` cross-compile；不要回退 |
| aarch64 manylinux2014 编译 `ring` 失败 ARM assembler 报错 | manylinux 镜像 cross-gcc 没传 `__ARM_ARCH` | 已加 `CFLAGS_aarch64_unknown_linux_gnu="-D__ARM_ARCH=8"`；不要回退 |
| `cargo check` 本地过 CI 挂 | 本地没带 `--all-targets`，test 模块没被 typecheck | Phase 2.1 已强制 `--all-targets`；本地必跑 |
| `rust-publish` 中途断（rate-limit） | crates.io 新 crate ≈ 1/10min | `gh workflow run rust-publish.yml -f start_layer=N`，N 是失败 layer |
| **下游 `cargo add czsc@=<X.Y.Z>` 解析到错误 stable 版本**（rc.8 实战） | crates.io 同时有 `1.0.0` stable 与 `1.0.0-rc.*`；workspace.dependencies 写 `version = "<X.Y.Z>"` 不带 `=`，cargo 按 SemVer 选 stable（stable > prerelease） | (a) 紧急：`cargo yank --version 1.0.0 <crate>` × 8 个 czsc-* crate，强制下游解析跳过 stable；(b) 永久：把 workspace.dependencies 改 `version = "=<X.Y.Z>"` 严格匹配 + bump 下一个 rc 重发 |
| **下游 `cargo add` 编不出来 — pyo3 / pyo3-stub-gen / numpy 无条件依赖**（rc.8 实战） | czsc-core / czsc-utils / czsc-signals / czsc-trader 把 pyo3 系列列成无条件 dep，纯 Rust 用户也被强制拉 PyO3 工具链 | 4 个 crate Cargo.toml 把 pyo3 系列改 `optional = true` + 加 `[features] python = ["pyo3", "pyo3-stub-gen", "numpy", ...]`；facade czsc 默认 features 为空（纯 Rust）；bump 下一个 rc 重发；本地 `cargo check --no-default-features` 验证纯 Rust 路径 |

**安全 bump 规则**（rc.4 → rc.5 的教训）：

- 如果 wheel **build 成功但 publish step 没跑/失败**（PyPI 上没出现这个版本号）→ 同号修 + force-push tag 是**不允许**的（tag 已推过、CI 已跑过、commit 已上 master）。**只能 bump 下一个 rc 号**，把修复打进新版本。
- 检查 PyPI 是否已经收到：`pip index versions czsc` 或 https://pypi.org/project/czsc/#history
- 检查 crates.io：`cargo search czsc-core --limit 1`

## 关键文件参考

| 文件 | 角色 |
|---|---|
| **`docs/release_checklist.md`** | **权威清单（必读）**，9 节 / 214 行，本 skill 是它的可执行子集；详见顶部 [Mandatory References](#-mandatory-references必读且必须逐项核完才能进-phase-3) |
| `Cargo.toml` (workspace root) | 唯一版本源 `[workspace.package].version` |
| `pyproject.toml` | 必须 `dynamic = ["version"]`，禁止硬编码版本（`build.rs` ratchet 拦） |
| `CHANGELOG.md` | Keep a Changelog 格式，`[Unreleased]` → `[X.Y.Z] — YYYY-MM-DD` |
| `.github/workflows/python-publish.yml` | tag `v*` 触发，wheels + smoke + PyPI |
| `.github/workflows/rust-publish.yml` | tag `v*` 触发 dry-run；workflow_dispatch + `do_publish=true` 真发 |
| `crates/czsc-python/build.rs` | 编译期 ratchet：pyproject.toml 不能硬编码 version |
| `czsc/__init__.py` | `__version__ = importlib.metadata.version("czsc")` 反查 |

## 触发场景速查

下面这些用户表达**都应该启用本 skill**：

- "发版 czsc rc.N"、"出 rc.N+1"、"准备 1.0.0 stable"
- "bump 版本号"、"bump 到 X.Y.Z"
- "release"、"publish czsc"、"推 PyPI"、"发 crates.io"
- "CHANGELOG [Unreleased] 落档"
- "tag vX.Y.Z"、"打 release tag"
- "上次 publish 失败，重发"、"rc 重发"

## 不要做的事

- ❌ **不要跳过 `docs/release_checklist.md` 的任何一节**——Phase 0 必须 Read 全文，Phase 2 跑 §3+§4+§9 子集，Phase 4.5 显式核 §1+§5+§6 step 1，Phase 5.5 核 §7。任一节"省略"都属违规
- ❌ 不要在 fail 状态下跳过 Phase 2 预检——历史 4 次重发都是这么开始的
- ❌ 不要替用户跑 `git push origin <tag>`——必须 AskUserQuestion 后再做
- ❌ 不要为了"快"在 rc 期间 force-push 同号 tag——PyPI/crates.io 版本号占名后永久不能复用
- ❌ 不要在 pyproject.toml 里写死 `version = "X.Y.Z"`——会被 build.rs 编译期拦下
- ❌ 不要只 bump `[workspace.package].version` 而漏掉 `[workspace.dependencies]` 里 czsc-* 的 version 字段——`cargo publish` 会拒绝
- ❌ 不要在 master 之外的分支打 release tag——CI checkout 的是 tag 指向的 commit，但 master 历史会缺失
