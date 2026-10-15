# 1.0.2 发布审核补证

## 当前版本与验收边界（2026-10-15）

维护者明确选择 1.0.2，保留 #368 的 34 项输出键迁移及新键契约，不增加别名或双协议，
不再推进兼容改造或 2.0.0 发布。CHANGELOG 保留破坏性警告；该范围决定不是合并、tag 或上传授权。
版本源、八个内部精确约束和九个工作区锁包必须统一 1.0.2，Python 版本仍由 maturin 动态读取。
`uv.lock` 的项目为 dynamic/editable，没有待替换的项目版本；第三方包的 2.0.0 不是项目版本。

```bash
REPO_ROOT="$PWD"
python -m pytest tests/test_release_dependencies.py .github/scripts/tests/test_release_wheel_smoke.py -q
uvx maturin build --release --locked --offline --interpreter "$PYTHON" --out target/release-1.0.2-dist
uvx maturin sdist --out target/release-1.0.2-dist
mkdir -p target/release-1.0.2-smoke-cwd
(cd target/release-1.0.2-smoke-cwd && "$PYTHON" "$REPO_ROOT/.github/scripts/smoke_release_wheel.py" \
  --expected-version 1.0.2 --expected-machine arm64 --wheel-dir "$REPO_ROOT/target/release-1.0.2-dist")
```

构建后必须在新 venv 完整安装实际 1.0.2 wheel，并在仓库外运行 smoke；上面的 `$PYTHON` 对安装和
检查命令应指向该环境，不能从源码目录导入旧 native 冒充新产物。检查版本/架构/来源/native 字节、
RawBar/CZSC、SMA、八个时间精度组合及实际新信号键/配置往返、旧键拒绝，不放宽原功能门禁。
原六平台 × Python 3.10–3.13 的 24 组合保持完整在线/no-cache 安装、pip check 和所有上传 needs；
只无上传演练 `publish_to_testpypi=false`，新 producer SHA/产物哈希及一次执行快照随任务评论交付，
没有结果的项目明确未验证，不轮询等待外部 CI。

## 历史 2.0.0 候选记录（以下至文末均非新版本通过证明）

下文保留此前源码、命令、版本、文件名、哈希及局部运行缺口的原貌，不改名复用历史产物。
其后独立复审已验收 `eeeb731` / run 38615098709 的六平台与 24/24 组合，三个上传 job 均 skipped；
该结论只属于原 2.0.0 产物。未变化的算法/安全图证据可按边界保留，不能替代 1.0.2 的重建和运行。

本次验证对应 PR #369 的审核修复内容，不等于发布批准。版本源仍为 Cargo workspace；正式版/RC、范围和上传授权未确认。禁止把以下本地通过替代六平台产物、线上 registry 安装或上传权限证据。

## 修复与可复现回归

- 时间精度：输入/merge 键/输出统一 `datetime64[ns]`，覆盖 s/ms/us/ns 和交易日/自然日。没有改笔/分型算法。
- 测试隔离：测试包导入不再写进程配置；默认值测试的环境清理通过 monkeypatch 恢复。没有调整收集顺序、刷新快照或为通过而设置笔长 6。
- 安全处置：30 项逐项见 `release_security_review.md`；版本阈值与普通安装 urllib3 下限有防回退守卫。
- 红灯证据：初始组合 11 failed / 6 passed，锁版本守卫 12 failed；环境恢复测试 1 failed、urllib3 安装下限测试 1 failed。
- 绿灯证据：首组修复 45 passed；原样核心/环境/安全组合两种顺序各 37 passed。顺序变换只用于证明隔离，不是修复手段。

```bash
PYTHON=.venv/bin/python
"$PYTHON" -m pytest tests/unit/test_core_parity.py -q
"$PYTHON" -m pytest tests/test_testing_configuration.py tests/test_release_dependencies.py \
  tests/unit/test_core_parity.py tests/test_envs.py -q
"$PYTHON" -m pytest tests/test_envs.py tests/unit/test_core_parity.py \
  tests/test_release_dependencies.py tests/test_testing_configuration.py -q
"$PYTHON" -m pytest tests/test_trade_utils.py tests/unit/test_resample_bars.py -q
```

分别使用 pandas 2.3.2 与 pandas 3.0.6 的 Python 3.11.15 环境，不把降级 pandas 当作修复。两套完整回归均为 **546 passed / 1 deselected**（分别 18.00s / 27.38s），执行命令如下；数量有交叉，不累加：

```bash
"$PYTHON" -m pytest tests --run-slow --import-mode=importlib \
  -k 'not test_wheel_install_in_clean_venv' -q
```

