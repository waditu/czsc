# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 22:20
describe: 交易员（traders）：使用 CZSC 分析工具进行择时策略的开发，交易等
"""
from czsc.traders.base import CzscSignals, CzscTrader, generate_czsc_signals, check_signals_acc, get_unique_signals

from czsc.traders.performance import (
    PairsPerformance,
    combine_holds_and_pairs,
    combine_dates_and_pairs,
)
from czsc.traders.dummy import DummyBacktest
from czsc.traders.sig_parse import SignalsParser, get_signals_config, get_signals_freqs
from czsc.traders.weight_backtest import get_ensemble_weight, stoploss_by_direction
# Import WeightBacktest from core to avoid circular import
# from czsc.traders.weight_backtest import WeightBacktest

# 延迟加载的属性映射
_LAZY_ATTRS = {
    'OpensOptimize': ('czsc.traders.optimize', 'OpensOptimize'),
    'ExitsOptimize': ('czsc.traders.optimize', 'ExitsOptimize'),
    'RedisWeightsClient': ('czsc.traders.rwc', 'RedisWeightsClient'),
    'get_strategy_mates': ('czsc.traders.rwc', 'get_strategy_mates'),
    'get_heartbeat_time': ('czsc.traders.rwc', 'get_heartbeat_time'),
    'clear_strategy': ('czsc.traders.rwc', 'clear_strategy'),
    'get_strategy_weights': ('czsc.traders.rwc', 'get_strategy_weights'),
    'get_strategy_latest': ('czsc.traders.rwc', 'get_strategy_latest'),
}


def __getattr__(name):
    if name in _LAZY_ATTRS:
        import importlib
        mod_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(mod_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
