# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/11 17:19
describe: 这是编写策略的案例
"""
import czsc
from copy import deepcopy
from collections import OrderedDict
from czsc import signals, Event, Position


class CzscStocksBeta(czsc.CzscStrategyBase):
    """CZSC 股票 Beta 策略"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_signals(cls, cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='全天', span=('0935', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='上午', span=('0935', '1130')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='下午', span=('1300', '1450')))
        s.update(signals.bar_zdt_V221110(cat.kas['15分钟'], di=1))

        s.update(signals.tas_macd_base_V221028(cat.kas['60分钟'], di=1, key='macd'))
        s.update(signals.tas_macd_base_V221028(cat.kas['60分钟'], di=5, key='macd'))

        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, ma_type='SMA', timeperiod=5))
        return s

    @property
    def positions(self):
        beta1 = self.create_beta1()
        beta2 = self.create_beta2()
        pos_list = [deepcopy(beta1), deepcopy(beta2)]
        return pos_list

    @property
    def freqs(self):
        return ['日线', '60分钟', '30分钟', '15分钟']

    def create_beta1(self):
        """60分钟MACD金叉"""

        opens = [
            {'name': '开多',
             'operate': '开多',
             'signals_all': [],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_ZDT_涨停_任意_任意_0'],
             'factors': [{'name': '60分钟MACD金叉',
                          'signals_all': ['全天_0935_1450_是_任意_任意_0',
                                          '60分钟_D1K_MACD_多头_任意_任意_0',
                                          '60分钟_D5K_MACD_空头_任意_任意_0'],
                          'signals_any': [],
                          'signals_not': []}
                         ]},
        ]

        exits = [
            {'name': '平多',
             'operate': '平多',
             'signals_all': ['全天_0935_1450_是_任意_任意_0'],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_ZDT_跌停_任意_任意_0'],
             'factors': [{'name': '60分钟MACD死叉',
                          'signals_all': ['60分钟_D1K_MACD_空头_任意_任意_0'],
                          'signals_any': [],
                          'signals_not': []}]},

        ]
        pos = Position(name="60分钟MACD金叉", symbol=self.symbol,
                       opens=[Event.load(x) for x in opens],
                       exits=[Event.load(x) for x in exits],
                       interval=3600 * 4, timeout=16 * 30, stop_loss=500)
        return pos

    def create_beta2(self):
        """5日线多头"""

        opens = [
            {'name': '开多',
             'operate': '开多',
             'signals_all': [],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_ZDT_涨停_任意_任意_0'],
             'factors': [{'name': '站上SMA5',
                          'signals_all': ['上午_0935_1130_是_任意_任意_0',
                                          '日线_D1K_SMA5_多头_任意_任意_0',
                                          '日线_D5K_SMA5_空头_任意_任意_0'],
                          'signals_any': [],
                          'signals_not': []}]}
        ]

        exits = [
            {'name': '平多',
             'operate': '平多',
             'signals_all': [],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_ZDT_跌停_任意_任意_0'],
             'factors': [{'name': '跌破SMA5',
                          'signals_all': ['下午_1300_1450_是_任意_任意_0',
                                          '日线_D1K_SMA5_空头_任意_任意_0',
                                          '日线_D2K_SMA5_多头_任意_任意_0'],
                          'signals_any': [],
                          'signals_not': []}]}
        ]
        pos = Position(name="5日线多头", symbol=self.symbol,
                       opens=[Event.load(x) for x in opens],
                       exits=[Event.load(x) for x in exits],
                       interval=3600 * 4, timeout=16 * 40, stop_loss=500)
        return pos

