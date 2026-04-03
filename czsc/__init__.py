"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""

from rs_czsc import WeightBacktest, daily_performance, top_drawdowns

from . import envs, traders, utils
from .core import CZSC, CzscJsonStrategy, CzscStrategyBase, Direction, Event, Freq, NewBar, Operate, Position, RawBar, Signal, ZS, format_standard_kline
from .eda import (
    cal_symbols_factor,
    cal_trade_price,
    cal_yearly_days,
    cross_sectional_strategy,
    dif_long_bear,
    judge_factor_direction,
    limit_leverage,
    make_price_features,
    mark_cta_periods,
    mark_volatility,
    min_max_limit,
    monotonicity,
    remove_beta_effects,
    rolling_layers,
    sma_long_bear,
    tsf_type,
    turnover_rate,
    twap,
    unify_weights,
    vwap,
    weights_simple_ensemble,
)
from .traders import (
    CzscSignals,
    CzscTrader,
    SignalsParser,
    check_signals_acc,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
)
from .utils import (
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
    "WeightBacktest",
    "daily_performance",
    "top_drawdowns",
    "envs",
    "traders",
    "utils",
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
    "CzscSignals",
    "CzscTrader",
    "SignalsParser",
    "check_signals_acc",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
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
    "svc",
    "fsa",
    "aphorism",
    "mock",
    "cwc",
    "CzscStrategyBase",
    "CzscJsonStrategy",
    "capture_warnings",
    "execute_with_warning_capture",
    "adjust_holding_weights",
    "log_strategy_info",
    "calculate_bi_info",
    "symbols_bi_infos",
    "plot_czsc_chart",
    "KlineChart",
    "check_kline_quality",
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
    "__version__",
    "__author__",
    "__email__",
    "__date__",
    "welcome",
]

__version__ = "0.10.12"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260308"

_LAZY_MODULES = {
    "svc": "czsc.svc",
    "fsa": "czsc.fsa",
    "aphorism": "czsc.aphorism",
    "mock": "czsc.mock",
    "cwc": "czsc.traders.cwc",
}

_LAZY_ATTRS = {
    "capture_warnings": ("czsc.utils.warning_capture", "capture_warnings"),
    "execute_with_warning_capture": ("czsc.utils.warning_capture", "execute_with_warning_capture"),
    "adjust_holding_weights": ("czsc.utils.trade", "adjust_holding_weights"),
    "log_strategy_info": ("czsc.utils.log", "log_strategy_info"),
    "calculate_bi_info": ("czsc.utils.bi_info", "calculate_bi_info"),
    "symbols_bi_infos": ("czsc.utils.bi_info", "symbols_bi_infos"),
    "plot_czsc_chart": ("czsc.utils.plotting.kline", "plot_czsc_chart"),
    "KlineChart": ("czsc.utils.plotting.kline", "KlineChart"),
    "check_kline_quality": ("czsc.utils.kline_quality", "check_kline_quality"),
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
