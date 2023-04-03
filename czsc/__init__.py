# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
from czsc import envs
from czsc import ai
from czsc import fsa
from czsc import utils
from czsc import traders
from czsc import sensors
from czsc import aphorism
from czsc.analyze import CZSC
from czsc.objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar, Position
from czsc.utils.cache import home_path, get_dir_size, empty_cache_path
from czsc.traders import CzscTrader, CzscSignals, generate_czsc_signals, check_signals_acc, get_unique_signals
from czsc.traders import PairsPerformance, combine_holds_and_pairs, combine_dates_and_pairs, stock_holds_performance
from czsc.traders import DummyBacktest, SignalsParser, get_signals_by_conf, get_signals_config, get_signals_freqs
from czsc.strategies import CzscStrategyBase
from czsc.utils import KlineChart, BarGenerator, resample_bars, dill_dump, dill_load, read_json, save_json
from czsc.utils import get_sub_elements, get_py_namespace, freqs_sorted, x_round, import_by_name, create_grid_params
from czsc.utils import cal_trade_price, cross_sectional_ic
from czsc.sensors import holds_concepts_effect, StocksDaySensor, ThsConceptsSensor, SignalsPerformance


__version__ = "0.9.15"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20230331"


def welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(f"CZSC环境变量："
          f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
          f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
          f"czsc_bi_change_th = {envs.get_bi_change_th()}")


if envs.get_welcome():
    welcome()


if get_dir_size(home_path) > pow(1024, 3) and envs.get_verbose():
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path 可以直接清空缓存")
