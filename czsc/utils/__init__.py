"""
czsc.utils 工具子包

本子包汇总了 CZSC 项目内的通用工具，包括：分析（analysis）、加解密（crypto）、
数据访问与缓存（data）、IO 助手（io）、技术指标（ta）、绘图（plotting）等。

为了兼顾"导入即可用"和"按需懒加载"两种诉求，本模块采用如下策略：

1. 顶部直接导入轻量级子模块及其常用函数；
2. ``plotting`` 子包以及绘图相关函数采用 :func:`__getattr__` 实现的懒加载，
   在首次访问时才真正导入，避免启动时拖慢 ``import czsc``；
3. ``logger`` 也通过懒加载从 ``loguru`` 暴露，便于其他模块统一使用同一实例。

同时本模块还提供一组小工具函数：``x_round``、``import_by_name``、``freqs_sorted``、
``create_grid_params``、``mac_address``、``to_arrow``、``timeout_decorator`` 等。
"""

import functools
import os
import threading

import pandas as pd

# ---------------------------------------------------------------------------
# 轻量级子模块的直接导入
# ---------------------------------------------------------------------------
# 这些子模块加载成本可控，且在 czsc 工程中被高频复用，因此直接 import
from . import analysis, crypto, data, io, ta

# 从 analysis 子模块再次导出常用的统计 / 绩效函数，方便在 czsc.utils 顶层直接使用
from .analysis import (
    cross_sectional_ic,
    daily_performance,
    holds_performance,
    nmi_matrix,
    psi,
    rolling_daily_performance,
    single_linear,
    top_drawdowns,
)

# 加解密相关：Fernet 密钥生成与对称加解密
from .crypto import fernet_decrypt, fernet_encrypt, generate_fernet_key

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

# 指数成分相关工具
from .index_composition import index_composition

# JSON / dill 等通用 IO 工具
from .io import dill_dump, dill_load, read_json, save_json

# 阿里云 OSS 客户端封装
from .oss import AliyunOSS

# 注意：``sig`` 模块依赖 ``czsc`` 顶层包，存在循环导入风险，故此处不预先 re-export，
# 调用方需要按需通过 ``from czsc.utils.sig import ...`` 方式直接引用。
# 交易/重采样相关工具
from .trade import resample_to_daily, risk_free_returns, update_bbars, update_nxb, update_tbars

__all__ = [
    # 子模块
    "analysis",
    "crypto",
    "data",
    "io",
    "ta",
    # analysis
    "cross_sectional_ic",
    "daily_performance",
    "holds_performance",
    "nmi_matrix",
    "psi",
    "rolling_daily_performance",
    "single_linear",
    "top_drawdowns",
    # crypto
    "fernet_decrypt",
    "fernet_encrypt",
    "generate_fernet_key",
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
    # index_composition
    "index_composition",
    # io
    "dill_dump",
    "dill_load",
    "read_json",
    "save_json",
    # oss
    "AliyunOSS",
    # trade
    "resample_to_daily",
    "risk_free_returns",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    # 本模块函数
    "x_round",
    "get_py_namespace",
    "code_namespace",
    "import_by_name",
    "freqs_sorted",
    "create_grid_params",
    "print_df_sample",
    "mac_address",
    "to_arrow",
    "timeout_decorator",
    "sorted_freqs",
    # 延迟加载模块
    "plotting",
    # 延迟加载属性
    "KlineChart",
    "plot_czsc_chart",
    "plot_cumulative_returns",
    "plot_drawdown_analysis",
    "plot_daily_return_distribution",
    "plot_monthly_heatmap",
    "plot_backtest_stats",
    "plot_colored_table",
    "plot_long_short_comparison",
    "plot_weight_histogram_kde",
    "plot_weight_cdf",
    "plot_turnover_overview",
    "plot_turnover_cost_analysis",
    "plot_weight_time_series",
    "logger",
]

# 标准 K 线周期排序顺序，用于 ``freqs_sorted`` 排序
sorted_freqs = [
    "Tick",
    "1分钟",
    "2分钟",
    "3分钟",
    "4分钟",
    "5分钟",
    "6分钟",
    "10分钟",
    "12分钟",
    "15分钟",
    "20分钟",
    "30分钟",
    "60分钟",
    "120分钟",
    "日线",
    "周线",
    "月线",
    "季线",
    "年线",
]


