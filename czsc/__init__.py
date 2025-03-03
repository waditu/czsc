# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
import sys
from .lazy import LazyModule

__version__ = "0.9.63"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20250101"

# 进行懒加载模块替换
old_obj = sys.modules.get(__name__)

# 子模块列表
submodules = [
    "envs", "fsa", "utils", "traders", "sensors", "aphorism", "analyze",
    "strategies", "features", "eda", "objects"
]

# 子模块中的属性映射
submod_attrs = {
    "objects": [
        "Freq", "Operate", "Direction", "Signal", "Factor", "Event",
        "RawBar", "NewBar", "Position", "ZS"
    ],
    "analyze": [
        "CZSC"
    ],
    "traders": [
        "CzscTrader", "CzscSignals", "generate_czsc_signals",
        "check_signals_acc", "get_unique_signals", "PairsPerformance",
        "combine_holds_and_pairs", "combine_dates_and_pairs", "DummyBacktest",
        "SignalsParser", "get_signals_config", "get_signals_freqs",
        "stoploss_by_direction", "get_ensemble_weight",
        "OpensOptimize", "ExitsOptimize", "rwc", "cwc"
    ],
    "traders.rwc": [
        "RedisWeightsClient", "get_strategy_mates", "get_strategy_names",
        "get_heartbeat_time", "clear_strategy", "get_strategy_weights",
        "get_strategy_latest"
    ],
    "utils": [
        "timeout_decorator", "mac_address", "overlap", "to_arrow",
        "format_standard_kline", "KlineChart", "WordWriter", "BarGenerator",
        "freq_end_time", "resample_bars", "is_trading_time", "get_intraday_times",
        "check_freq_and_market", "dill_dump", "dill_load", "read_json", "save_json",
        "get_sub_elements", "get_py_namespace", "code_namespace", "freqs_sorted",
        "x_round", "import_by_name", "create_grid_params", "cal_trade_price",
        "update_bbars", "update_tbars", "update_nxb", "risk_free_returns",
        "resample_to_daily", "cross_sectional_ranker", "cross_sectional_ic",
        "rolling_daily_performance", "holds_performance", "subtract_fee", "psi",
        "home_path", "DiskCache", "disk_cache", "clear_cache", "get_dir_size",
        "empty_cache_path", "print_df_sample", "index_composition", "AliyunOSS",
        "DataClient", "set_url_token", "get_url_token", "optuna_study",
        "optuna_good_params", "generate_fernet_key", "fernet_encrypt",
        "fernet_decrypt", "ta"
    ],
    "utils.calendar": [
        "is_trading_date", "next_trading_date", "prev_trading_date",
        "get_trading_dates"
    ],
    "utils.trade": [
        "adjust_holding_weights"
    ],
    "utils.st_components": [
        "show_daily_return", "show_yearly_stats", "show_splited_daily",
        "show_monthly_return", "show_correlation", "show_corr_graph",
        "show_sectional_ic", "show_factor_layering", "show_symbol_factor_layering",
        "show_weight_backtest", "show_ts_rolling_corr", "show_ts_self_corr",
        "show_stoploss_by_direction", "show_cointegration", "show_out_in_compare",
        "show_optuna_study", "show_drawdowns", "show_rolling_daily_performance",
        "show_event_return", "show_psi", "show_strategies_symbol",
        "show_strategies_dailys", "show_holds_backtest", "show_symbols_corr",
        "show_feature_returns", "show_czsc_trader", "show_strategies_recent",
        "show_factor_value", "show_code_editor", "show_classify",
        "show_df_describe", "show_date_effect", "show_weight_distribution"
    ],
    "utils.bi_info": [
        "calculate_bi_info", "symbols_bi_infos"
    ],
    "utils.features": [
        "normalize_feature", "normalize_ts_feature", "feature_cross_layering",
        "find_most_similarity"
    ],
    "features.utils": [
        "is_event_feature", "rolling_corr", "rolling_rank", "rolling_norm",
        "rolling_qcut", "rolling_compare", "rolling_scale", "rolling_slope",
        "rolling_tanh", "feature_adjust", "normalize_corr", "feature_to_weight",
        "feature_returns", "feature_sectional_corr"
    ],
    "utils.kline_quality": [
        "check_kline_quality"
    ],
    "utils.portfolio": [
        "max_sharp"
    ],
    "eda": [
        "remove_beta_effects", "vwap", "twap", "cross_sectional_strategy",
        "judge_factor_direction", "monotonicity", "min_max_limit",
        "rolling_layers", "cal_symbols_factor", "weights_simple_ensemble",
        "unify_weights", "sma_long_bear", "dif_long_bear", "tsf_type",
        "limit_leverage"
    ],
    "strategies": [
        "CzscStrategyBase", "CzscJsonStrategy"
    ],
    "sensors": [
        "holds_concepts_effect", "CTAResearch", "EventMatchSensor",
        "FixedNumberSelector"
    ]
}

# 创建懒加载模块并替换当前模块
lazy_module = LazyModule(
    name=__name__,
    submodules=submodules,
    submod_attrs=submod_attrs,
    old_obj=old_obj
)

# 替换系统模块字典中的模块
sys.modules[__name__] = lazy_module


def welcome():
    """打印欢迎信息"""
    # 使用局部导入避免循环引用
    from importlib import import_module
    aphorism = import_module("czsc.aphorism")
    envs = import_module("czsc.envs")

    # 导入 get_dir_size 和 home_path
    utils = import_module("czsc.utils")
    get_dir_size = utils.get_dir_size
    home_path = utils.home_path

    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(
        f"CZSC环境变量："
        f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
        f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
    )
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")


# 检查缓存目录大小 - 使用局部导入避免循环引用
try:
    from importlib import import_module

    utils = import_module("czsc.utils")
    if utils.get_dir_size(utils.home_path) > pow(1024, 3):
        print(f"{utils.home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
except ImportError:
    # 忽略初始导入错误，因为这不是核心功能
    pass