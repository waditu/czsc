import functools
import os
import threading

import pandas as pd

# 导入轻量级子模块
from . import analysis, crypto, data, io, ta
from .analysis import (
    cross_sectional_ic,
    daily_performance,
    holds_performance,
    nmi_matrix,
    overlap,
    psi,
    rolling_daily_performance,
    single_linear,
    top_drawdowns,
)
from .crypto import fernet_decrypt, fernet_encrypt, generate_fernet_key
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
from .index_composition import index_composition
from .io import dill_dump, dill_load, read_json, save_json
from .oss import AliyunOSS

# Delayed import to avoid circular dependency - import these from czsc.utils.sig directly
# from .sig import check_gap_info, is_bis_down, is_bis_up, get_sub_elements, is_symmetry_zs
# from .sig import same_dir_counts, fast_slow_cross, count_last_same, create_single_signal
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
    "overlap",
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
    "echarts_plot",
    "plotting",
    "backtest_report",
    # 延迟加载属性
    "kline_pro",
    "trading_view_kline",
    "generate_backtest_report",
    "generate_html_backtest_report",
    "generate_pdf_backtest_report",
    "PdfReportBuilder",
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
    "get_sub_elements",
    "logger",
]

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

    :param x: 数字
    :param digit: 保留小数位数
    :return:
    """
    if isinstance(x, int):
        return x

    try:
        digit_ = pow(10, digit)
        x = int(x * digit_) / digit_
    except Exception:
        print(f"x_round error: x = {x}")
    return x


def get_py_namespace(file_py: str, keys: list = None) -> dict:
    """获取 python 脚本文件中的 namespace

    :param file_py: python 脚本文件名
    :param keys: 指定需要的对象名称
    :return: namespace
    """
    if keys is None:
        keys = []
    text = open(file_py, encoding="utf-8").read()
    code = compile(text, file_py, "exec")
    namespace = {"file_py": file_py, "file_name": os.path.basename(file_py).split(".")[0]}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def code_namespace(code: str, keys: list = None) -> dict:
    """获取 python 代码中的 namespace

    :param code: python 代码
    :param keys: 指定需要的对象名称
    :return: namespace
    """
    if keys is None:
        keys = []
    namespace = {"code": code}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def import_by_name(name):
    """通过字符串导入模块、类、函数

    函数执行逻辑：

    1. 检查 name 中是否包含点号（'.'）。如果没有，则直接使用内置的 import 函数来导入整个模块，并返回该模块对象。
    2. 如果 name 包含点号，先处理一个相对路径。将 name 拆分为两部分：module_name 和 function_name。
        使用 Python 内置的 rsplit 方法从右边开始分割，只取一次，这样可以确保我们将最后的一个点号前的部分作为 module_name，点号后面的部分作为 function_name。
    3. 使用import函数导入指定的 module_name。
        这里传入三个参数：globals() 和 locals() 分别代表当前全局和局部命名空间；
        [function_name] 是一个列表，用于指定要导入的子模块或属性名。
        这样做是为了避免一次性导入整个模块的所有内容，提高效率。
    4.  使用 vars 函数获取模块的字典表示形式（即模块内所有的变量和函数），取出 function_name 对应的值，然后返回这个值。

    :param name: 模块名，如：'czsc.objects.Factor'
    :return: 模块对象
    """
    if "." not in name:
        return __import__(name)

    # 从右边开始分割，分割成模块名和函数名
    module_name, function_name = name.rsplit(".", 1)
    module = __import__(module_name, globals(), locals(), [function_name])
    return vars(module)[function_name]


def freqs_sorted(freqs):
    """K线周期列表排序并去重，第一个元素是基础周期

    :param freqs: K线周期列表
    :return: K线周期排序列表
    """
    _freqs_new = [x for x in sorted_freqs if x in freqs]
    return _freqs_new


def create_grid_params(prefix: str = "", multiply=3, **kwargs) -> dict:
    """创建 grid search 参数组合

    :param prefix: 参数组前缀
    :param multiply: 参数组合的位数，如果为 0，则使用 # 分隔参数
    :param kwargs: 任意参数的候选序列，参数值推荐使用 iterable
    :return: 参数组合字典

    examples
    ============
    >>>x = create_grid_params("test", x=(1, 2), y=('a', 'b'), detail=True)
    >>>print(x)
    Out[0]:
        {'test_x=1_y=a': {'x': 1, 'y': 'a'},
         'test_x=1_y=b': {'x': 1, 'y': 'b'},
         'test_x=2_y=a': {'x': 2, 'y': 'a'},
         'test_x=2_y=b': {'x': 2, 'y': 'b'}}

    # 单个参数传入单个值也是可以的，但类型必须是 int, float, str 中的任一
    >>>x = create_grid_params("test", x=2, y=('a', 'b'), detail=False)
    >>>print(x)
    Out[1]:
        {'test001': {'x': 2, 'y': 'a'},
         'test002': {'x': 2, 'y': 'b'}}
    """
    from sklearn.model_selection import ParameterGrid

    params_grid = dict(kwargs)
    for k, v in params_grid.items():
        # 处理非 list 类型数据
        if type(v) in [int, float, str]:
            v = [v]
        assert type(v) in [tuple, list], f"输入参数值必须是 list 或 tuple 类型，当前参数 {k} 值：{v}"
        params_grid[k] = v

    params = {}
    for i, row in enumerate(ParameterGrid(params_grid), 1):
        key = "#".join([f"{k}={v}" for k, v in row.items()]) if multiply == 0 else str(i).zfill(multiply)

        row["version"] = f"{prefix}{key}"
        params[f"{prefix}@{key}"] = row
    return params


def print_df_sample(df, n=5):
    from tabulate import tabulate

    print(tabulate(df.head(n).values, headers=df.columns, tablefmt="rst"))


def mac_address():
    """获取本机 MAC 地址

    MAC地址（英语：Media Access Control Address），直译为媒体访问控制地址，也称为局域网地址（LAN Address），
    以太网地址（Ethernet Address）或物理地址（Physical Address），它是一个用来确认网络设备位置的地址。在OSI模
    型中，第三层网络层负责IP地址，第二层数据链接层则负责MAC地址。MAC地址用于在网络中唯一标示一个网卡，一台设备若有一
    或多个网卡，则每个网卡都需要并会有一个唯一的MAC地址。

    :return: 本机 MAC 地址
    """
    import uuid

    x = uuid.UUID(int=uuid.getnode()).hex[-12:].upper()
    x = "-".join([x[i : i + 2] for i in range(0, 11, 2)])
    return x


def to_arrow(df: pd.DataFrame):
    """将 pandas.DataFrame 转换为 pyarrow.Table"""
    import io

    import pyarrow as pa

    table = pa.Table.from_pandas(df)
    with io.BytesIO() as sink:
        with pa.ipc.new_file(sink, table.schema) as writer:
            writer.write_table(table)
        return sink.getvalue()


def timeout_decorator(timeout):
    """Timeout decorator using threading

    :param timeout: int, timeout duration in seconds
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
                from loguru import logger as _logger

                _logger.warning(f"{func.__name__} timed out after {timeout} seconds; args: {args}; kwargs: {kwargs}")
                return None

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper

    return decorator


