# coding: utf-8
import os
from typing import List, Union

from . import qywx
from . import ta
from . import io
from . import echarts_plot

from .echarts_plot import kline_pro, heat_map
from .word_writer import WordWriter
from .corr import nmi_matrix, single_linear, cross_sectional_ic
from .bar_generator import BarGenerator, freq_end_time, resample_bars
from .io import dill_dump, dill_load, read_json, save_json
from .sig import check_pressure_support, check_gap_info, is_bis_down, is_bis_up, get_sub_elements
from .sig import same_dir_counts, fast_slow_cross, count_last_same, create_single_signal
from .plotly_plot import KlineChart
from .trade import cal_trade_price, update_nbars, update_bbars, update_tbars
from .cross import CrossSectionalPerformance
from .stats import daily_performance, net_value_stats, subtract_fee


sorted_freqs = ['Tick', '1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线']


def x_round(x: Union[float, int], digit: int = 4) -> Union[float, int]:
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
    except:
        print(f"x_round error: x = {x}")
    return x


def get_py_namespace(file_py: str, keys: list = []) -> dict:
    """获取 python 脚本文件中的 namespace

    :param file_py: python 脚本文件名
    :param keys: 指定需要的对象名称
    :return: namespace
    """
    text = open(file_py, 'r', encoding='utf-8').read()
    code = compile(text, file_py, 'exec')
    namespace = {"file_py": file_py, 'file_name': os.path.basename(file_py).split('.')[0]}
    exec(code, namespace)
    if keys:
        namespace = {k: v for k, v in namespace.items() if k in keys}
    return namespace


def import_by_name(name):
    """通过字符串导入模块、类、函数

    :param name: 模块名，如：'czsc.objects.Factor'
    :return: 模块对象
    """
    if '.' not in name:
        return __import__(name)

    # 从右边开始分割，分割成模块名和函数名
    module_name, function_name = name.rsplit('.', 1)
    module = __import__(module_name, globals(), locals(), [function_name])
    return vars(module)[function_name]


def freqs_sorted(freqs):
    """K线周期列表排序并去重，第一个元素是基础周期

    :param freqs: K线周期列表
    :return: K线周期排序列表
    """
    _freqs_new = [x for x in sorted_freqs if x in freqs]
    return _freqs_new


def create_grid_params(prefix: str, detail=False, **kwargs) -> dict:
    """创建 grid search 参数组合

    :param prefix: 参数组前缀
    :param detail: 是否使用参数值构建参数组的名称
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
        {'test@001': {'x': 2, 'y': 'a'},
         'test@002': {'x': 2, 'y': 'b'}}
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
        if detail:
            key = "#".join([f"{k}={v}" for k, v in row.items()])
            # params[f"{prefix}@{key}"] = row
        else:
            key = f"{'0' * (3-len(str(i)))}{i}"

        row['version'] = f"{prefix}@{key}"
        params[f"{prefix}@{key}"] = row
    return params


def print_df_sample(df, n=5):
    from tabulate import tabulate
    print(tabulate(df.head(n).values, headers=df.columns, tablefmt='rst'))
