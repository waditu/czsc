# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 22:20
describe: 交易员（traders）的主要职能是依据感应系统（sensors）的输出来调整仓位，以此应对变幻无常的市场风险。
"""

from .advanced import CzscAdvancedTrader, create_advanced_trader, CzscDummyTrader
from .ts_backtest import TsStocksBacktest
from .performance import TradersPerformance, PairsPerformance
from .ts_simulator import TradeSimulator
from .utils import trader_fast_backtest


