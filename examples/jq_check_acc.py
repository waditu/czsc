# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/26 17:48
describe: 验证信号计算的准确性
"""
from collections import OrderedDict
from czsc.data import jq
from czsc import CZSC
from czsc.objects import Signal, Freq
from czsc.sensors.utils import check_signals_acc
from czsc.signals.signals import get_s_like_bs


symbol = '000001.XSHG'
f1_raw_bars = jq.get_kline_period(symbol=symbol, freq='1min', start_date='20181101', end_date='20210101')

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
    check_signals_acc(f1_raw_bars, signals, freqs=['5分钟', '15分钟'], get_signals=get_signals)