def x_round(x: float | int, digit: int = 4) -> float | int:
    """用去尾法截断小数

    与 :func:`round` 不同，该函数采用去尾（向零）方式截断小数位，避免四舍五入
    带来的微小偏差。

    :param x: 数字（int 或 float）；如为 int 则原样返回
    :param digit: 保留的小数位数
    :return: 截断后的数字；异常时返回原值并打印日志
    """
    if isinstance(x, int):
        return x

    try:
        digit_ = pow(10, digit)
        x = int(x * digit_) / digit_
    except Exception:
        # 浮点转换失败时打印诊断信息，但不抛异常以保护调用链
        print(f"x_round error: x = {x}")
    return x


def get_py_namespace(file_py: str, keys: list = None) -> dict:
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
    file_py = os.path.abspath(file_py)
    # 安全白名单：只允许执行 czsc 内部的策略 / 信号脚本
    allowed_prefixes = [os.path.abspath("czsc/strategies"), os.path.abspath("czsc/signals")]
    if not any(file_py.startswith(p) for p in allowed_prefixes):
        raise ValueError(f"文件路径 {file_py} 不在白名单目录内")
    text = open(file_py, encoding="utf-8").read()
    code = compile(text, file_py, "exec")
    namespace = {"file_py": file_py, "file_name": os.path.basename(file_py).split(".")[0]}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def code_namespace(code: str, keys: list = None) -> dict:
    """获取 Python 代码字符串中的 namespace

    与 :func:`get_py_namespace` 类似，但接受的是源代码字符串而非文件路径，
    且不做白名单校验，调用方需自行确保来源安全。

    :param code: str，Python 源代码
    :param keys: list，指定需要的对象名称；若提供则仅返回这些键
    :return: dict，namespace
    """
    if keys is None:
        keys = []
    namespace = {"code": code}
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

    :param freqs: K 线周期列表（如 ``['日线', '5分钟', '30分钟']``）
    :return: list，按 :data:`sorted_freqs` 顺序排序并去重后的结果
    """
    _freqs_new = [x for x in sorted_freqs if x in freqs]
    return _freqs_new


def create_grid_params(prefix: str = "", multiply=3, **kwargs) -> dict:
    """创建 grid search 参数组合

    基于 ``sklearn.model_selection.ParameterGrid`` 生成参数笛卡尔积，并按用户
    指定的命名风格输出，便于在批量回测、网格搜索时复用。

    :param prefix: str，参数组前缀
    :param multiply: int，参数组合编号的位数；为 0 时改用 ``#`` 连接的可读 key
    :param kwargs: 任意参数的候选序列；推荐使用 list/tuple，单个值也会被自动包装
    :return: dict，``{key: 参数字典}`` 形式的参数组合

    示例：
        >>> x = create_grid_params("test", x=(1, 2), y=('a', 'b'), detail=True)
        >>> print(x)
        Out[0]:
            {'test_x=1_y=a': {'x': 1, 'y': 'a'},
             'test_x=1_y=b': {'x': 1, 'y': 'b'},
             'test_x=2_y=a': {'x': 2, 'y': 'a'},
             'test_x=2_y=b': {'x': 2, 'y': 'b'}}

        # 单个参数传入单个值也是可以的，但类型必须是 int, float, str 中的任一
        >>> x = create_grid_params("test", x=2, y=('a', 'b'), detail=False)
        >>> print(x)
        Out[1]:
            {'test001': {'x': 2, 'y': 'a'},
             'test002': {'x': 2, 'y': 'b'}}
    """
    from sklearn.model_selection import ParameterGrid

    params_grid = dict(kwargs)
    for k, v in params_grid.items():
        # 标量值自动包装为单元素列表，便于 ParameterGrid 处理
        if type(v) in [int, float, str]:
            v = [v]
        assert type(v) in [tuple, list], f"输入参数值必须是 list 或 tuple 类型，当前参数 {k} 值：{v}"
        params_grid[k] = v

    params = {}
    for i, row in enumerate(ParameterGrid(params_grid), 1):
        # multiply == 0 时使用可读的 key，否则使用补零后的序号
        key = "#".join([f"{k}={v}" for k, v in row.items()]) if multiply == 0 else str(i).zfill(multiply)

        row["version"] = f"{prefix}{key}"
        params[f"{prefix}@{key}"] = row
    return params


def print_df_sample(df, n=5):
    """以 reST 表格形式打印 DataFrame 的前 n 行，便于在文档中粘贴

    :param df: pd.DataFrame
    :param n: int，打印的行数，默认 5
    """
    from tabulate import tabulate

    print(tabulate(df.head(n).values, headers=df.columns, tablefmt="rst"))


def mac_address():
    """获取本机 MAC 地址

    MAC 地址（Media Access Control Address），又称为局域网地址（LAN Address）、
    以太网地址（Ethernet Address）或物理地址（Physical Address），用于唯一标识
    网络中的网卡。一台设备若有多块网卡，则每块网卡都会拥有各自的 MAC 地址。

    :return: str，本机 MAC 地址，形如 ``"AA-BB-CC-DD-EE-FF"``
    """
    import uuid

    x = uuid.UUID(int=uuid.getnode()).hex[-12:].upper()
    x = "-".join([x[i : i + 2] for i in range(0, 11, 2)])
    return x


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


def timeout_decorator(timeout):
    """基于线程实现的超时装饰器

    将被装饰函数放在子线程中执行，主线程 ``join`` 等待 ``timeout`` 秒；超时则
    返回 ``None`` 并打印 warning 日志。注意：超时不会真正终止子线程，子线程仍在
    后台运行。

    :param timeout: int，超时秒数
    :return: 装饰器
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 用列表作为 mutable 容器，便于子线程回写
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(timeout)

            if thread.is_alive():
                # 超时：不终止线程，只输出告警并返回 None
                from loguru import logger as _logger

                _logger.warning(f"{func.__name__} timed out after {timeout} seconds; args: {args}; kwargs: {kwargs}")
                return None

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# 延迟加载（lazy import）配置
# ---------------------------------------------------------------------------
# plotting 子包及其下属绘图函数加载较重，统一在首次访问时再 importlib，避免
# ``import czsc`` 阶段就把全部 plotly / matplotlib 等依赖拉起来。

