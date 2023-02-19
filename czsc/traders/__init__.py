# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 22:20
describe: 交易员（traders）
"""
from czsc.traders.base import CzscSignals, CzscTrader, generate_czsc_signals, check_signals_acc
from czsc.traders.performance import PairsPerformance, combine_holds_and_pairs, combine_dates_and_pairs


