# coding: utf-8

from .analyze import CZSC, CzscTrader
from .utils.ta import SMA, EMA, MACD, KDJ
from .data.jq import JqCzscTrader
from . import aphorism

__version__ = "0.8.8"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20211129"

print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")

aphorism.print_one()

