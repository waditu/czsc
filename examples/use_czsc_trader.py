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
    from czsc.strategies import CzscStocksBeta
    from czsc.data.ts_cache import TsDataCache
    dc = TsDataCache(r'C:\ts_data', sdt='2010-01-01', edt='20211209')

    # 获取K线数据，这里使用的是tushare的数据，也可以使用其他数据源。必须返回 RawBar 对象的列表
    symbol = '000001.SZ'
    bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                              sdt='20151101', edt='20210101', adj='hfq', raw_bar=True)

    # 实例化策略对象，这里使用的是 CzscStocksBeta 策略，也可以使用其他策略
    tactic = CzscStocksBeta(symbol=symbol)

    # 调用策略对象的 init_trader 方法，传入K线数据，获取 CzscTrader 对象实例
    # sdt = '20200801' 表示从 2020-08-01 开始回测，在这个时候之后的交易会被记录在持仓对象中
    trader = tactic.init_trader(bars, sdt='20200801')

    # 查看所有持仓策略的交易绩效
    for pos in trader.positions:
        print(pos.name, pos.evaluate(trade_dir='多空'))

    # 也可以调用策略基类中 replay 方法执行策略回放，查看策略交易的HTML快照
    trader = tactic.replay(bars, res_path=r"C:\ts_data_czsc\trade_replay_test_c", sdt='20170101', refresh=True)
    print(trader.positions[0].evaluate_pairs())


def use_czsc_trader_by_qmt():
    from czsc.connectors import qmt_connector as qmc

    symbol = '000001.SZ'
    tactic = CzscStrategySMA5(symbol=symbol)
    bars = qmc.get_raw_bars(symbol, freq=tactic.sorted_freqs[0], sdt='20151101', edt='20210101', fq="后复权")
    print(bars[-1])

    # 初始化交易对象
    trader = tactic.init_trader(bars, sdt='20200801')

    # 执行策略回放，查看交易结果
    for i in range(len(trader.positions)):
        print(trader.positions[i].evaluate_pairs())

    # # 执行策略回放，生成交易快照文件
    # trader = tactic.replay(bars, res_path=r"C:\ts_data_czsc\trade_replay_test", sdt='20170101', refresh=True)
    # print(trader.positions[0].evaluate_pairs())


def example_qmt_manager():
    """使用 QmtTradeManager 进行交易"""
    from czsc.connectors import qmt_connector as qmc

    symbols = ['600000.SH', '600004.SH', '600006.SH', '600007.SH']
    manager = qmc.QmtTradeManager(mini_qmt_dir=r'D:\国金QMT交易端模拟\userdata_mini', account_id='55002763',
                                  symbols=symbols, symbol_max_pos=0.3, strategy=CzscStrategySMA5)
    manager.run()






