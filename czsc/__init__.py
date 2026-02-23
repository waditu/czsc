# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2019/10/29 15:01
"""
# 尝试从 rs_czsc 导入，失败则使用 Python 版本
try:
    from rs_czsc import (
        daily_performance,
        top_drawdowns,
        # python版本：from czsc.traders.weight_backtest import WeightBacktest
        WeightBacktest,
    )
except ImportError:
    # 回退到 Python 版本
    from czsc.core import WeightBacktest
    # daily_performance 和 top_drawdown 在 Python 版本中的位置
    from czsc.utils import daily_performance, top_drawdowns

from czsc import envs
from czsc import utils
from czsc import traders
from czsc.core import CZSC, Freq, Operate, Direction, Signal, Event, RawBar, NewBar, Position, ZS, format_standard_kline
from czsc.utils import ta
from czsc.traders import (
    CzscTrader,
    CzscSignals,
    generate_czsc_signals,
    check_signals_acc,
    get_unique_signals,
    PairsPerformance,
    combine_holds_and_pairs,
    combine_dates_and_pairs,
    DummyBacktest,
    SignalsParser,
    get_signals_config,
    get_signals_freqs,
    stoploss_by_direction,
    get_ensemble_weight,
    OpensOptimize,
    ExitsOptimize,
)

from czsc.utils import (
    timeout_decorator,
    mac_address,
    overlap,
    to_arrow,
    dill_dump,
    dill_load,
    read_json,
    save_json,
    get_sub_elements,
    get_py_namespace,
    code_namespace,
    freqs_sorted,
    x_round,
    import_by_name,
    create_grid_params,
    update_bbars,
    update_tbars,
    update_nxb,
    risk_free_returns,
    resample_to_daily,
    cross_sectional_ic,
    rolling_daily_performance,
    holds_performance,
    psi,
    home_path,
    DiskCache,
    disk_cache,
    clear_cache,
    clear_expired_cache,
    get_dir_size,
    empty_cache_path,
    print_df_sample,
    index_composition,
    AliyunOSS,
    DataClient,
    set_url_token,
    get_url_token,
    generate_fernet_key,
    fernet_encrypt,
    fernet_decrypt,
)


__version__ = "0.10.10"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260210"

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
    'CzscStrategyBase': ('czsc.strategies', 'CzscStrategyBase'),
    'CzscJsonStrategy': ('czsc.strategies', 'CzscJsonStrategy'),
    # czsc.sensors
    'holds_concepts_effect': ('czsc.sensors', 'holds_concepts_effect'),
    'CTAResearch': ('czsc.sensors', 'CTAResearch'),
    # czsc.utils.warning_capture
    'capture_warnings': ('czsc.utils.warning_capture', 'capture_warnings'),
    'execute_with_warning_capture': ('czsc.utils.warning_capture', 'execute_with_warning_capture'),
    # czsc.py.calendar
    'is_trading_date': ('czsc.py.calendar', 'is_trading_date'),
    'next_trading_date': ('czsc.py.calendar', 'next_trading_date'),
    'prev_trading_date': ('czsc.py.calendar', 'prev_trading_date'),
    'get_trading_dates': ('czsc.py.calendar', 'get_trading_dates'),
    # czsc.utils.trade
    'adjust_holding_weights': ('czsc.utils.trade', 'adjust_holding_weights'),
    # czsc.utils.log
    'log_strategy_info': ('czsc.utils.log', 'log_strategy_info'),
    # czsc.utils.bi_info
    'calculate_bi_info': ('czsc.utils.bi_info', 'calculate_bi_info'),
    'symbols_bi_infos': ('czsc.utils.bi_info', 'symbols_bi_infos'),
    # czsc.features.utils
    'is_event_feature': ('czsc.features.utils', 'is_event_feature'),
    'normalize_corr': ('czsc.features.utils', 'normalize_corr'),
    'feature_returns': ('czsc.features.utils', 'feature_returns'),
    'feature_sectional_corr': ('czsc.features.utils', 'feature_sectional_corr'),
    # czsc.utils.plotting.kline
    'plot_czsc_chart': ('czsc.utils.plotting.kline', 'plot_czsc_chart'),
    'KlineChart': ('czsc.utils.plotting.kline', 'KlineChart'),
    # czsc.utils.kline_quality
    'check_kline_quality': ('czsc.utils.kline_quality', 'check_kline_quality'),
    # czsc.py.bar_generator
    'resample_bars': ('czsc.py.bar_generator', 'resample_bars'),
    'get_intraday_times': ('czsc.py.bar_generator', 'get_intraday_times'),
    'check_freq_and_market': ('czsc.py.bar_generator', 'check_freq_and_market'),
    # czsc.eda
    'remove_beta_effects': ('czsc.eda', 'remove_beta_effects'),
    'vwap': ('czsc.eda', 'vwap'),
    'twap': ('czsc.eda', 'twap'),
    'cross_sectional_strategy': ('czsc.eda', 'cross_sectional_strategy'),
    'judge_factor_direction': ('czsc.eda', 'judge_factor_direction'),
    'monotonicity': ('czsc.eda', 'monotonicity'),
    'min_max_limit': ('czsc.eda', 'min_max_limit'),
    'rolling_layers': ('czsc.eda', 'rolling_layers'),
    'cal_symbols_factor': ('czsc.eda', 'cal_symbols_factor'),
    'weights_simple_ensemble': ('czsc.eda', 'weights_simple_ensemble'),
    'unify_weights': ('czsc.eda', 'unify_weights'),
    'sma_long_bear': ('czsc.eda', 'sma_long_bear'),
    'dif_long_bear': ('czsc.eda', 'dif_long_bear'),
    'tsf_type': ('czsc.eda', 'tsf_type'),
    'limit_leverage': ('czsc.eda', 'limit_leverage'),
    'cal_trade_price': ('czsc.eda', 'cal_trade_price'),
    'mark_cta_periods': ('czsc.eda', 'mark_cta_periods'),
    'mark_volatility': ('czsc.eda', 'mark_volatility'),
    'cal_yearly_days': ('czsc.eda', 'cal_yearly_days'),
    'turnover_rate': ('czsc.eda', 'turnover_rate'),
    'make_price_features': ('czsc.eda', 'make_price_features'),
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

    print(
        f"CZSC环境变量：" f"czsc_min_bi_len = {envs.get_min_bi_len()}; " f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
    )
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")


# if get_dir_size(home_path) > pow(1024, 3):
#     print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
