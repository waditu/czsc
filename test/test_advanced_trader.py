# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 21:07
"""
import pandas as pd
from tqdm import tqdm
from collections import OrderedDict
from czsc import signals
from czsc.traders.advanced import CzscAdvancedTrader, BarGenerator
from czsc.objects import Signal, Factor, Event, Operate, PositionLong, PositionShort
from test.test_analyze import read_1min, read_daily


def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    for _, c in cat.kas.items():
        s.update(signals.bxt.get_s_like_bs(c, di=1))

    if cat.long_pos:
        s.update(signals.cat.get_s_position(cat, cat.long_pos))
    if cat.short_pos:
        s.update(signals.cat.get_s_position(cat, cat.short_pos))
    return s


def trader_strategy_test(symbol, T0=False):
    """A股市场择时策略样例，支持按交易标的独立设置参数

    :param symbol:
    :param T0: 是否允许T0交易
    :return:
    """
    long_events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="5分钟一买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
            Factor(name="1分钟一买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
        ]),

        Event(name="加多1", operate=Operate.LA1, factors=[
            Factor(name="5分钟二买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
            Factor(name="1分钟二买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
        ]),

        Event(name="加多2", operate=Operate.LA1, factors=[
            Factor(name="5分钟三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
            Factor(name="1分钟三买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="5分钟二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="5分钟三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
        ]),
    ]
    long_pos = PositionLong(symbol=symbol, hold_long_a=0.5, hold_long_b=0.8, hold_long_c=1, T0=T0)
    short_events = [
        Event(name="开空", operate=Operate.SO, factors=[
            Factor(name="5分钟一买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
            Factor(name="1分钟一买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
        ]),

        Event(name="加空1", operate=Operate.SA1, factors=[
            Factor(name="5分钟二买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
            Factor(name="1分钟二买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
        ]),

        Event(name="加空2", operate=Operate.SA1, factors=[
            Factor(name="5分钟三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
            Factor(name="1分钟三买", signals_all=[Signal("1分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
        ]),

        Event(name="平空", operate=Operate.SE, factors=[
            Factor(name="5分钟二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="5分钟三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
        ]),
    ]
    short_pos = PositionShort(symbol=symbol, hold_short_a=0.5, hold_short_b=0.8, hold_short_c=1, T0=T0)

    tactic = {
        "base_freq": '1分钟',
        "freqs": ['5分钟', '15分钟', '30分钟', '60分钟', '日线'],
        "get_signals": get_signals,
        "signals_n": 0,

        "long_pos": long_pos,
        "long_events": long_events,

        # 空头策略不进行定义，也就是不做空头交易
        "short_pos": short_pos,
        "short_events": short_events,
    }

    return tactic


def test_daily_trader():
    bars = read_daily()
    kg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars[:1000]:
        kg.update(bar)

    def __trader_strategy(symbol):
        tactic = {
            "base_freq": '1分钟',
            "freqs": ['5分钟', '15分钟', '30分钟', '60分钟', '日线'],
            "get_signals": get_signals,
            "signals_n": 0,

            "long_pos": None,
            "long_events": None,

            # 空头策略不进行定义，也就是不做空头交易
            "short_pos": None,
            "short_events": None,
        }

        return tactic
    ct = CzscAdvancedTrader(kg, __trader_strategy)

    signals_ = []
    for bar in bars[1000:]:
        ct.update(bar)
        signals_.append(dict(ct.s))

    assert len(signals_) == 2332

    # 测试传入空策略
    ct = CzscAdvancedTrader(kg)
    assert len(ct.s) == 0 and len(ct.kas) == 3


def run_advanced_trader(T0=True):
    bars = read_1min()
    kg = BarGenerator(base_freq='1分钟', freqs=['5分钟', '15分钟', '30分钟', '60分钟', '日线'], max_count=3000)
    for row in tqdm(bars[:150000], desc='init kg'):
        kg.update(row)

    def _strategy(symbol):
        return trader_strategy_test(symbol, T0=T0)
    ct = CzscAdvancedTrader(kg, _strategy)

    assert len(ct.s) == 28
    for row in tqdm(bars[150000:], desc="trade"):
        ct.update(row)
        # if long_pos.pos_changed:
        #     print(" : long op     : ", long_pos.operates[-1])
        # if short_pos.pos_changed:
        #     print(" : short op    : ", short_pos.operates[-1])

        if ct.long_pos.pos > 0:
            assert ct.long_pos.long_high > 0
            assert ct.long_pos.long_cost > 0
            assert ct.long_pos.long_bid > 0

        if ct.short_pos.pos > 0:
            assert ct.short_pos.short_low > 0
            assert ct.short_pos.short_cost > 0
            assert ct.short_pos.short_bid > 0

    long_yk = pd.DataFrame(ct.long_pos.pairs)['盈亏比例'].sum()
    short_yk = pd.DataFrame(ct.short_pos.pairs)['盈亏比例'].sum()
    assert abs(long_yk) == abs(short_yk)
    print(f"\nT0={T0}: 多头累计盈亏比例：{long_yk}；空头累计盈亏比例：{short_yk}")
    if not T0:
        assert ct.s['多头_最大_盈利'] == '超过800BP_任意_任意_0'
        assert ct.s['多头_累计_盈亏'] == '盈利_超过800BP_任意_0'
        assert ct.s['空头_最大_回撤'] == '超过800BP_任意_任意_0'
        assert ct.s['空头_累计_盈亏'] == '亏损_超过800BP_任意_0'

        holds_long = pd.DataFrame(ct.long_holds)
        assert round(holds_long['long_pos'].mean(), 4) == 0.7351

        holds_short = pd.DataFrame(ct.short_holds)
        assert round(holds_short['short_pos'].mean(), 4) == 0.7351


def test_advanced_trader():
    run_advanced_trader(T0=False)
    run_advanced_trader(T0=True)


