# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
from czsc import envs
from czsc import ai
from czsc import utils
from czsc import traders
from czsc import sensors
from czsc import aphorism
from czsc.analyze import CZSC
from czsc.objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar, Position
from czsc.utils.cache import home_path, get_dir_size, empty_cache_path
from czsc.traders import CzscTrader, CzscSignals, generate_czsc_signals
from czsc.traders import PairsPerformance, combine_holds_and_pairs, combine_dates_and_pairs


__version__ = "0.9.9"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20230220"


if envs.get_welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(f"CZSC环境变量："
          f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
          f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
          f"czsc_bi_change_th = {envs.get_bi_change_th()}")


if get_dir_size(home_path) > pow(1024, 3) and envs.get_verbose():
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path 可以直接清空缓存")
