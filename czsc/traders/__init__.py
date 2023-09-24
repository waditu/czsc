# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 22:20
describe: 交易员（traders）：使用 CZSC 分析工具进行择时策略的开发，交易等
"""
from czsc.traders.base import (
    CzscSignals, CzscTrader, generate_czsc_signals, check_signals_acc, get_unique_signals
)

from czsc.traders.performance import (
    PairsPerformance, combine_holds_and_pairs, combine_dates_and_pairs, stock_holds_performance
)
from czsc.traders.dummy import DummyBacktest
from czsc.traders.sig_parse import SignalsParser, get_signals_config, get_signals_freqs
from czsc.traders.weight_backtest import WeightBacktest, get_ensemble_weight, long_short_equity
from czsc.traders.rwc import RedisWeightsClient
from czsc.traders.optimize import OpensOptimize, ExitsOptimize
