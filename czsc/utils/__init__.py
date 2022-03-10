# coding: utf-8

from .echarts_plot import kline_pro, heat_map
from .ta import KDJ, MACD, EMA, SMA
from .io import read_pkl, save_pkl, read_json, save_json
from .log import create_logger
from .word_writer import WordWriter
from .corr import nmi_matrix
from . import qywx
from . import ta


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
