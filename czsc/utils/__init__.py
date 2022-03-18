# coding: utf-8

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
