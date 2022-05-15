# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
from . import envs
from . import ai
from . import utils
from . import traders
from . import sensors
from . import aphorism
from .analyze import CZSC
from .traders.advanced import CzscAdvancedTrader, create_advanced_trader
from .utils.ta import SMA, EMA, MACD, KDJ
from .objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar
from .utils.cache import home_path, get_dir_size, empty_cache_path

__version__ = "0.8.27"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20220515"

print(f"CZSC环境变量："
      f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
      f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
      f"czsc_bi_change_th = {envs.get_bi_change_th()}")

if envs.get_welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()


if get_dir_size(home_path) > pow(1024, 3) and envs.get_verbose():
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 empty_cache_path 可以直接清空缓存")
