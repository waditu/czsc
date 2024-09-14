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
from czsc.sensors.feature import FixedNumberSelector
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
    stoploss_by_direction,
    get_ensemble_weight,
    long_short_equity,

    RedisWeightsClient,
    get_strategy_mates,
    get_heartbeat_time,
    clear_strategy,
    get_strategy_weights,

    OpensOptimize,
    ExitsOptimize,
)
from czsc.utils import (
    mac_address,
    overlap,
    to_arrow,

    format_standard_kline,

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
    code_namespace,
    freqs_sorted,
    x_round,
    import_by_name,
    create_grid_params,
    cal_trade_price,
    update_bbars,
    update_tbars,
    update_nxb,
    risk_free_returns,
    resample_to_daily,

    CrossSectionalPerformance,
    cross_sectional_ranker,
    cross_sectional_ic,
    SignalAnalyzer,
    SignalPerformance,
    daily_performance,
    rolling_daily_performance,
    weekly_performance,
    holds_performance,
    net_value_stats,
    subtract_fee,
    top_drawdowns,
    psi,

    home_path,
    DiskCache,
    disk_cache,
    clear_cache,
    get_dir_size,
    empty_cache_path,
    print_df_sample,
    index_composition,

    AliyunOSS,
    DataClient,
    set_url_token,
    get_url_token,

    optuna_study,
    optuna_good_params,

    generate_fernet_key,
    fernet_encrypt,
    fernet_decrypt,
)

# 交易日历工具
from czsc.utils.calendar import (
    is_trading_date,
    next_trading_date,
    prev_trading_date,
    get_trading_dates,
)

from czsc.utils.trade import (
    adjust_holding_weights,
)

# streamlit 量化分析组件
from czsc.utils.st_components import (
    show_daily_return,
    show_yearly_stats,
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
    show_stoploss_by_direction,
    show_cointegration,
    show_out_in_compare,
    show_optuna_study,
    show_drawdowns,
    show_rolling_daily_performance,
    show_event_return,
    show_psi,
    show_strategies_symbol,
    show_strategies_dailys,
    show_holds_backtest,
    show_symbols_corr,
    show_feature_returns,
    show_czsc_trader,
    show_strategies_recent,
    show_factor_value,
    show_code_editor,
    show_classify,
)

from czsc.utils.bi_info import (
    calculate_bi_info,
    symbols_bi_infos,
)

from czsc.utils.features import (
    normalize_feature,
    normalize_ts_feature,
    feture_cross_layering,
    find_most_similarity,
)

from czsc.features.utils import (
    is_event_feature,
    rolling_corr,
    rolling_rank,
    rolling_norm,
    rolling_qcut,
    rolling_compare,
    rolling_scale,
    rolling_slope,
    rolling_tanh,
    feature_adjust,
    normalize_corr,
    feature_to_weight,
    feature_returns,
    feature_sectional_corr,
)


from czsc.utils.kline_quality import (
    check_high_low,
    check_price_gap,
    check_abnormal_volume,
    check_zero_volume,
)


from czsc.utils.portfolio import (
    max_sharp,
)

from czsc.eda import (
    remove_beta_effects, vwap, twap,
    cross_sectional_strategy,
    judge_factor_direction,
    monotonicity,
    min_max_limit,
    rolling_layers,
)


__version__ = "0.9.59"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20240901"


def welcome():
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(
        f"CZSC环境变量："
        f"czsc_min_bi_len = {envs.get_min_bi_len()}; "
        f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
    )


if envs.get_welcome():
    welcome()


if get_dir_size(home_path) > pow(1024, 3):
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