# 延迟加载的子模块映射：属性名 -> 模块路径
_LAZY_SUBMODULES = {
    "plotting": "czsc.utils.plotting",
}

# 延迟加载的属性映射：属性名 -> (模块路径, 属性名)
_LAZY_ATTRS = {
    # plotting.kline
    "KlineChart": ("czsc.utils.plotting.kline", "KlineChart"),
    "plot_czsc_chart": ("czsc.utils.plotting.kline", "plot_czsc_chart"),
    # plotting.backtest
    "plot_cumulative_returns": ("czsc.utils.plotting.backtest", "plot_cumulative_returns"),
    "plot_drawdown_analysis": ("czsc.utils.plotting.backtest", "plot_drawdown_analysis"),
    "plot_daily_return_distribution": ("czsc.utils.plotting.backtest", "plot_daily_return_distribution"),
    "plot_monthly_heatmap": ("czsc.utils.plotting.backtest", "plot_monthly_heatmap"),
    "plot_backtest_stats": ("czsc.utils.plotting.backtest", "plot_backtest_stats"),
    "plot_colored_table": ("czsc.utils.plotting.backtest", "plot_colored_table"),
    "plot_long_short_comparison": ("czsc.utils.plotting.backtest", "plot_long_short_comparison"),
    # plotting.weight
    "plot_weight_histogram_kde": ("czsc.utils.plotting.weight", "plot_weight_histogram_kde"),
    "plot_weight_cdf": ("czsc.utils.plotting.weight", "plot_weight_cdf"),
    "plot_turnover_overview": ("czsc.utils.plotting.weight", "plot_turnover_overview"),
    "plot_turnover_cost_analysis": ("czsc.utils.plotting.weight", "plot_turnover_cost_analysis"),
    "plot_weight_time_series": ("czsc.utils.plotting.weight", "plot_weight_time_series"),
    # loguru logger 也通过懒加载暴露
    "logger": ("loguru", "logger"),
}


def __getattr__(name):
    """模块级 ``__getattr__``：实现延迟加载

    当用户访问尚未导入的属性时（包括 ``plotting`` 子模块和具体的绘图函数），由
    本函数完成动态 import 并把结果写回模块全局空间，以便后续再次访问无需重复导入。

    :param name: str，访问的属性名
    :return: 对应的模块或属性
    :raises AttributeError: 当 name 既不在懒加载子模块也不在懒加载属性表中时
    """
    import importlib

    if name in _LAZY_SUBMODULES:
        module = importlib.import_module(_LAZY_SUBMODULES[name])
        globals()[name] = module
        return module

    if name in _LAZY_ATTRS:
        mod_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(mod_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
