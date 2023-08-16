# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 21:07
"""
import os
import pandas as pd
from copy import deepcopy
from czsc.utils.cache import home_path
from czsc.traders.base import CzscSignals, BarGenerator, CzscTrader
from czsc.traders.sig_parse import get_signals_config, get_signals_freqs
from czsc.objects import Signal, Factor, Event, Operate, Position
from test.test_analyze import read_daily


def test_object_position():
    bars = read_daily()
    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars[:1000]:
        bg.update(bar)

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

    signals_config = get_signals_config(pos.unique_signals)
    cs = CzscSignals(deepcopy(bg), signals_config=signals_config)
    for bar in bars[1000:]:
        cs.update_signals(bar)
        pos.update(cs.s)

    df = pd.DataFrame(pos.pairs)
    assert df.shape == (16, 11)
    assert len(cs.s) == 12

    exits = [
        Event(name='平多', operate=Operate.LE, factors=[
            Factor(name="跌破SMA5", signals_all=[
                Signal("日线_D0停顿分型_BE辅助V230106_看空_强_任意_0"),
            ])
        ]),
        Event(name='平空', operate=Operate.SE, factors=[
            Factor(name="站上SMA5", signals_all=[
                Signal("日线_D0停顿分型_BE辅助V230106_看多_强_任意_0"),
            ])
        ]),
    ]

    pos = Position(name="测试B", symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=300)

    assert len(pos.unique_signals) == 4
    assert len(pos.events[0].unique_signals) == 1

    signals_config = get_signals_config(pos.unique_signals)
    cs = CzscSignals(deepcopy(bg), signals_config=signals_config)
    for bar in bars[1000:]:
        cs.update_signals(bar)
        pos.update(cs.s)

    df = pd.DataFrame(pos.pairs)
    assert df.shape == (17, 11)
    assert len(cs.s) == 13

    # 测试 dump 和 load
    pos_x = pos.dump()
    assert isinstance(pos_x, dict)
    pos_x['name'] = "测试C"
    pos_y = Position.load(pos_x)
    cs = CzscSignals(deepcopy(bg), signals_config=get_signals_config(pos_y.unique_signals))
    for bar in bars[1000:]:
        cs.update_signals(bar)
        pos_y.update(cs.s)

    df = pd.DataFrame(pos_y.pairs)
    assert df.shape == (17, 11)
    assert len(cs.s) == 13


def test_generate_czsc_signals():
    from czsc.traders.base import generate_czsc_signals

    bars = read_daily()
    signals_seq = [
        "日线_D1B_BUY1_一买_任意_任意_0",
        "日线_D1B_BUY1_一卖_任意_任意_0",
        "日线_D0停顿分型_BE辅助V230106_看空_强_任意_0"
    ]

    signals_config = get_signals_config(signals_seq)

    # 通过 signals_seq 得到 freqs
    freqs = get_signals_freqs(signals_seq)

    # 通过 signals_config 得到 freqs
    freqs1 = get_signals_freqs(signals_config)

    assert freqs == freqs1
    res = generate_czsc_signals(bars, signals_config=signals_config, freqs=freqs, sdt="20100101", init_n=500)
    rdf = generate_czsc_signals(bars, signals_config=signals_config, freqs=freqs, sdt="20100101", init_n=500, df=True)

    assert len(res) == len(rdf)


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
                    Signal("日线_D0停顿分型_BE辅助V230106_看空_强_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D0停顿分型_BE辅助V230106_看多_强_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100, name="测试A")

        return pos

    def __create_sma10_pos():
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
                    Signal("日线_D0停顿分型_BE辅助V230106_看空_强_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D0停顿分型_BE辅助V230106_看多_强_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100, name="测试B")
        return pos

    def __create_sma20_pos():
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D3B_BUY1_一买_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_D3B_BUY1_一卖_任意_任意_0"),
                ])
            ]),
        ]

        exits = [
            Event(name='平多', operate=Operate.LE, factors=[
                Factor(name="跌破SMA5", signals_all=[
                    Signal("日线_D0停顿分型_BE辅助V230106_看空_强_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="站上SMA5", signals_all=[
                    Signal("日线_D0停顿分型_BE辅助V230106_看多_强_任意_0"),
                ])
            ]),
        ]

        pos = Position(symbol=bg.symbol, opens=opens, exits=exits, interval=0, timeout=20, stop_loss=100, name="测试C")
        return pos

    positions = [__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()]
    signals_seq = []
    for _pos in positions:
        signals_seq.extend(_pos.unique_signals)

    signals_config = get_signals_config(list(set(signals_seq)))
    # 通过 update 执行
    ct = CzscTrader(deepcopy(bg), signals_config=signals_config,
                    positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for bar in bars_right:
        ct.update(bar)
        for _pos in ct.positions:
            if _pos.pos_changed:
                assert _pos.operates[-1]['dt'] == _pos.end_dt
                print(_pos.name, _pos.operates[-1], _pos.end_dt, _pos.pos)
                assert ct.pos_changed

    assert list(ct.positions[0].dump(False).keys()) == ['symbol', 'name', 'opens', 'exits', 'interval', 'timeout',
                                                        'stop_loss', 'T0']
    assert list(ct.positions[0].dump(True).keys()) == ['symbol', 'name', 'opens', 'exits', 'interval', 'timeout',
                                                       'stop_loss', 'T0', 'pairs', 'holds']
    assert [x.pos for x in ct.positions] == [0, 0, 0]

    # 测试自定义仓位集成
    def _weighted_ensemble(poss):
        return 0.5 * poss['测试A'] + 0.5 * poss['测试B']

    assert ct.get_ensemble_pos(_weighted_ensemble) == 0
    assert ct.get_ensemble_pos('vote') == 0
    assert ct.get_ensemble_pos('max') == 0
    assert ct.get_ensemble_pos('mean') == 0
    dfw = ct.get_ensemble_weight(method='mean')
    assert len(dfw) == len(bars_right)

    res = ct.weight_backtest(method='mean', res_path=os.path.join(home_path, "test_trader"))

    # 通过 on_bar 执行
    ct1 = CzscTrader(deepcopy(bg), signals_config=signals_config,
                     positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for bar in bars_right:
        ct1.on_bar(bar)
        # print(ct1.s)
        print(f"{ct1.end_dt}: pos_seq = {[x.pos for x in ct1.positions]}mean_pos = {ct1.get_ensemble_pos('mean')}; "
              f"vote_pos = {ct1.get_ensemble_pos('vote')}; max_pos = {ct1.get_ensemble_pos('max')}")

    assert [x.pos for x in ct1.positions] == [0, 0, 0]

    assert len(ct1.positions[0].pairs) == len(ct.positions[0].pairs)
    assert len(ct1.positions[1].pairs) == len(ct.positions[1].pairs)
    assert len(ct1.positions[2].pairs) == len(ct.positions[2].pairs)

    # 通过 on_sig 执行
    from czsc.traders.base import generate_czsc_signals
    res = generate_czsc_signals(bars, signals_config=signals_config, freqs=['周线', '月线'], sdt=sdt, init_n=init_n)
    ct2 = CzscTrader(positions=[__create_sma5_pos(), __create_sma10_pos(), __create_sma20_pos()])
    for sig in res:
        ct2.on_sig(sig)
        print(f"{ct2.end_dt}: pos_seq = {[x.pos for x in ct2.positions]}mean_pos = {ct2.get_ensemble_pos('mean')}; "
              f"vote_pos = {ct2.get_ensemble_pos('vote')}; max_pos = {ct2.get_ensemble_pos('max')}")

    assert [x.pos for x in ct2.positions] == [0, 0, 0]

    assert len(ct1.positions[0].pairs) == len(ct2.positions[0].pairs)
    assert len(ct1.positions[1].pairs) == len(ct2.positions[1].pairs)
    assert len(ct1.positions[2].pairs) == len(ct2.positions[2].pairs)
