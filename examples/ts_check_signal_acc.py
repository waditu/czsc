# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: 验证信号计算的准确性，仅适用于缠论笔相关的信号，
          技术指标构建的信号，用这个工具检查不是那么方便
"""
import sys
sys.path.insert(0, '..')
import os
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CzscAdvancedTrader
from czsc.objects import Signal, Freq
from czsc.sensors.utils import check_signals_acc
from czsc import signals


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # signals.update_ma_cache(cat.kas['15分钟'], ma_type='SMA', timeperiod=5)
    # signals.update_ma_cache(cat.kas['15分钟'], ma_type='SMA', timeperiod=10)
    s.update(signals.bar_mean_amount_V221112(cat.kas['15分钟'], di=2, n=20))
    # s.update(signals.bar_zdt_V221111(cat, '15分钟', di=2))

    # # 使用缓存来更新信号的方法
    # signals.update_macd_cache(cat.kas['15分钟'])
    # s.update(signals.tas_macd_direct_V221106(cat.kas['15分钟'], di=1))
    # signals.update_boll_cache(cat.kas['15分钟'])
    # s.update(signals.tas_boll_power_V221112(cat.kas['15分钟'], di=1))
    return s


def trader_strategy_base(symbol):
    tactic = {
        "symbol": symbol,
        "base_freq": '15分钟',
        "freqs": ['30分钟', '60分钟', '日线'],
        "get_signals": get_signals,
        "signals_n": 0,
    }
    return tactic


if __name__ == '__main__':
    # 直接查看全部信号的隔日快照
    check_signals_acc(bars, strategy=trader_strategy_base)

    # 查看指定信号的隔日快照
    # signals = [
    #     Signal("5分钟_倒9笔_类买卖点_类一买_任意_任意_0"),
    #     Signal("5分钟_倒9笔_类买卖点_类一卖_任意_任意_0"),
    # ]
    # check_signals_acc(bars, signals=signals, get_signals=get_signals)






