"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""

from rs_czsc import (
    WeightBacktest,
    daily_performance,
    top_drawdowns,
)

from czsc import envs, traders, utils
from czsc.core import CZSC, ZS, Direction, Event, Freq, NewBar, Operate, Position, RawBar, Signal, format_standard_kline
from czsc.traders import (
    CzscSignals,
    CzscTrader,
    DummyBacktest,
    ExitsOptimize,
    OpensOptimize,
    PairsPerformance,
    SignalsParser,
    check_signals_acc,
    combine_dates_and_pairs,
    combine_holds_and_pairs,
    generate_czsc_signals,
    get_ensemble_weight,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
    stoploss_by_direction,
)
from czsc.utils import (
    AliyunOSS,
    DataClient,
    DiskCache,
    clear_cache,
    clear_expired_cache,
    code_namespace,
    create_grid_params,
    cross_sectional_ic,
    dill_dump,
    dill_load,
    disk_cache,
    empty_cache_path,
    fernet_decrypt,
    fernet_encrypt,
    freqs_sorted,
    generate_fernet_key,
    get_dir_size,
    get_py_namespace,
    get_sub_elements,
    get_url_token,
    holds_performance,
    home_path,
    import_by_name,
    index_composition,
    mac_address,
    overlap,
    print_df_sample,
    psi,
    read_json,
    resample_to_daily,
    risk_free_returns,
    rolling_daily_performance,
    save_json,
    set_url_token,
    ta,
    timeout_decorator,
    to_arrow,
    update_bbars,
    update_nxb,
    update_tbars,
    x_round,
)

__all__ = [
    # rs_czsc
    "WeightBacktest",
    "daily_performance",
    "top_drawdowns",
    # czsc 子模块
    "envs",
    "traders",
    "utils",
    # czsc.core
    "CZSC",
    "ZS",
    "Direction",
    "Event",
    "Freq",
    "NewBar",
    "Operate",
    "Position",
    "RawBar",
    "Signal",
    "format_standard_kline",
    # czsc.traders
    "CzscSignals",
    "CzscTrader",
    "DummyBacktest",
    "ExitsOptimize",
    "OpensOptimize",
    "PairsPerformance",
    "SignalsParser",
    "check_signals_acc",
    "combine_dates_and_pairs",
    "combine_holds_and_pairs",
    "generate_czsc_signals",
    "get_ensemble_weight",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
    "stoploss_by_direction",
    # czsc.utils
    "AliyunOSS",
    "DataClient",
    "DiskCache",
    "clear_cache",
    "clear_expired_cache",
    "code_namespace",
    "create_grid_params",
    "cross_sectional_ic",
    "dill_dump",
    "dill_load",
    "disk_cache",
    "empty_cache_path",
    "fernet_decrypt",
    "fernet_encrypt",
    "freqs_sorted",
    "generate_fernet_key",
    "get_dir_size",
    "get_py_namespace",
    "get_sub_elements",
    "get_url_token",
    "holds_performance",
    "home_path",
    "import_by_name",
    "index_composition",
    "mac_address",
    "overlap",
    "print_df_sample",
    "psi",
    "read_json",
    "resample_to_daily",
    "risk_free_returns",
    "rolling_daily_performance",
    "save_json",
    "set_url_token",
    "ta",
    "timeout_decorator",
    "to_arrow",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    "x_round",
    # 延迟加载模块
    "svc",
    "fsa",
    "sensors",
    "aphorism",
    "mock",
    "rwc",
    "cwc",
    # 延迟加载属性
    "CzscStrategyBase",
    "CzscJsonStrategy",
    "holds_concepts_effect",
    "CTAResearch",
    "capture_warnings",
    "execute_with_warning_capture",
    "is_trading_date",
    "next_trading_date",
    "prev_trading_date",
    "get_trading_dates",
    "adjust_holding_weights",
    "log_strategy_info",
    "calculate_bi_info",
    "symbols_bi_infos",
    "is_event_feature",
    "normalize_corr",
    "feature_returns",
    "feature_sectional_corr",
    "plot_czsc_chart",
    "KlineChart",
    "check_kline_quality",
    "resample_bars",
    "get_intraday_times",
    "check_freq_and_market",
    "remove_beta_effects",
    "vwap",
    "twap",
    "cross_sectional_strategy",
    "judge_factor_direction",
    "monotonicity",
    "min_max_limit",
    "rolling_layers",
    "cal_symbols_factor",
    "weights_simple_ensemble",
    "unify_weights",
    "sma_long_bear",
    "dif_long_bear",
    "tsf_type",
    "limit_leverage",
    "cal_trade_price",
    "mark_cta_periods",
    "mark_volatility",
    "cal_yearly_days",
    "turnover_rate",
    "make_price_features",
    "generate_backtest_report",
    # 模块元信息
    "__version__",
    "__author__",
    "__email__",
    "__date__",
    # 函数
    "welcome",
]

__version__ = "0.10.12"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260308"

