# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/14 21:50
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import pandas as pd
from czsc.data.ts_cache import TsDataCache
from czsc.traders.ts_backtest import TsStocksBacktest
from examples import tactics


pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)

data_path = r"C:\ts_data"
dc = TsDataCache(data_path, sdt='2000-01-01', edt='20211216', verbose=False)


if __name__ == '__main__':
    tsb = TsStocksBacktest(dc=dc, strategy=tactics.trader_strategy_a, sdt='20140101', edt="20211216", init_n=1000*4)
    # tsb.batch_backtest('check')
    tsb.batch_backtest('index')
    # tsb.batch_backtest('train')
    # tsb.batch_backtest('valid')
    # tsb.batch_backtest('stock')

