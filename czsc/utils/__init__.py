"""
czsc.utils 工具子包

本子包汇总了 CZSC 项目内的通用工具，包括：分析（analysis）、
数据访问与缓存（data）、IO 助手（io）、绘图（plotting）等。

技术指标（TA）算子已统一由 Rust 端 ``czsc._native.ta`` 提供，从顶层
``czsc.ta`` 直接访问；本子包不再暴露 ``ta`` 子模块。

加载策略（2026-05 评审后已统一）：

1. 顶部直接 import 所有轻量级子模块及其常用函数；
2. ``plotting`` 子包按需 ``import czsc.utils.plotting.xxx`` 显式访问，
   不再通过 ``__getattr__`` 暴露到本模块；
3. 周期排序统一走 ``czsc._runtime_adapters._FREQ_ORDER``，避免两份顺序表漂移。

同时本模块还提供一组小工具函数：``import_by_name``、``freqs_sorted``、
``to_arrow`` 等。
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 轻量级子模块的直接导入
# ---------------------------------------------------------------------------
from . import analysis, data, io

# 从 analysis 子模块再次导出常用的统计 / 绩效函数，方便在 czsc.utils 顶层直接使用
# 2026-05-17 PR-A 起，analysis 仅保留 cross_sectional_ic；daily_performance /
# top_drawdowns 改由调用方走 wbt（czsc 顶层 ``czsc.daily_performance`` 仍可用）。
from .analysis import cross_sectional_ic

# 数据访问、磁盘缓存以及统一数据客户端
from .data import (
    DataClient,
    DiskCache,
    clear_cache,
    clear_expired_cache,
    disk_cache,
    empty_cache_path,
    get_dir_size,
    get_url_token,
    home_path,
    set_url_token,
)

# 股票持仓概念板块效应分析
from .holds_concepts import holds_concepts_effect

# 指数成分相关工具
from .index_composition import index_composition

# JSON / dill 等通用 IO 工具
from .io import dill_dump, dill_load, read_json, save_json

# CTA / 波动率区间后验标注工具（2026-05-17 PR-B 从 czsc/eda.py 拆分而来）
from .mark_cta_periods import mark_cta_periods
from .mark_volatility import mark_volatility

# 开仓 / 平仓参数批量优化（2026-05-17 PR-C 从 czsc/traders/optimize.py 搬运过来）
from .optimize import (
    CzscExitOptimStrategy,
    CzscOpenOptimStrategy,
    ExitsOptimize,
    OpensOptimize,
)

# 交易/重采样相关工具
from .trade import resample_to_daily, risk_free_returns, update_bbars, update_nxb, update_tbars

__all__ = [
    # 子模块
    "analysis",
    "data",
    "io",
    # analysis
    "cross_sectional_ic",
    # data
    "DataClient",
    "DiskCache",
    "clear_cache",
    "clear_expired_cache",
    "disk_cache",
    "empty_cache_path",
    "get_dir_size",
    "get_url_token",
    "home_path",
    "set_url_token",
    # holds_concepts
    "holds_concepts_effect",
    # index_composition
    "index_composition",
    # mark_*（后验区间标注，PR-B 从 czsc/eda.py 拆分而来）
    "mark_cta_periods",
    "mark_volatility",
    # optimize（PR-C 从 czsc/traders/ 搬运而来）
    "OpensOptimize",
    "ExitsOptimize",
    "CzscOpenOptimStrategy",
    "CzscExitOptimStrategy",
    # io
    "dill_dump",
    "dill_load",
    "read_json",
    "save_json",
    # trade
    "resample_to_daily",
    "risk_free_returns",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    # 本模块函数
    "get_py_namespace",
    "code_namespace",
    "import_by_name",
    "freqs_sorted",
    "print_df_sample",
    "to_arrow",
]


# 包根目录：用于 get_py_namespace 的白名单判断，避免依赖 CWD
_CZSC_PKG_ROOT = Path(__file__).resolve().parent.parent


def get_py_namespace(file_py: str, keys: list | None = None) -> dict:
    """获取 Python 脚本文件中的 namespace

    通过 ``compile`` + ``exec`` 在内存中执行脚本，并把执行后的全局命名空间返回。
    出于安全考虑，只允许加载 ``czsc/strategies`` 与 ``czsc/signals`` 目录下的脚本。

    :param file_py: str，Python 脚本文件名（绝对或相对路径均可）
    :param keys: list，指定需要的对象名称；若提供则仅返回这些键
    :return: dict，namespace
    :raises ValueError: 当文件路径不在白名单目录内时
    """
    if keys is None:
        keys = []
    target = Path(file_py).resolve()
    # 白名单基于包真实位置而非 CWD，避免在仓库根目录之外调用时绕过校验
    allowed_dirs = [_CZSC_PKG_ROOT / "strategies", _CZSC_PKG_ROOT / "signals"]
    if not any(target.is_relative_to(d) for d in allowed_dirs):
        raise ValueError(f"文件路径 {target} 不在白名单目录内")
    with open(target, encoding="utf-8") as _f:
        text = _f.read()
    code = compile(text, str(target), "exec")
    namespace: dict = {"file_py": str(target), "file_name": target.stem}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def code_namespace(code: str, keys: list | None = None) -> dict:
    """获取 Python 代码字符串中的 namespace

    与 :func:`get_py_namespace` 类似，但接受的是源代码字符串而非文件路径，
    且不做白名单校验，调用方需自行确保来源安全。

    :param code: str，Python 源代码
    :param keys: list，指定需要的对象名称；若提供则仅返回这些键
    :return: dict，namespace
    """
    if keys is None:
        keys = []
    namespace: dict = {"code": code}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def import_by_name(name):
    """通过字符串导入模块、类或函数

    函数执行逻辑：

    1. 检查 ``name`` 是否包含点号（``.``）。如果没有，则直接 ``__import__`` 整个模块；
    2. 否则用 ``rsplit('.', 1)`` 拆为 ``module_name`` 与 ``function_name``；
    3. 调用 ``__import__`` 时通过 fromlist 参数 ``[function_name]`` 显式声明，
       这样可以避免一次性导入整棵模块树，提高加载效率；
    4. 通过 ``vars(module)`` 取出指定属性。

    :param name: str，模块名或模块.属性名，例如 ``'czsc.objects.Factor'``
    :return: 模块对象 / 类 / 函数
    """
    if "." not in name:
        return __import__(name)

    # 从右侧分割一次，保证最后一个点之前的部分整体作为模块路径
    module_name, function_name = name.rsplit(".", 1)
    module = __import__(module_name, globals(), locals(), [function_name])
    return vars(module)[function_name]


def freqs_sorted(freqs):
    """K 线周期列表排序并去重，第一个元素是基础周期

    内部统一调用 :func:`czsc._runtime_adapters.sort_freqs`，避免两份顺序表漂移。

    :param freqs: K 线周期列表（如 ``['日线', '5分钟', '30分钟']``）
    :return: list，从高频到低频去重后的结果
    """
    from czsc._runtime_adapters import sort_freqs

    return sort_freqs(freqs)


def print_df_sample(df, n=5):
    """以 reST 表格形式打印 DataFrame 的前 n 行，便于在文档中粘贴

    :param df: pd.DataFrame
    :param n: int，打印的行数，默认 5
    """
    from tabulate import tabulate

    print(tabulate(df.head(n).values, headers=df.columns, tablefmt="rst"))


def to_arrow(df: pd.DataFrame):
    """将 ``pandas.DataFrame`` 转换为 Arrow IPC 字节串

    通过 ``pyarrow.ipc.new_file`` 写出，可在不同进程 / 服务之间高效传输 DataFrame。

    :param df: pd.DataFrame
    :return: bytes，Arrow IPC file 格式的二进制数据
    """
    import io

    import pyarrow as pa

    table = pa.Table.from_pandas(df)
    with io.BytesIO() as sink:
        with pa.ipc.new_file(sink, table.schema) as writer:
            writer.write_table(table)
        return sink.getvalue()
