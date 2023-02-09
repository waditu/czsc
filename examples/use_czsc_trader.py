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
from examples.strategies.czsc_strategy_sma5 import CzscStrategySMA5

os.environ['czsc_verbose'] = '1'


def use_czsc_trader_by_tushare():
    from czsc.data.ts_cache import TsDataCache
    dc = TsDataCache(r'C:\ts_data', sdt='2010-01-01', edt='20211209')

    symbol = '000001.SZ'
    bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='5min',
                              sdt='20151101', edt='20210101', adj='hfq', raw_bar=True)

    tactic = CzscStrategySMA5(symbol="000001.SHSE")
    trader = tactic.init_trader(bars, sdt='20200801')
    # trader = tactic.replay(bars, res_path=r"C:\ts_data_czsc\trade_replay_test_c", sdt='20170101')
    print(trader.positions[0].evaluate_pairs())


def use_czsc_trader_by_qmt():
    from czsc.connectors import qmt_connector as qmc

    symbol = '000001.SZ'
    bars = qmc.get_kline(symbol, period='5m', start_time='20151101', end_time='20210101',
                         dividend_type='back', download_hist=True, df=False)
    tactic = CzscStrategySMA5(symbol="000001.SHSE", freqs=['5分钟', '15分钟', '30分钟', '日线'])
    trader = tactic.init_trader(bars, sdt='20200801')
    # trader = tactic.replay(bars, res_path=r"C:\ts_data_czsc\trade_replay_test_c", sdt='20170101')
    print(trader.positions[0].evaluate_pairs())