唯一未执行项是在线 pip clean-install 测试；独立环境离线安装、native import、依赖检查另行取证，不把离线安装等同在线无约束 resolver 验证。pandas 2 环境检查 53 个包、pandas 3 环境检查 41 个包，均报告 `All installed packages are compatible`。完整新 wheel 的本地结果和 SHA256 以本轮交付日志为准。

## 构建、typing 和 Rust 产物

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --exclude czsc-python --locked
PYO3_PYTHON="$("$PYTHON" -c 'import sys; print(sys.executable)')" \
  cargo test -p czsc-core --features python --test test_python_enum_extraction --locked
PYO3_PYTHON="$("$PYTHON" -c 'import sys; print(sys.executable)')" \
  cargo run --locked --bin stub_gen -p czsc-python --no-default-features --features stub-gen
git diff --exit-code -- czsc/_native/__init__.pyi tests/unit/snapshots/
uvx maturin build --release --locked --interpreter "$PYTHON"
uvx maturin sdist --out dist
cargo package --workspace --exclude czsc-python --allow-dirty --locked --offline
```

- 已验证 Rust 273 passed / 1 ignored，额外 Python enum 提取契约 2 passed；fmt/Clippy 通过。
- 新 stub generator 已执行，stub 与原提交字节一致。debug stub_gen 的 macOS 链接器报告 `__eh_frame` 超过 compact unwind 16MB 限制；没有屏蔽告警，异常展开性能未测，不能将其称为 release 运行失败或宣称性能无影响。
- 八个可发布 crate 均实际 `Packaged` 和 `Verifying` 成功；没有使用 `--no-verify`，不只编译 workspace path 依赖。Cargo 在本地临时 registry 中解析本次 `=2.0.0` 依赖。
- 额外纯 Rust 消费者使用 `czsc = "=2.0.0"`，无 path dependency、无 `[patch]`、无 Python feature。将八个 `.crate` 与 `cargo vendor --locked --offline --versioned-dirs` 的第三方源放入隔离 source mirror，生成 archive/file SHA256 校验后，`cargo run --offline` 成功，`czsc::Freq::F1` 实际运行；normal tree 没有 pyo3/numpy。
- 此消费者验证的是本次归档在离线镜像里的行为，**不是正式 crates.io 安装**；2.0.0 尚未上传，不能制造线上验证证据。

## Wheel 内容与独立环境验证

```bash
"$PYTHON" - <<'PY'
from pathlib import Path
from zipfile import ZipFile
from email import message_from_bytes
import hashlib
wheels = list(Path('dist').glob('czsc-*.whl'))
assert wheels, 'No release wheel found'
for wheel in wheels:
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = message_from_bytes(archive.read(next(name for name in names if name.endswith('/METADATA'))))
        assert metadata['Version'] == '2.0.0'
        assert 'urllib3>=2.8.0' in metadata.get_all('Requires-Dist', [])
        payload = [name for name in names if name.startswith('czsc/') and name.endswith(('.py', '.pyi', 'py.typed'))]
        assert all(archive.read(name) == Path(name).read_bytes() for name in payload)
        assert any(name.startswith('czsc/_native') and name.endswith(('.so', '.pyd')) for name in names)
        assert 'czsc/py.typed' in names and 'czsc/_native/__init__.pyi' in names
        assert any(name.endswith('/LICENSE') for name in names)
        print(wheel.name, len(payload), hashlib.sha256(wheel.read_bytes()).hexdigest())
