"""``czsc/utils/__init__.pyi`` 与运行时实现的同步测试。

背景：
    历史上 ``czsc/utils/__init__.pyi`` 残留过一批被删除的 stub 声明
    （例如 ``crypto`` / ``overlap`` / ``cross_sectional_ranker`` /
    ``fernet_*`` / ``KlineChart``），导致 ``basedpyright`` 把 import
    解析到不存在的对象。L-1 评审决议要求 stub 与实现保持同步，并由 CI
    自动护卫。本测试就是这道护栏的运行时版本。

策略：
    解析 ``czsc/utils/__init__.pyi``（用 AST 模块，不需要执行）取出所有
    ``from .xxx import Y as Y`` 风格的 re-export，断言每一个 Y 都能从
    运行时 ``czsc.utils`` 上访问到。

    这种"用 AST 比对 stub vs runtime"的方式比起 ``basedpyright czsc/``
    更轻量：不依赖外部类型检查器、不依赖 ``--strict`` 模式，单纯防止
    stub 文件再次悄悄声明已删除的符号。
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

STUB_PATH = Path(__file__).resolve().parent.parent.parent / "czsc" / "utils" / "__init__.pyi"


def _collect_reexported_names(stub_path: Path) -> list[str]:
    """从 stub 里抽取 ``from .x import Y as Y`` 形式的 re-export 名字。"""
    tree = ast.parse(stub_path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                # 形如 `from .data import DataClient as DataClient`：
                #   alias.name == "DataClient"，alias.asname == "DataClient"
                if alias.asname is not None:
                    names.append(alias.asname)
    return names


@pytest.mark.parametrize("name", _collect_reexported_names(STUB_PATH))
def test_stub_reexported_name_resolves_at_runtime(name: str) -> None:
    """断言 stub 中 re-export 的每一个名字都能从 ``czsc.utils`` 访问到。

    任何 stub 声明但运行时缺失的符号都会让本用例 FAIL，及时拦截
    "stub 与实现脱钩" 这类回归。
    """
    utils = importlib.import_module("czsc.utils")
    assert hasattr(utils, name), (
        f"czsc/utils/__init__.pyi 声明了 `{name}` 但运行时 czsc.utils 没有该属性；"
        " 请同步更新 stub 文件，或恢复缺失的实现。"
    )
