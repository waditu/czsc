# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
from . import ai
from . import utils
from . import traders
from . import sensors
from . import aphorism

from .analyze import CZSC
from .traders.advanced import CzscAdvancedTrader
from .utils.ta import SMA, EMA, MACD, KDJ
from .objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar

__version__ = "0.8.21"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20220402"

print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")

aphorism.print_one()