PY
```

普通安装与本地源测试是两种证据。先在全新 venv 安装完整依赖快照与新 wheel，在非仓库目录执行 native import 和 `uv pip check`，再执行对应环境的 pandas 回归；避免从仓库导入旧 `.so` 冒充新产物。

本轮重新构建的 `czsc-2.0.0-cp310-abi3-macosx_11_0_arm64.whl` SHA256 为 `93b89636192d89a3dcb49fce6f4bdf6fa22ccddfa603f4d2fa278a8ed25d180f`；97 个 Python/stub/typing payload 与修复源码逐字节一致。native 使用升级后的 PyO3/NumPy 重新编译，不复用审核前产物。wheel 在修复提交前的 worktree 构建，源码一致性已验证，但不能将其描述为 CI 的 clean-checkout 产物。

在线无约束 pip resolver 与所有 Python/平台组合尚不能由离线依赖快照证明。原 `test_wheel_install_in_clean_venv` 的在线安装项若未执行，必须明确列出，不得把 deselected 写成 passed。

## 未验证门禁（不得标绿）

| 项目 | 本次证据 / 剩余动作 |
| --- | --- |
| macOS arm64 / Python 3.11 | 本机 release wheel、metadata/源码/stub/native 与独立环境验证；详见本轮日志 |
| Linux x86_64、Linux arm64、musllinux、macOS Intel、Windows wheel | 本机未验证；需收集同一 head 的六平台 workflow 产物与真实运行环境 smoke |
| Python 3.10/3.12/3.13 | 本机未重新运行；PR CI 是开发构建回归，不能替代对应 release wheel 验证 |
| ARM/musllinux/macOS Intel import smoke | 已给现有 workflow 增加原生 ARM/Intel runner 与 Alpine 运行检查；配置不等于执行通过，本机 Docker daemon 不可用，结果仍须单独收集 |
| 官方 crates.io 下游解析/安装 | 未发布，尚不可验证；离线镜像验证不是线上证据 |
| PyPI Trusted Publisher / crates.io token | 仅知道 repo environment / secret 名存在，未验证有效性，不读取 secret 值 |
| TestPyPI/正式上传与发布后验收 | 无授权，未触发；正式版/RC 和范围须维护者确认 |

安全构建演练可以在同一新 head 的分支上使用现有 workflow 的 `publish_to_testpypi=false`；它仅构建与测试，上传 job 条件不成立，仍必须核对 run 输入/事件与结果：

```bash
gh workflow run python-publish.yml --repo waditu/czsc \
  --ref agent/codex/SKZ-964-release-2.0.0 -f publish_to_testpypi=false
