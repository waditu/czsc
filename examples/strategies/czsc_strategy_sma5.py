# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/2 18:30
describe: 
"""
import os
import pandas as pd
from copy import deepcopy
from deprecated import deprecated
from abc import ABC, abstractmethod
from loguru import logger
from czsc import signals
from czsc.objects import RawBar, List, Freq, Operate, Signal, Factor, Event, Position
from collections import OrderedDict
from czsc.utils import x_round, freqs_sorted, BarGenerator, dill_dump
from czsc.strategies import CzscStrategyBase


class CzscStrategySMA5(CzscStrategyBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_signals(cls, cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='全天', span=('0935', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='临收盘', span=('1410', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='下午', span=('1300', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='上午', span=('0935', '1130')))
        s.update(signals.bar_zdt_V221111(cat, '15分钟', di=1))
        s.update(signals.bar_mean_amount_V221112(cat.kas['日线'], di=2, n=20, th1=2, th2=1000))

        signals.update_ma_cache(cat.kas["日线"], ma_type='SMA', timeperiod=5)
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, ma_type='SMA', timeperiod=5))
        c = cat.kas['30分钟']
        s.update(signals.cxt_first_buy_V221126(c, di=1))
        return s

    @property
    def positions(self):
        return [
            self.create_pos_a(),
            self.create_pos_b(),
            self.create_pos_c(),
        ]

    @property
    def freqs(self):
        return ['日线', '30分钟', '60分钟', '15分钟']

    @property
    def __shared_exits(self):
        return [
            Event(name='平多', operate=Operate.LE, factors=[
                Factor(name="日线三笔向上收敛", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上收敛_任意_任意_0"),
                ])
            ]),
            Event(name='平空', operate=Operate.SE, factors=[
                Factor(name="日线三笔向下收敛", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下收敛_任意_任意_0"),
                ])
            ]),
        ]

    def create_pos_a(self):
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="日线一买", signals_all=[
                    Signal("日线_D1B_BUY1_一买_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="日线一卖", signals_all=[
                    Signal("日线_D1B_BUY1_一卖_任意_任意_0"),
                ])
            ]),
        ]
        pos = Position(name="A", symbol=self.symbol, opens=opens, exits=self.__shared_exits,
                       interval=0, timeout=20, stop_loss=100)
        return pos

    def create_pos_b(self):
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="日线三笔向下无背", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向下无背_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="日线三笔向上无背", signals_all=[
                    Signal("日线_倒1笔_三笔形态_向上无背_任意_任意_0"),
                ])
            ]),
        ]

        pos = Position(name="B", symbol=self.symbol, opens=opens, exits=None, interval=0, timeout=20, stop_loss=100)
        return pos

    def create_pos_c(self):
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="日线一买", signals_all=[
                    Signal("日线_D2B_BUY1_一买_任意_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="日线一卖", signals_all=[
                    Signal("日线_D2B_BUY1_一卖_任意_任意_0"),
                ])
            ]),
        ]
        pos = Position(name="C", symbol=self.symbol, opens=opens, exits=self.__shared_exits,
                       interval=0, timeout=20, stop_loss=50)
        return pos
