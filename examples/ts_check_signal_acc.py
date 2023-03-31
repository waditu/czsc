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
from czsc.traders.base import CzscTrader, check_signals_acc
from czsc import signals


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 定义需要检查的信号
    # s.update(signals.cxt_zhong_shu_gong_zhen_V221221(cat.kas['15分钟'], di=1))
    s.update(signals.cxt_zhong_shu_gong_zhen_V221221(cat))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)

    # 也可以指定信号的K线周期，比如只检查日线信号
    # check_signals_acc(bars, get_signals, freqs=['日线'])