# 延迟加载重型可选模块，避免影响导入速度
_LAZY_MODULES = {
    "svc": "czsc.svc",
    "fsa": "czsc.fsa",
    "sensors": "czsc.sensors",
    "aphorism": "czsc.aphorism",
    "mock": "czsc.mock",
    "rwc": "czsc.traders.rwc",
    "cwc": "czsc.traders.cwc",
}

# 延迟加载的属性映射：属性名 -> (模块路径, 属性名)
_LAZY_ATTRS = {
    # czsc.strategies
    "CzscStrategyBase": ("czsc.strategies", "CzscStrategyBase"),
    "CzscJsonStrategy": ("czsc.strategies", "CzscJsonStrategy"),
    # czsc.sensors
    "holds_concepts_effect": ("czsc.sensors", "holds_concepts_effect"),
    "CTAResearch": ("czsc.sensors", "CTAResearch"),
    # czsc.utils.warning_capture
    "capture_warnings": ("czsc.utils.warning_capture", "capture_warnings"),
    "execute_with_warning_capture": ("czsc.utils.warning_capture", "execute_with_warning_capture"),
    # czsc.py.calendar
    "is_trading_date": ("czsc.py.calendar", "is_trading_date"),
    "next_trading_date": ("czsc.py.calendar", "next_trading_date"),
    "prev_trading_date": ("czsc.py.calendar", "prev_trading_date"),
    "get_trading_dates": ("czsc.py.calendar", "get_trading_dates"),
    # czsc.utils.trade
    "adjust_holding_weights": ("czsc.utils.trade", "adjust_holding_weights"),
    # czsc.utils.log
    "log_strategy_info": ("czsc.utils.log", "log_strategy_info"),
    # czsc.utils.bi_info
    "calculate_bi_info": ("czsc.utils.bi_info", "calculate_bi_info"),
    "symbols_bi_infos": ("czsc.utils.bi_info", "symbols_bi_infos"),
    # czsc.features.utils
    "is_event_feature": ("czsc.features.utils", "is_event_feature"),
    "normalize_corr": ("czsc.features.utils", "normalize_corr"),
    "feature_returns": ("czsc.features.utils", "feature_returns"),
    "feature_sectional_corr": ("czsc.features.utils", "feature_sectional_corr"),
    # czsc.utils.plotting.kline
    "plot_czsc_chart": ("czsc.utils.plotting.kline", "plot_czsc_chart"),
    "KlineChart": ("czsc.utils.plotting.kline", "KlineChart"),
    # czsc.utils.kline_quality
    "check_kline_quality": ("czsc.utils.kline_quality", "check_kline_quality"),
    # czsc.py.bar_generator
    "resample_bars": ("czsc.py.bar_generator", "resample_bars"),
    "get_intraday_times": ("czsc.py.bar_generator", "get_intraday_times"),
    "check_freq_and_market": ("czsc.py.bar_generator", "check_freq_and_market"),
    # czsc.eda
    "remove_beta_effects": ("czsc.eda", "remove_beta_effects"),
    "vwap": ("czsc.eda", "vwap"),
    "twap": ("czsc.eda", "twap"),
    "cross_sectional_strategy": ("czsc.eda", "cross_sectional_strategy"),
    "judge_factor_direction": ("czsc.eda", "judge_factor_direction"),
    "monotonicity": ("czsc.eda", "monotonicity"),
    "min_max_limit": ("czsc.eda", "min_max_limit"),
    "rolling_layers": ("czsc.eda", "rolling_layers"),
    "cal_symbols_factor": ("czsc.eda", "cal_symbols_factor"),
    "weights_simple_ensemble": ("czsc.eda", "weights_simple_ensemble"),
    "unify_weights": ("czsc.eda", "unify_weights"),
    "sma_long_bear": ("czsc.eda", "sma_long_bear"),
    "dif_long_bear": ("czsc.eda", "dif_long_bear"),
    "tsf_type": ("czsc.eda", "tsf_type"),
    "limit_leverage": ("czsc.eda", "limit_leverage"),
    "cal_trade_price": ("czsc.eda", "cal_trade_price"),
    "mark_cta_periods": ("czsc.eda", "mark_cta_periods"),
    "mark_volatility": ("czsc.eda", "mark_volatility"),
    "cal_yearly_days": ("czsc.eda", "cal_yearly_days"),
    "turnover_rate": ("czsc.eda", "turnover_rate"),
    "make_price_features": ("czsc.eda", "make_price_features"),
    # czsc.utils.backtest_report
    "generate_backtest_report": ("czsc.utils.backtest_report", "generate_backtest_report"),
}


def __getattr__(name):
    import importlib

    if name in _LAZY_MODULES:
        module = importlib.import_module(_LAZY_MODULES[name])
        globals()[name] = module
        return module

    if name in _LAZY_ATTRS:
        mod_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(mod_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr

    raise AttributeError(f"module 'czsc' has no attribute {name!r}")


def welcome():
    from czsc import aphorism

    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(f"CZSC环境变量：czsc_min_bi_len = {envs.get_min_bi_len()}; czsc_max_bi_num = {envs.get_max_bi_num()}; ")
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")


# if get_dir_size(home_path) > pow(1024, 3):
#     print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
