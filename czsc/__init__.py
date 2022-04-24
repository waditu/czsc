# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
import os
import shutil

from . import envs
from . import ai
from . import utils
from . import traders
from . import sensors
from . import aphorism
from .analyze import CZSC
from .traders.advanced import CzscAdvancedTrader
from .utils.ta import SMA, EMA, MACD, KDJ
from .objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar
from .utils.cache import home_path, get_dir_size, empty_cache_path

__version__ = "0.8.24"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20220418"


if envs.get_welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()


if get_dir_size(home_path) > pow(1024, 3) and envs.get_verbose():
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 empty_cache_path 可以直接清空缓存")
