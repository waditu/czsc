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
from czsc import fsa
from czsc import utils
from czsc import traders
from czsc import sensors
from czsc import aphorism
from czsc import svc
from czsc import mock
from czsc.traders import rwc
from czsc.traders import cwc
from czsc.core import CZSC, Freq, Operate, Direction, Signal, Event, RawBar, NewBar, Position, ZS, format_standard_kline
from czsc.strategies import CzscStrategyBase, CzscJsonStrategy
from czsc.sensors import holds_concepts_effect, CTAResearch
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

# 警告信息捕获工具
from czsc.utils.warning_capture import (
    capture_warnings,
    execute_with_warning_capture,
)

# 交易日历工具
from czsc.py.calendar import (
    is_trading_date,
    next_trading_date,
    prev_trading_date,
    get_trading_dates,
)

from czsc.utils.trade import (
    adjust_holding_weights,
)

from czsc.utils.log import (
    log_strategy_info,
)

from czsc.utils.bi_info import (
    calculate_bi_info,
    symbols_bi_infos,
)

from czsc.features.utils import (
    is_event_feature,
    normalize_corr,
    feature_returns,
    feature_sectional_corr,
)

from czsc.utils.plotly_plot import (
    plot_czsc_chart,
    KlineChart
)

from czsc.utils.kline_quality import check_kline_quality
from czsc.traders import cwc

from czsc.py.bar_generator import (
    resample_bars,
    get_intraday_times,
    check_freq_and_market,
)

from czsc.eda import (
    remove_beta_effects,
    vwap,
    twap,
    cross_sectional_strategy,
    judge_factor_direction,
    monotonicity,
    min_max_limit,
    rolling_layers,
    cal_symbols_factor,
    weights_simple_ensemble,
    unify_weights,
    sma_long_bear,
    dif_long_bear,
    tsf_type,
    limit_leverage,
    cal_trade_price,
    mark_cta_periods,
    mark_volatility,
    cal_yearly_days,
    turnover_rate,
    make_price_features,
)


__version__ = "0.10.10"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260210"


def welcome():
    # from czsc import aphorism, envs
    from czsc.utils import get_dir_size, home_path

    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(
        f"CZSC环境变量：" f"czsc_min_bi_len = {envs.get_min_bi_len()}; " f"czsc_max_bi_num = {envs.get_max_bi_num()}; "
    )
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")


if get_dir_size(home_path) > pow(1024, 3):
    print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
