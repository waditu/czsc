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

from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CZSC
from czsc.objects import Signal, Freq
from czsc.sensors.utils import check_signals_acc
from czsc.signals.signals import get_s_like_bs

data_path = r'D:\research\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209', verbose=True)

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='5min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)

signals = [
    Signal("5分钟_倒9笔_类买卖点_类一买_任意_任意_0"),
    Signal("5分钟_倒9笔_类买卖点_类二买_任意_任意_0"),
    Signal("5分钟_倒9笔_类买卖点_类三买_任意_任意_0"),
    Signal("5分钟_倒9笔_类买卖点_类一卖_任意_任意_0"),
    Signal("5分钟_倒9笔_类买卖点_类二卖_任意_任意_0"),
    Signal("5分钟_倒9笔_类买卖点_类三卖_任意_任意_0"),
]


def get_signals(c: CZSC) -> OrderedDict:
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    if c.freq == Freq.F5:
        s.update(get_s_like_bs(c, di=9))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, signals, freqs=['15分钟', '30分钟'], get_signals=get_signals)






