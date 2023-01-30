# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 13:24
describe: 提供一些策略的编写案例

以 trader_ 开头的是择时交易策略案例
"""
from abc import ABC, abstractmethod, abstractproperty
from czsc import signals
from czsc.objects import Freq, Operate, Signal, Factor, Event
from collections import OrderedDict
from czsc.traders import CzscAdvancedTrader
from czsc.objects import Position, PositionLong, PositionShort, RawBar
from czsc.utils import freqs_sorted


class CzscStrategyBase(ABC):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @property
    def symbol(self):
        """交易标的"""
        return self.kwargs['symbol']

    @property
    def sorted_freqs(self):
        """排好序的 K 线周期列表"""
        return freqs_sorted(self.freqs)

    @abstractmethod
    def get_signals(cls, **kwargs) -> OrderedDict:
        """交易信号计算函数"""
        raise NotImplementedError

    @abstractmethod
    def positions(self):
        """持仓策略列表"""
        raise NotImplementedError

    @abstractmethod
    def freqs(self):
        """K线周期列表"""
        raise NotImplementedError


class CzscStrategyExample1(CzscStrategyBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_signals(cls, cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bxt.get_s_three_bi(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_buy_V221126(cat.kas['日线'], di=2))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=1))
        s.update(signals.cxt_first_sell_V221126(cat.kas['日线'], di=2))
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
        return ['日线', '30分钟', '60分钟']

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
        pos = Position(symbol=self.symbol, opens=opens, exits=self.__shared_exits, interval=0, timeout=20, stop_loss=100)
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

        pos = Position(symbol=self.symbol, opens=opens, exits=None, interval=0, timeout=20, stop_loss=100)
        return pos

    def create_pos_c(self):
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
        pos = Position(symbol=self.symbol, opens=opens, exits=self.__shared_exits, interval=0, timeout=20, stop_loss=50)
        return pos


def trader_standard(symbol, T0=False, min_interval=3600*4):
    """择时策略编写的一些标准说明

    输入参数：
    1. symbol 是必须要有的，且放在第一个位置，策略初始化过程指明交易哪个标的
    2. 除此之外的一些策略层面的参数可选，比如 T0，min_interval 等

    :param symbol: 择时策略初始化的必须参数，指明交易哪个标的
    :param T0:
    :param min_interval:
    :return:
    """
    pass


def trader_example1(symbol, T0=False, min_interval=3600*4):
    """A股市场择时策略样例，支持按交易标的独立设置参数

    :param symbol:
    :param T0: 是否允许T0交易
    :param min_interval: 最小开仓时间间隔，单位：秒
    :return:
    """
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.pos.get_s_long01(cat, th=100))
        s.update(signals.pos.get_s_long02(cat, th=100))
        s.update(signals.pos.get_s_long05(cat, span='月', th=500))

        for _, c in cat.kas.items():
            s.update(signals.bxt.get_s_d0_bi(c))
            if c.freq in [Freq.F1]:
                s.update(signals.other.get_s_zdt(c, di=1))
                s.update(signals.other.get_s_op_time_span(c, op='开多', time_span=('13:00', '14:50')))
                s.update(signals.other.get_s_op_time_span(c, op='平多', time_span=('09:35', '14:50')))
            if c.freq in [Freq.F60, Freq.D, Freq.W]:
                s.update(signals.ta.get_s_macd(c, di=1))
        return s

    # 定义多头持仓对象和交易事件
    long_pos = PositionLong(symbol, hold_long_a=1, hold_long_b=1, hold_long_c=1,
                            T0=T0, long_min_interval=min_interval)

    long_events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="低吸", signals_all=[
                Signal("开多时间范围_13:00_14:50_是_任意_任意_0"),
                Signal("1分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("15分钟_倒0笔_长度_5根K线以下_任意_任意_0"),
            ]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="持有资金", signals_all=[
                Signal("平多时间范围_09:35_14:50_是_任意_任意_0"),
                Signal("1分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
            ], signals_not=[
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
            ]),
        ]),
    ]

    tactic = {
        "base_freq": '1分钟',
        "freqs": ['5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'],
        "get_signals": get_signals,

        "long_pos": long_pos,
        "long_events": long_events,

        # 空头策略不进行定义，也就是不做空头交易
        "short_pos": None,
        "short_events": None,
    }

    return tactic


def trader_strategy_a(symbol):
    """A股市场择时策略A"""
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.pos.get_s_long01(cat, th=100))
        s.update(signals.pos.get_s_long02(cat, th=100))
        s.update(signals.pos.get_s_long05(cat, span='月', th=500))
        for _, c in cat.kas.items():
            if c.freq in [Freq.F15]:
                s.update(signals.bxt.get_s_d0_bi(c))
                s.update(signals.other.get_s_zdt(c, di=1))
                s.update(signals.other.get_s_op_time_span(c, op='开多', time_span=('13:00', '14:50')))
                s.update(signals.other.get_s_op_time_span(c, op='平多', time_span=('09:35', '14:50')))

            if c.freq in [Freq.F60, Freq.D, Freq.W]:
                s.update(signals.ta.get_s_macd(c, di=1))
        return s

    # 定义多头持仓对象和交易事件
    long_pos = PositionLong(symbol, hold_long_a=1, hold_long_b=1, hold_long_c=1,
                            T0=False, long_min_interval=3600*4)
    long_events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="低吸", signals_all=[
                Signal("开多时间范围_13:00_14:50_是_任意_任意_0"),
                Signal("15分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("15分钟_倒0笔_长度_5根K线以下_任意_任意_0"),
            ]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="持有资金", signals_all=[
                Signal("平多时间范围_09:35_14:50_是_任意_任意_0"),
                Signal("15分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
            ], signals_not=[
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
            ]),
        ]),
    ]

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,

        "long_pos": long_pos,
        "long_events": long_events,

        # 空头策略不进行定义，也就是不做空头交易
        "short_pos": None,
        "short_events": None,
    }

    return tactic



