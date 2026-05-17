"""PR-1 防护测试：streamlit 解耦的 ratchet。

设计成两组：

* **A 组（源码 grep）**：锁定一批"现在已经独立"的模块文件，其 .py 源码
  不得出现 ``import streamlit`` / ``from streamlit``。PR-1 现状下应当立刻
  全部 pass；任何后续 PR 把 streamlit 重新拉进这些文件都会让 CI 立即红。
* **B 组（运行时 ratchet）**：观察"当前耦合、PR-2/PR-4 之后应当独立"的
  运行时 import 行为，统一标 ``xfail(strict=True)``。解耦完成后这些用例
  会从 xfail 变成 unexpectedly passed，CI 红灯，提示维护者摘掉 xfail——
  形成显式的进度 ratchet，防止"PR 合了但没真正解耦"。

不在测试里用 monkeypatch 直接 ``import czsc``：因为 ``czsc/__init__.py``
当前 eager-import ``svc``，这条链在 PR-2 之前必然触发 streamlit；运行时
断言只能通过 ``xfail`` 表达基线，源码层面的边界用 grep 锁定。

二阶段清理 PR-D 更新：原"KlineChart / plot_czsc_chart / plot_cumulative_returns /
plot_backtest_stats 必须保留"的兜底断言已反转为"必须删除"，与
``test_drop_secondary_api.py`` 共同守护本次清理决议。
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

CZSC_ROOT = Path(__file__).resolve().parents[2] / "czsc"

# 锚定 import streamlit 或 from streamlit 的两种写法（行首允许任意缩进，
# 兼容 lazy import 的 ``def f(): import streamlit``）。
_STREAMLIT_IMPORT = re.compile(r"^\s*(?:import\s+streamlit|from\s+streamlit\b)", re.MULTILINE)


def _file_touches_streamlit(p: Path) -> bool:
    return bool(_STREAMLIT_IMPORT.search(p.read_text(encoding="utf-8")))


# --- A 组：源码层面"现在已经独立"，PR 不允许把 streamlit 加回去 ---------------

# 这些路径的边界含义：
#   _macd.py             - 私有 helper，仅 numpy
#   kline.py             - plotly，networkx 图绘制（二阶段清理 PR-C 起 KlineChart / plot_czsc_chart 已删）
#   data/cache.py        - 缓存 / IO，与可视化无关
#   utils/data/__init__  - 数据 IO 命名空间
#
# 注：``utils/plotting/backtest.py`` 已在二阶段清理 PR-C 整文件 git rm，故移出本列表。
INDEPENDENT_FILES = pytest.mark.parametrize(
    "relpath",
    [
        "utils/plotting/_macd.py",
        "utils/plotting/kline.py",
        "utils/data/cache.py",
        "utils/data/__init__.py",
    ],
)


@INDEPENDENT_FILES
def test_source_file_does_not_touch_streamlit(relpath: str) -> None:
    """A 组：固化"现在已独立"的文件边界，PR 不许把 streamlit 写回去。"""
    target = CZSC_ROOT / relpath
    assert target.exists(), f"baseline 文件 {target} 不存在，可能被误删或路径过时"
    assert not _file_touches_streamlit(target), (
        f"{target} 不应包含 import streamlit / from streamlit；可视化层应使用 plotly 直接渲染或返回 plotly Figure。"
    )


# --- B 组：运行时 ratchet，xfail strict，解耦完成后强制摘标 ---------------------


def _run_isolated_import(modname: str) -> tuple[int, str]:
    """在 streamlit 被 ban 的全新子进程里 import 指定模块，返回退出码 + 合并输出。

    用子进程隔离避免 sys.modules 残留干扰；用 ``sys.modules["streamlit"] = None``
    让任何 ``import streamlit`` 立即抛 ``ModuleNotFoundError``。
    """
    code = (
        "import sys\n"
        'sys.modules["streamlit"] = None\n'
        'sys.modules["streamlit_lightweight_charts"] = None\n'
        f"import {modname}\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def test_import_czsc_does_not_require_streamlit() -> None:
    """B 组：``import czsc`` 顶层不依赖 streamlit。

    PR-2 删除 ``czsc/__init__.py`` 中 eager-import ``svc`` 后转正式 pass；
    后续 PR 把 streamlit 再拉回顶层 import 链会让本用例立即红。
    """
    rc, output = _run_isolated_import("czsc")
    assert rc == 0, f"import czsc 仍触发 streamlit:\n{output}"


def test_lightweight_html_does_not_require_streamlit() -> None:
    """B 组：lightweight 子包的 HTML 路径不依赖 streamlit。

    早期 ``_streamlit_renderer.py`` 已经把 ``import streamlit`` 放在函数内
    (lazy)，本测试即为正式 pass。PR-4 会进一步删除 ``_streamlit_renderer.py``
    与 ``lightweight/__init__.py`` 中的 streamlit 分支；删完之后本用例仍应 pass。
    """
    rc, output = _run_isolated_import("czsc.utils.plotting.lightweight")
    assert rc == 0, f"import czsc.utils.plotting.lightweight 仍触发 streamlit:\n{output}"


# --- 兼容性兜底：导入接口仍存在 ----------------------------------------------


def test_macd_helper_still_importable() -> None:
    """无论是否 streamlit 在 sys.path 中，``compute_macd`` 必须可用。

    用普通 import 而非 ratchet：本测试不检查 streamlit 副作用，只检查
    PR 没把 ``_macd.py`` 删错或重命名。
    """
    mod = importlib.import_module("czsc.utils.plotting._macd")
    assert hasattr(mod, "compute_macd"), "_macd.compute_macd 必须保留（kline/lightweight 下游）"


def test_plot_kline_no_longer_exposes_kline_chart() -> None:
    """二阶段清理 PR-C 起：KlineChart / plot_czsc_chart 已删除。

    上一波 PR-1 此处断言"必须保留"，本次清理把缠论 K 线可视化统一收敛到
    :mod:`czsc.utils.plotting.lightweight`（离线 HTML，多周期联立）。本测试反向
    锁定该决议，避免有人后续把 KlineChart 加回来。
    """
    mod = importlib.import_module("czsc.utils.plotting.kline")
    assert not hasattr(mod, "KlineChart"), "kline.KlineChart 应已删除（二阶段清理 PR-C breaking change）"
    assert not hasattr(mod, "plot_czsc_chart"), "kline.plot_czsc_chart 应已删除（二阶段清理 PR-C breaking change）"
    # plot_nx_graph 仍保留（networkx 图渲染，与缠论 K 线无关）
    assert hasattr(mod, "plot_nx_graph"), "kline.plot_nx_graph 必须保留"


def test_plot_backtest_module_removed() -> None:
    """二阶段清理 PR-C 起：``czsc.utils.plotting.backtest`` 整文件已 git rm。

    上一波 PR-1 在这里断言 "plot_cumulative_returns / plot_backtest_stats 必须可
    import"，本次清理整体放弃这套绘图 API，改由调用方自行用 ``plotly.express`` 或
    ``wbt.generate_backtest_report`` 渲染。
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("czsc.utils.plotting.backtest")
