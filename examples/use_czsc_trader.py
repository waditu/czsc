# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/1/30 13:32
describe: CzscTrader 使用案例
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
import pandas as pd
from typing import List
from czsc.traders.base import CzscTrader
from czsc.utils.bar_generator import BarGenerator, RawBar
from czsc.strategies import CzscStrategyExample1, CzscStrategyBase
from czsc.data.ts_cache import TsDataCache


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='30min',
                          sdt='20151101', edt='20210101', adj='qfq', raw_bar=True)

if __name__ == '__main__':
    tactic = CzscStrategyExample1(symbol="000001.SHSE")
    tactic.trade_replay(bars, res_path=r"C:\ts_data_czsc\trade_replay_test_20170101B", sdt='20170101')
