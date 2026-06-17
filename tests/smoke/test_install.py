"""安装产物烟雾测试：maturin wheel 安装与原生扩展可用性验证。

本测试套件用于在最小可运行范围内验证 czsc 的 Rust/Python 混合架构构建产物
（wheel）是否被正确打包，并且能够在干净的虚拟环境中安装并通过基本的导入
冒烟测试。

业务背景：
    项目通过 ``maturin build --release`` 构建跨平台二进制 wheel
    （manylinux/macOS/Windows），其中包含 Rust 编译产物 ``czsc._native``
    动态库。安装该 wheel 后，必须满足：

    1. ``import czsc`` 成功；
    2. ``import czsc._native`` 成功且 ``__file__`` 指向编译产物（.so/.pyd/.dylib）；
    3. 不再需要任何额外的 ``rs_czsc`` 包。

测试覆盖：
    - ``pyproject.toml`` 已使用 ``maturin`` 作为构建后端；
    - 当前安装环境中可成功导入 ``czsc._native``；
    - ``dist/`` 下的 wheel 在干净 venv 中可安装且 ``czsc.CZSC.__module__`` 指向 czsc 命名空间。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# 仓库根目录（基于本测试文件位置反推），以及构建产物所在目录
REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "dist"


def test_pyproject_uses_maturin_backend() -> None:
    """验证 pyproject.toml 使用 maturin 作为构建后端。

    测试目标：
        确保项目构建系统已切换为 maturin（PyO3 推荐的 Python 扩展打包工具），
        以便能够产出包含 Rust 原生扩展的 wheel。

    关键断言：
        pyproject.toml 文件中包含 ``maturin`` 字符串，意味着 ``[build-system]``
        节点声明了 ``requires=['maturin>=...']`` 与 ``build-backend='maturin'``。
    """
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.is_file():
        pytest.fail(f"未找到 pyproject.toml，路径：{pyproject}")
    text = pyproject.read_text(encoding="utf-8")
    assert "maturin" in text, (
        "pyproject.toml 必须声明 [build-system] requires=['maturin>=...'] 以及 build-backend='maturin'"
    )


@pytest.mark.slow
def test_native_extension_present_in_install() -> None:
    """验证当前安装环境中已包含编译后的 czsc._native 扩展。

    测试场景：
        通过子进程方式调用 Python 解释器尝试 ``import czsc._native``，
        并打印其 ``__file__`` 属性。

    关键断言：
        - 子进程退出码必须为 0（导入成功）；
        - ``czsc._native.__file__`` 必须以 ``.so`` / ``.pyd`` / ``.dylib`` 结尾，
          表明它是编译生成的二进制扩展，而不是普通 Python 模块。
    """
    proc = subprocess.run(
        [sys.executable, "-c", "import czsc._native; print(czsc._native.__file__)"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "在当前安装环境中 `import czsc._native` 必须成功 "
        f"(stderr: {proc.stderr.strip()!r})；"
        "构建流程必须保证 maturin 正确打包了 Rust 扩展"
    )
    out = proc.stdout.strip()
    assert out.endswith((".so", ".pyd", ".dylib")), f"czsc._native.__file__ 应指向编译扩展，实际为 {out!r}"


def test_wheel_install_in_clean_venv(tmp_path: Path) -> None:
    """在干净 venv 中安装 wheel 并执行最小冒烟导入。

    测试场景：
        1. 在 ``dist/`` 下查找最新构建的 ``czsc-*.whl`` 文件；
        2. 在 pytest 提供的临时目录下创建一个全新的虚拟环境；
        3. 使用 ``pip install --find-links`` 将 wheel 安装进该 venv；
        4. 在该 venv 中执行 ``import czsc; print(czsc.CZSC.__module__)``。

    设计要点：
        - 使用 ``--find-links DIST_DIR`` 让 pip 能够找到 dist/ 下的同伴 wheel
          （例如尚未发布到 PyPI 的预发布版 wbt wheel），不可用时再回退到 PyPI；
        - 打印的是 ``czsc.CZSC.__module__``（类的模块名），而不是
          ``type(czsc.CZSC).__module__``（其元类的模块名）。后者对于 PyO3 类
          会返回 ``"builtins"``，无法验证迁移目标是否达成。

    关键断言：
        - ``pip install`` 退出码为 0；
        - 子进程导入并打印的模块名包含 ``"czsc"``，证明 ``CZSC`` 类来自
          ``czsc._native`` 命名空间。
    """
    # 选取 dist/ 下的所有 czsc 安装包，并以排序方式取最新版本
    wheels = sorted(DIST_DIR.glob("czsc-*.whl")) if DIST_DIR.is_dir() else []
    if not wheels:
        # 常规 CI 的 test job 只跑 `maturin develop`，不产 wheel；
        # wheel 安装验证由 python-publish.yml 的 smoke-test job 在发布流程
        # 里专门跑。所以本地/常规 CI 没 wheel 时跳过，不算失败。
        pytest.skip(f"在 {DIST_DIR} 下找不到 wheel；如需运行本测试，请先 `maturin build --release`")

    # 构建一个全新的虚拟环境用于隔离安装
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    py = venv / "bin" / "python"

    # `--find-links DIST_DIR` 让 pip 解析 dist/ 下的同伴 wheel
    # （例如尚未发布到 PyPI 的预发布 wbt-0.1.7 wheel，提前包含了
    # czsc 在模块加载时引用的 top_drawdowns 等名称）。
    # 缺少该参数时安装会从 PyPI 拉取 wbt 0.1.6，导致 czsc 启动失败。
    install = subprocess.run(
        [str(pip), "install", "--find-links", str(DIST_DIR), str(wheels[-1])],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        pytest.fail(f"pip install {wheels[-1].name} 失败: {install.stderr}")

    # 在新 venv 中打印 czsc.CZSC.__module__，
    # 该值由 PyO3 的 #[pyclass(module=...)] 设置为 "czsc._native"
    smoke = subprocess.run(
        [str(py), "-c", "import czsc; print(czsc.CZSC.__module__)"],
        capture_output=True,
        text=True,
    )
    if smoke.returncode != 0:
        pytest.fail(f"冒烟 `import czsc` 失败: {smoke.stderr}")
    out = smoke.stdout.strip()
    assert "czsc" in out, f"冒烟测试输出异常：{out!r}"
