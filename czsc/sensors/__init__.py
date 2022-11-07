# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/28 20:51
describe: 感应系统
"""
from czsc.sensors.plates import ThsConceptsSensor
from czsc.sensors.stocks import StocksDaySensor
from czsc.sensors.utils import (
    check_signals_acc,
    generate_signals,
    generate_stocks_signals,
    generate_symbol_signals,
    read_cached_signals,
    turn_over_rate,
    discretizer,
    compound_returns,
    get_index_beta
)


