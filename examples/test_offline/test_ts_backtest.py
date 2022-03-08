# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/24 14:17
describe: TsBacktest 单元测试
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import pandas as pd
from czsc.data.ts_cache import TsDataCache
from czsc.traders.ts_backtest import TsStocksBacktest, TraderPerformance
from examples import tactics

df = pd.read_excel(r"C:\ts_data\trader_stocks_v2_a_t0\trader_stocks_v2_a_t0_check_long_pairs.xlsx")


tp = TraderPerformance(df)