# 延迟加载的模块映射
_LAZY_SUBMODULES = {
    "echarts_plot": "czsc.utils.echarts_plot",
    "plotting": "czsc.utils.plotting",
    "backtest_report": "czsc.utils.backtest_report",
}

# 延迟加载的属性映射：属性名 -> (模块路径, 属性名)
_LAZY_ATTRS = {
    # echarts_plot
    "kline_pro": ("czsc.utils.echarts_plot", "kline_pro"),
    "trading_view_kline": ("czsc.utils.echarts_plot", "trading_view_kline"),
    # backtest_report
    "generate_backtest_report": ("czsc.utils.backtest_report", "generate_backtest_report"),
    "generate_html_backtest_report": ("czsc.utils.backtest_report", "generate_html_backtest_report"),
    "generate_pdf_backtest_report": ("czsc.utils.backtest_report", "generate_pdf_backtest_report"),
    # pdf_report_builder
    "PdfReportBuilder": ("czsc.utils.pdf_report_builder", "PdfReportBuilder"),
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
    # sig
    "get_sub_elements": ("czsc.utils.sig", "get_sub_elements"),
    # loguru logger
    "logger": ("loguru", "logger"),
}


def __getattr__(name):
    """延迟加载重型子模块和属性，避免影响导入速度"""
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
