# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: 验证信号计算的准确性
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CZSC
from czsc.objects import Signal, Freq
from czsc.sensors.utils import check_signals_acc
from czsc.signals.signals import get_s_like_bs

os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='5min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)

def get_signals(c: CZSC) -> OrderedDict:
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    if c.freq == Freq.F5:
        s.update(get_s_like_bs(c, di=9))
    return s


if __name__ == '__main__':
    # 直接查看全部信号的隔日快照
    check_signals_acc(bars, get_signals=get_signals)

    # 查看指定信号的隔日快照
    signals = [
        Signal("5分钟_倒9笔_类买卖点_类一买_任意_任意_0"),
        Signal("5分钟_倒9笔_类买卖点_类一卖_任意_任意_0"),
    ]
    check_signals_acc(bars, signals=signals, get_signals=get_signals)






