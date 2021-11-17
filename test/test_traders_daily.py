# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 23:22
"""
from czsc.utils.bar_generator import BarGenerator
from czsc.traders.daily import CzscDailyTrader, KlineGeneratorD
from test.test_analyze import read_daily, get_user_signals


def test_daily_trader():
    bars = read_daily()

    kg = KlineGeneratorD(freqs=['日线', '周线', '月线'])
    for bar in bars[:1000]:
        kg.update(bar)

    ct = CzscDailyTrader(kg, get_user_signals)

    signals = []
    for bar in bars[1000:]:
        ct.update(bar)
        signals.append(dict(ct.s))

    assert len(signals) == 2332

    kg = BarGenerator(base_freq='日线', freqs=['周线', '月线'])
    for bar in bars[:1000]:
        kg.update(bar)

    ct = CzscDailyTrader(kg, get_user_signals)

    signals = []
    for bar in bars[1000:]:
        ct.update(bar)
        signals.append(dict(ct.s))

    assert len(signals) == 2332