```

不要改成 true 或推 v* tag 来获取证据：前者会上传 TestPyPI，后者会自动上传正式 PyPI。Rust 真正发布需要授权后在同一 tag dispatch `do_publish=true`。本任务不合并、不打 tag、不上传包。

## 补充 release wheel 运行检查

现有 `python-publish.yml` 的 smoke 已扩展至六个平台 × Python 3.10/3.11/3.12/3.13（24 个组合），不是重新运行全套算法回归：

- manylinux x86_64、aarch64 分别在 x86_64、`ubuntu-24.04-arm` 原生 runner 执行；macOS Intel 在 `macos-15-intel`，arm64 在 Apple Silicon，Windows 在 x64 runner 执行。
- musllinux x86_64 在对应 Python 版本的 Alpine Docker 环境执行，不能用 glibc Linux 或交叉编译结果替代实际加载。
- 每个组合创建新 venv，从公开 PyPI 在线解析完整运行时依赖，安装同一 run 的 release wheel，执行 `pip check`；取消原最小依赖/no-deps smoke。依赖若缺少该平台发行包或编译环境，必须失败并记录，不能跳过依赖伪装普通安装成功。
- 在仓库之外执行 `.github/scripts/smoke_release_wheel.py`；校验版本、runner 架构、模块属于目标 venv、native 二进制与下载 wheel 字节一致，并实际运行 RawBar/CZSC、Rust SMA 和八种时间精度组合。
- 两个 smoke job 仅有 contents/actions read 权限，没有上传步骤或 OIDC write。原 PyPI/TestPyPI 上传条件不变，两个上传 job 新增 musl smoke 为依赖；演练必须继续显式 `publish_to_testpypi=false`。
- 新脚本与门禁回归使用独立安装环境执行：`python -m pytest .github/scripts/tests/test_release_wheel_smoke.py -q`。原始红灯 5 failed，修复后 5 passed。此工具回归不混入先前 546 项算法回归计数。

当前配置的静态检查、本机在线安装与实际 CI wheel 执行日志随任务评论交付。远程 24 组合是否通过只能由新 head 的 job 执行结果证明；dispatch 成功或 queued 不算运行通过。未完成时只记录快照，不轮询等待外部 CI，也不申请发布批准。

## Windows 编码与 musl 安装环境补证（2026-10-15）

### 已完成演练的实际结果

[run 38607249078](https://github.com/waditu/czsc/actions/runs/38607249078) 对应
`bba2c0802931db51c43e523c19d2ee33f6ab4a7c`，已结束且失败，不是仍在等待。
六个平台 wheel 和 sdist 构建成功；24 个运行组合为 **16 success / 8 failure**。
manylinux x86_64/aarch64、macOS Intel/arm64 的 Python 3.10–3.13 全部完成完整在线无缓存安装、
`pip check` 和 wheel/native/功能检查。Windows 四组合在 Cargo 版本读取阶段失败；
musl 四组合在 wbt 源包的构建准备阶段失败，均尚未执行 native smoke。
PyPI、TestPyPI、GitHub Release 三个 job 均 skipped。该远程证据更新前文的本地未验证记录，
但不把历史产物或旧 SHA 的结果改写成修复 head 的结果。

### 最小修复与回归

- 两个 smoke 版本命令显式使用 UTF-8 读取 Cargo.toml；不设置全局 UTF-8/locale 环境绕开缺陷。
  参数化回归直接执行 workflow 中的两个真实 Python 命令，在默认编码 cp1252 下先复现
  `UnicodeDecodeError`（2 failed），然后验证显式 UTF-8（2 passed）。
- musl 容器在创建新 venv 前安装 `build-base libgcc libstdc++ rustup pkgconf openssl-dev`，
  用 `rustup-init -y --profile minimal --default-toolchain stable` 显式准备 musl Rust 工具链，
  把 `$HOME/.cargo/bin` 加入 PATH，并打印 Alpine、APK、rustc 和 Cargo 版本。
  不再依赖 Python 构建后端隐式安装 Rust；仅补 libgcc 不足以构建 wbt。
- 以 `CARGO_BUILD_JOBS=2` 限制源码编译并行度，musl job 预算由 20 分钟改为 60 分钟，
  为 Polars 及 wbt 的 release 编译预留资源。这不是运行成功证明，仍可能内存不足或超时。
  不改变 wbt 的 LTO/profile，不更改 Python 依赖约束，不跳过完整安装，不删除平台或放宽上传 needs。
- 环境配置回归先因缺少 APK 前置安装失败（1 failed），补齐后通过；8 项工具回归包含
  编码、环境顺序、原完整安装/上传约束和本地既有已安装 wheel 的正反例。
  静态配置断言不能代替真正的 Alpine 编译、在线依赖解析及 native 加载。

### runner 补齐与用户分发要求不同

核对公开 PyPI 的 wbt 0.9.2 文件清单及校验 SHA256 的 sdist：目前无 musllinux wheel，
sdist 使用 maturin、Rust edition 2024、PyO3 0.28 与 Polars 0.53，Cargo.lock 无 git source。
所以普通 Alpine 完整安装会构建 wbt 源包，需要可用的 Rust/C/C++ 工具链、头文件、链接器、
运行库、网络以及足够 CPU/内存/时间；CZSC 的 abi3 musllinux wheel 本身不提供这些依赖。
APK 的 rustup 包提供 rustup-init 并依赖 libgcc，可由
[Alpine 包清单](https://pkgs.alpinelinux.org/package/v3.23/community/x86_64/rustup) 核对。
容器日志中的实际 Alpine/工具链版本才是本次执行环境，不假定浮动标签永远不变。

不能把 PyArrow 一概归为源码构建阻塞：本次 PyPI 清单中，25.0.1 有 Python 3.10 的
musllinux_1_2_x86_64 wheel，26.0.0 有 3.11–3.13 对应 wheel；旧 3.11 失败日志也已选中
PyArrow 的 musllinux wheel。因此此修复不安装或绑定发行版 Arrow SDK。
若将来 resolver 选到只有 sdist 的 PyArrow，则需匹配的 Arrow C++ SDK、CMake 等，
参见 [Arrow 源码构建说明](https://arrow.apache.org/docs/developers/python.html)；届时必须重新验证，
不能使用 distro Python 包或 no-deps 假装满足普通 pip 安装。

维护者需决定是否接受“musl 完整安装需要构建 wbt 源码”的用户要求。建议协调 wbt 上游补齐
musllinux wheel，以降低用户编译成本；该跨仓库构建/上传不属于本任务，也未获得授权。
本轮仅补 runner 基线，不调整依赖或支持范围。若完整安装仍失败，应继续记录实际缺口，
由维护者选择补充工具/资源、上游 wheel 分发或其他明确方案；不能自行删掉 musl 门禁。

### 证据复用与新 SHA 范围

本次不修改 CZSC native/Python 运行源码、依赖图、wheel 构建参数或功能 smoke 脚本。
既有算法、Rust、归档、安全审核和旧 head 的 16 个成功组合可作为历史证据复用，
但新 run 的 wheel 必须标明其自身 producer SHA，不能标记旧产物为新产物。
重点复核 Windows/musl × Python 3.10–3.13 八组合。由于共享版本命令也影响另外四平台，
沿用现有完整 24 组合发布 smoke 演练、重建同一 head 产物，不另造只跑子集却能发布的通道；
这会再次运行短 smoke，不重复已充分验证的全套算法测试。
新演练显式 `publish_to_testpypi=false`，只取一次快照，不等待/轮询外部 CI。
Windows 本机不可用，Docker daemon 不可用，未将本地编码/静态回归宣称为这八组合已通过。

最终复审需核对实际修复 head、八组合安装/native 结果、其余平台共享命令结果以及所有上传
仍 skipped。正式版/RC、最终发布范围、维护者审批、旧 extras 等残余风险接受和上传权限
继续独立待确认；无上传演练通过也不是发布授权。
