# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/26 11:43
"""
import os
from czsc.objects import Signal, Factor, Event, Operate, Freq
from czsc.cobra import backtest as bt
from test.test_analyze import read_1min

cur_path = os.path.split(os.path.realpath(__file__))[0]
kline = read_1min()


def test_cobra_backtest():
    bars = read_1min()
    signals = bt.generate_signals(bars, len(bars)-10000, bt.get_default_signals)

    long_open_event = Event(name="开多", operate=Operate.LO, factors=[
        Factor(name="5分钟三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
    ])
    long_exit_event = Event(name="平多", operate=Operate.LE, factors=[
        Factor(name="1分钟一卖", signals_all=[Signal("1分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
        Factor(name="5分钟一卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
        Factor(name="5分钟二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
        Factor(name="5分钟三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
    ])
    pairs, pf = bt.long_trade_simulator(signals, long_open_event, long_exit_event, T0=True, verbose=True)
    assert len(pairs) == 65
    assert pf['累计收益（%）'] > pf['基准收益（%）']

    event = Event(name="多头过滤", operate=Operate.LO, factors=[
        Factor(name="多头过滤", signals_all=[
            Signal("30分钟_倒1K_DIF多空_多头_任意_任意_0"),
        ]),
    ])
    pairs, pf = bt.one_event_estimator(signals, event)
    assert len(pairs) == 8
    assert pf['累计收益（%）'] > pf['基准收益（%）']
