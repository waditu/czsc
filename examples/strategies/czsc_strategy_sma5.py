# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/2 18:30
describe: 
"""
from czsc import signals
from collections import OrderedDict
from czsc.objects import Event, Position
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
        # s.update(signals.bar_end_V221111(cat.kas['5分钟'], '15分钟'))
        s.update(signals.bar_mean_amount_V221112(cat.kas['日线'], di=2, n=20, th1=2, th2=1000))

        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, ma_type='SMA', timeperiod=5))

        s.update(signals.cxt_first_buy_V221126(cat.kas['30分钟'], di=1))
        return s

    @property
    def positions(self):
        return [
            self.create_pos_a(),
        ]

    @property
    def freqs(self):
        return ['日线', '30分钟', '15分钟']

    def create_pos_a(self):
        opens = [
            {'name': '开多',
             'operate': '开多',
             'signals_all': ['日线_D2K20B均额_2至1000千万_是_任意_任意_0'],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_涨停_任意_任意_0'],
             'factors': [
                 {'name': '站上SMA5',
                  'signals_all': ['全天_0935_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_多头_任意_任意_0',
                                  '日线_D5K_SMA5_空头_向下_任意_0',
                                  '30分钟_D1B_BUY1_一买_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]},
            {'name': '开空',
             'operate': '开空',
             'signals_all': ['日线_D2K20B均额_2至1000千万_是_任意_任意_0'],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_跌停_任意_任意_0'],
             'factors': [
                 {'name': '站上SMA5',
                  'signals_all': ['全天_0935_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_空头_任意_任意_0',
                                  '日线_D5K_SMA5_多头_向下_任意_0',
                                  '30分钟_D1B_BUY1_一卖_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]},
        ]

        exits = [
            {'name': '平多',
             'operate': '平多',
             'signals_all': [],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_跌停_任意_任意_0'],
             'factors': [
                 {'name': '跌破SMA5',
                  'signals_all': ['下午_1300_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_空头_任意_任意_0',
                                  '日线_D2K_SMA5_多头_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]}
        ]
        pos = Position(name="A", symbol=self.symbol,
                       opens=[Event.load(x) for x in opens],
                       exits=[Event.load(x) for x in exits],
                       interval=3600*4, timeout=100, stop_loss=1000, T0=False)
        return pos
