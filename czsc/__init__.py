# coding: utf-8

from .analyze import KlineAnalyze, down_zs_number, up_zs_number, is_bei_chi
from .ta import ma, macd, boll
from .utils import plot_kline
from .solid import SolidAnalyze
from .solid import is_in_tolerance, is_first_buy, is_first_sell, is_second_buy, \
    is_second_sell, is_third_buy, is_third_sell, is_xd_buy, is_xd_sell

__version__ = "0.3.5"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"


