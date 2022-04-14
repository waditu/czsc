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

__version__ = "0.8.23"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20220414"

print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
aphorism.print_one()

home_path = os.path.join(os.path.expanduser("~"), '.czsc')
os.makedirs(home_path, exist_ok=True)


def get_dir_size(path):
    """获取目录大小，单位：Bytes"""
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total


if get_dir_size(home_path) > pow(1024, 3) and envs.get_verbose():
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 empty_cache_path 可以直接清空缓存")


def empty_cache_path():
    shutil.rmtree(home_path)
    os.makedirs(home_path, exist_ok=False)
    print(f"已清空缓存文件夹：{home_path}")

