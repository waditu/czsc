# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 21:07
"""
from tqdm import tqdm
from czsc.traders.advanced import CzscAdvancedTrader
from czsc.signals import get_default_signals
from czsc.utils import KlineGenerator
from czsc.objects import Signal, Factor, Event, Operate, PositionLong
from test.test_analyze import read_1min

def test_advanced_trader_with_t0():
    bars = read_1min()
    kg = KlineGenerator(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in tqdm(bars[:-10000], desc='init kg'):
        kg.update(row)

    events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="5分钟三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="1分钟一卖", signals_all=[Signal("1分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟一卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="5分钟三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
        ]),
    ]
    long_pos = PositionLong(symbol='000001.SH', hold_long_a=1, hold_long_b=1, hold_long_c=1, T0=True)
    ct = CzscAdvancedTrader(kg=kg, get_signals=get_default_signals, long_events=events, long_pos=long_pos)
    assert len(ct.s) == 215
    for row in tqdm(bars[-10000:], desc="trade"):
        ct.update(row)
        if long_pos.pos_changed:
            print(" : op    : ", long_pos.operates[-1])

def test_advanced_trader_without_t0():
    bars = read_1min()
    kg = KlineGenerator(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in tqdm(bars[:150000], desc='init kg'):
        kg.update(row)

    events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="5分钟三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="1分钟一卖", signals_all=[Signal("1分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟一卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="5分钟三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
        ]),
    ]
    long_pos = PositionLong(symbol='000001.SH', hold_long_a=1, hold_long_b=1, hold_long_c=1, T0=False)
    ct = CzscAdvancedTrader(kg=kg, get_signals=get_default_signals, long_events=events, long_pos=long_pos)
    assert len(ct.s) == 215
    for row in tqdm(bars[150000:], desc="trade"):
        ct.update(row)
        if long_pos.pos_changed:
            print(" : op    : ", long_pos.operates[-1])
