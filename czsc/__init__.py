# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
from czsc import envs
from czsc import fsa
from czsc import utils
from czsc import traders
from czsc import sensors
from czsc import aphorism
from czsc.analyze import CZSC
from czsc.objects import Freq, Operate, Direction, Signal, Factor, Event, RawBar, NewBar, Position, ZS
from czsc.strategies import CzscStrategyBase, CzscJsonStrategy
from czsc.sensors import holds_concepts_effect, CTAResearch, EventMatchSensor
from czsc.sensors.feature import FixedNumberSelector, FeatureAnalyzeBase
from czsc.traders import (
    CzscTrader,
    CzscSignals,
    generate_czsc_signals,
    check_signals_acc,
    get_unique_signals,
    PairsPerformance,
    combine_holds_and_pairs,
    combine_dates_and_pairs,
    stock_holds_performance,
    DummyBacktest,
    SignalsParser,
    get_signals_config,
    get_signals_freqs,
    WeightBacktest,
    get_ensemble_weight,
    long_short_equity,
    RedisWeightsClient,
    OpensOptimize,
    ExitsOptimize,
)
from czsc.utils import (
    KlineChart,
    WordWriter,
    BarGenerator,
    freq_end_time,
    resample_bars,
    is_trading_time,
    get_intraday_times,
    check_freq_and_market,

    dill_dump,
    dill_load,
    read_json,
    save_json,
    get_sub_elements,
    get_py_namespace,
    freqs_sorted,
    x_round,
    import_by_name,
    create_grid_params,
    cal_trade_price,
    update_bbars,
    update_tbars,
    update_nbars,
    risk_free_returns,
    resample_to_daily,

    CrossSectionalPerformance,
    cross_sectional_ranker,
    cross_sectional_ic,
    SignalAnalyzer,
    SignalPerformance,
    daily_performance,
    weekly_performance,
    net_value_stats,
    subtract_fee,

    home_path,
    DiskCache,
    disk_cache,
    get_dir_size,
    empty_cache_path,
    print_df_sample,
    index_composition,

    AliyunOSS,
    DataClient,
    set_url_token,
    get_url_token,
)

# 交易日历工具
from czsc.utils.calendar import (
    is_trading_date,
    next_trading_date,
    prev_trading_date,
    get_trading_dates,
)

# streamlit 量化分析组件
from czsc.utils.st_components import (
    show_daily_return,
    show_splited_daily,
    show_monthly_return,
    show_correlation,
    show_sectional_ic,
    show_factor_returns,
    show_factor_layering,
    show_symbol_factor_layering,
    show_weight_backtest,
    show_ts_rolling_corr,
    show_ts_self_corr,
)

from czsc.utils.bi_info import (
    calculate_bi_info,
    symbols_bi_infos,
)

from czsc.utils.features import (
    normalize_feature,
    normalize_ts_feature,
    feture_cross_layering,
    rolling_rank,
    rolling_norm,
    rolling_qcut,
    rolling_compare,
    find_most_similarity,
)

__version__ = "0.9.41"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20240114"


def welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(
        f"CZSC环境变量："
        f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
        f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
        f"czsc_bi_change_th = {envs.get_bi_change_th()}"
    )


if envs.get_welcome():
    welcome()


if get_dir_size(home_path) > pow(1024, 3):
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path 可以直接清空缓存")
