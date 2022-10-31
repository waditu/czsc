# coding: utf-8
import os

from . import qywx
from . import ta
from . import io
from . import log
from . import echarts_plot
from . import fei_shu

from .echarts_plot import kline_pro, heat_map
from .log import create_logger
from .word_writer import WordWriter
from .corr import nmi_matrix
from .bar_generator import BarGenerator, freq_end_time
from .io import dill_dump, dill_load, read_json, save_json
from .sig import check_pressure_support, check_gap_info, is_bis_down, is_bis_up, get_sub_elements
from .sig import same_dir_counts, fast_slow_cross


def x_round(x: [float, int], digit=4):
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


def get_py_namespace(file_py: str, keys: list = None) -> dict:
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

