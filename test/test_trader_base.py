# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 21:07
"""
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from loguru import logger
from typing import List
from collections import OrderedDict
from czsc import signals
from czsc.traders.base import CzscSignals, CzscAdvancedTrader, BarGenerator, CzscTrader
from czsc.objects import Signal, Factor, Event, Operate, PositionLong, PositionShort, Position
from test.test_analyze import read_1min, read_daily


def test_object_position():
    bars = read_daily()
    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars[:1000]:
        bg.update(bar)

    def __get_signals(cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=1))
        s.update(signals.bxt.get_s_three_bi(cat.kas['日线'], di=1))
        return s

    opens = [
        Event(name='开多', operate=Operate.LO, factors=[
            Factor(name="站上SMA5", signals_all=[
                Signal("日线_D1B_BUY1_一买_任意_任意_0"),
            ])
        ]),
        Event(name='开空', operate=Operate.SO, factors=[
            Factor(name="跌破SMA5", signals_all=[
                Signal("日线_D1B_BUY1_一卖_任意_任意_0"),
            ])
        ]),
    ]

    # 没有出场条件的测试
    pos = Position(name="测试A", symbol=bg.symbol, opens=opens, exits=[], interval=0, timeout=20, stop_loss=300)

    cs = CzscSignals(deepcopy(bg), get_signals=__get_signals)
    for bar in bars[1000:]:
        cs.update_signals(bar)
        pos.update(cs.s)

    df = pd.DataFrame(pos.pairs)
    assert df.shape == (16, 11)
    assert len(cs.s) == 13

    exits = [
        Event(name='平多', operate=Operate.LE, factors=[
            Factor(name="跌破SMA5", signals_all=[
                Signal("日线_倒1笔_三笔形态_向上收敛_任意_任意_0"),
            ])
        ]),
        Event(name='平空', operate=Operate.SE, factors=[
            Factor(name="站上SMA5", signals_all=[
                Signal("日线_倒1笔_三笔形态_向下收敛_任意_任意_0"),
            ])
        ]),
    ]

    pos = Position(name="测试B", symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=300)

    cs = CzscSignals(deepcopy(bg), get_signals=__get_signals)
    for bar in bars[1000:]:
        cs.update_signals(bar)
        pos.update(cs.s)

    df = pd.DataFrame(pos.pairs)
    assert df.shape == (21, 11)
    assert len(cs.s) == 13


def test_generate_czsc_signals():
    from czsc.traders.base import generate_czsc_signals

    bars = read_daily()

    def __get_signals(cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bxt.get_s_three_bi(cat.kas['日线'], di=1))
        s.update(signals.bxt.get_s_three_bi(cat.kas['周线'], di=1))
        s.update(signals.bxt.get_s_three_bi(cat.kas['月线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=2))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=2))
        return s

    res = generate_czsc_signals(bars, get_signals=__get_signals, freqs=['周线', '月线'], sdt="20100101", init_n=500)
    res_df = generate_czsc_signals(bars, get_signals=__get_signals, freqs=['周线', '月线'],
                                   sdt="20100101", init_n=500, df=True)

    assert len(res) == len(res_df)


def test_czsc_trader():
    bars = read_daily()

    sdt = "20100101"
    init_n = 2000
    sdt = pd.to_datetime(sdt)
    bars_left = [x for x in bars if x.dt < sdt]
    if len(bars_left) <= init_n:
        bars_left = bars[:init_n]
        bars_right = bars[init_n:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]

    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars_left:
        bg.update(bar)

    def __get_signals(cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bxt.get_s_three_bi(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=2))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=2))
        return s

    def __create_sma5_pos():
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D1B_BUY1_一买_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_D1B_BUY1_一卖_任意_任意_0"),
                ])
            ]),
        ]

        exits = [
            Event(name='平多', operate=Operate.LE, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上收敛_任意_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下收敛_任意_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100)

        return pos

    def __create_sma10_pos():
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下无背_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上无背_任意_任意_0"),
                ])
            ]),
        ]

        exits = [
            Event(name='平多', operate=Operate.LE, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上收敛_任意_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下收敛_任意_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100)
        return pos

    def __create_sma20_pos():
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D2B_BUY1_一买_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_D2B_BUY1_一卖_任意_任意_0"),
                ])
            ]),
        ]

        exits = [
            Event(name='平多', operate=Operate.LE, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上收敛_任意_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下收敛_任意_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100)
        return pos

    # 通过 update 执行
    ct = CzscTrader(deepcopy(bg), get_signals=__get_signals,
                    positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for bar in bars_right:
        ct.update(bar)
        print(f"{bar.dt}: pos_seq = {[x.pos for x in ct.positions]}mean_pos = {ct.get_ensemble_pos('mean')}; vote_pos = {ct.get_ensemble_pos('vote')}; max_pos = {ct.get_ensemble_pos('max')}")

    assert [x.pos for x in ct.positions] == [0, -1, 0]

    # 测试自定义仓位集成
    def _weighted_ensemble(positions: List[Position]):
        return 0.5 * positions[0].pos + 0.5 * positions[1].pos

    assert ct.get_ensemble_pos(_weighted_ensemble) == -0.5
    assert ct.get_ensemble_pos('vote') == -1
    assert ct.get_ensemble_pos('max') == 0
    assert ct.get_ensemble_pos('mean') == -0.3333333333333333

    # 通过 on_bar 执行
    ct1 = CzscTrader(deepcopy(bg), get_signals=__get_signals,
                     positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for bar in bars_right:
        ct1.on_bar(bar)
        # print(ct1.s)
        print(f"{ct1.end_dt}: pos_seq = {[x.pos for x in ct1.positions]}mean_pos = {ct1.get_ensemble_pos('mean')}; vote_pos = {ct1.get_ensemble_pos('vote')}; max_pos = {ct1.get_ensemble_pos('max')}")

    assert [x.pos for x in ct1.positions] == [0, -1, 0]

    assert len(ct1.positions[0].pairs) == len(ct.positions[0].pairs)
    assert len(ct1.positions[1].pairs) == len(ct.positions[1].pairs)
    assert len(ct1.positions[2].pairs) == len(ct.positions[2].pairs)

    # 通过 on_sig 执行
    from czsc.traders.base import generate_czsc_signals
    res = generate_czsc_signals(bars, get_signals=__get_signals, freqs=['周线', '月线'], sdt=sdt, init_n=init_n)
    ct2 = CzscTrader(positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for sig in res:
        ct2.on_sig(sig)
        # print(ct2.s)
        print(f"{ct2.end_dt}: pos_seq = {[x.pos for x in ct2.positions]}mean_pos = {ct2.get_ensemble_pos('mean')}; vote_pos = {ct2.get_ensemble_pos('vote')}; max_pos = {ct2.get_ensemble_pos('max')}")

    assert [x.pos for x in ct2.positions] == [0, -1, 0]

    assert len(ct1.positions[0].pairs) == len(ct2.positions[0].pairs)
    assert len(ct1.positions[1].pairs) == len(ct2.positions[1].pairs)
    assert len(ct1.positions[2].pairs) == len(ct2.positions[2].pairs)


def get_signals(cat) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    for _, c in cat.kas.items():
        s.update(signals.bxt.get_s_like_bs(c, di=1))

    if isinstance(cat, CzscAdvancedTrader) and cat.long_pos:
        s.update(signals.cat.get_s_position(cat, cat.long_pos))
    if isinstance(cat, CzscAdvancedTrader) and cat.short_pos:
        s.update(signals.cat.get_s_position(cat, cat.short_pos))
    return s


def test_czsc_signals():
    bars = read_daily()
    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars[:1000]:
        bg.update(bar)

    cs = CzscSignals(bg, get_signals=get_signals)
    for bar in bars[1000:]:
        cs.update_signals(bar)
    assert len(cs.s) == 14


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

    assert len(ct.s) == 29
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
        assert round(holds_long['long_pos'].mean(), 4) == 0.7516

        holds_short = pd.DataFrame(ct.short_holds)
        assert round(holds_short['short_pos'].mean(), 4) == 0.7516


def test_advanced_trader():
    run_advanced_trader(T0=False)
    run_advanced_trader(T0=True)


