from __future__ import annotations

from types import ModuleType
from typing import Any

from . import envs as envs
from . import traders as traders
from . import utils as utils
from .core import (
    CZSC,
    Direction,
    Event,
    Freq,
    NewBar,
    Operate,
    Position,
    RawBar,
    Signal,
    ZS,
    format_standard_kline,
)
from .traders import (
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
    top_drawdowns,
    update_bbars,
    update_nxb,
    update_tbars,
    x_round,
    daily_performance,
)
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
from .features.utils import (
    feature_returns,
    feature_sectional_corr,
    is_event_feature,
    normalize_corr,
)
from .py.bar_generator import check_freq_and_market, get_intraday_times, resample_bars
from .py.calendar import get_trading_dates, is_trading_date, next_trading_date, prev_trading_date
from .sensors import CTAResearch, holds_concepts_effect
from .strategies import CzscJsonStrategy, CzscStrategyBase
from .utils.backtest_report import generate_backtest_report
from .utils.bi_info import calculate_bi_info, symbols_bi_infos
from .utils.kline_quality import check_kline_quality
from .utils.log import log_strategy_info
from .utils.plotting.kline import KlineChart, plot_czsc_chart
from .utils.trade import adjust_holding_weights
from .utils.warning_capture import capture_warnings, execute_with_warning_capture

# 来自可选 Rust 扩展，类型保持宽松
WeightBacktest: Any

__version__: str
__author__: str
__email__: str
__date__: str

# 延迟模块（运行时由 __getattr__ 注入）
svc: ModuleType
fsa: ModuleType
sensors: ModuleType
aphorism: ModuleType
mock: ModuleType
rwc: ModuleType
cwc: ModuleType

__all__ = [
    "envs",
    "traders",
    "utils",
    "CZSC",
    "Direction",
    "Event",
    "Freq",
    "NewBar",
    "Operate",
    "Position",
    "RawBar",
    "Signal",
    "ZS",
    "format_standard_kline",
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
    "top_drawdowns",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    "x_round",
    "daily_performance",
    "WeightBacktest",
    "svc",
    "fsa",
    "sensors",
    "aphorism",
    "mock",
    "rwc",
    "cwc",
    "cal_symbols_factor",
    "cal_trade_price",
    "cal_yearly_days",
    "cross_sectional_strategy",
    "dif_long_bear",
    "judge_factor_direction",
    "limit_leverage",
    "make_price_features",
    "mark_cta_periods",
    "mark_volatility",
    "min_max_limit",
    "monotonicity",
    "remove_beta_effects",
    "rolling_layers",
    "sma_long_bear",
    "tsf_type",
    "turnover_rate",
    "twap",
    "unify_weights",
    "vwap",
    "weights_simple_ensemble",
    "feature_returns",
    "feature_sectional_corr",
    "is_event_feature",
    "normalize_corr",
    "check_freq_and_market",
    "get_intraday_times",
    "resample_bars",
    "get_trading_dates",
    "is_trading_date",
    "next_trading_date",
    "prev_trading_date",
    "CTAResearch",
    "holds_concepts_effect",
    "CzscJsonStrategy",
    "CzscStrategyBase",
    "generate_backtest_report",
    "calculate_bi_info",
    "symbols_bi_infos",
    "check_kline_quality",
    "log_strategy_info",
    "KlineChart",
    "plot_czsc_chart",
    "adjust_holding_weights",
    "capture_warnings",
    "execute_with_warning_capture",
    "welcome",
]


def __getattr__(name: str) -> Any:
    ...


def welcome() -> None:
    ...
