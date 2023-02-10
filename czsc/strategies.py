# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 13:24
describe: 提供一些策略的编写案例

以 trader_ 开头的是择时交易策略案例
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
from czsc.traders.base import CzscTrader
from czsc.traders import CzscAdvancedTrader
from czsc.objects import PositionLong
from czsc.utils import x_round, freqs_sorted, BarGenerator, dill_dump


class CzscStrategyBase(ABC):
    """
    择时交易策略的要素：

    1. 交易品种以及该品种对应的参数
    2. K线周期列表
    3. 交易信号计算函数
    4. 持仓策略列表
    """
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
    def positions(self) -> List[Position]:
        """持仓策略列表"""
        raise NotImplementedError

    @abstractmethod
    def freqs(self):
        """K线周期列表"""
        raise NotImplementedError

    def init_bar_generator(self, bars: List[RawBar], **kwargs):
        """使用策略定义初始化一个 BarGenerator 对象

        :param bars: 基础周期K线
        :param kwargs:
            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量
        :return:
        """
        bg: BarGenerator = kwargs.get('bg', None)
        if bg is None:
            sdt = pd.to_datetime(kwargs.get('sdt', '20200101'))
            n = int(kwargs.get('n', 500))
            bg = BarGenerator(self.sorted_freqs[0], freqs=self.sorted_freqs[1:])

            # 拆分基础周期K线，sdt 之前的用来初始化BarGenerator，随后的K线是 trader 初始化区间
            bars_init = [x for x in bars if x.dt <= sdt]
            if len(bars_init) > n:
                bars1 = bars_init
                bars2 = [x for x in bars if x.dt > sdt]
            else:
                bars1 = bars[:n]
                bars2 = bars[n:]

            for bar in bars1:
                bg.update(bar)

            return bg, bars2
        else:
            assert bg.base_freq == bars[-1].freq.value, "BarGenerator 的基础周期和 bars 的基础周期不一致"
            bars2 = [x for x in bars if x.dt > bg.end_dt]
            return bg, bars2

    def init_trader(self, bars: List[RawBar], **kwargs):
        """使用策略定义初始化一个 CzscTrader 对象

        :param bars: 基础周期K线
        :param kwargs:
            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量
        :return:
        """
        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions))
        for bar in bars2:
            trader.on_bar(bar)
        return trader

    def replay(self, bars: List[RawBar], res_path, **kwargs):
        """交易策略交易过程回放

        :param bars: 基础周期K线
        :param res_path: 结果目录
        :param kwargs:
            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量
        :return:
        """
        exist_ok = kwargs.get("exist_ok", False)
        if os.path.exists(res_path) and not exist_ok:
            logger.warning(f"结果文件夹存在且不允许覆盖：{res_path}，如需执行，请先删除文件夹")
            return
        os.makedirs(res_path, exist_ok=exist_ok)

        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions))
        for position in trader.positions:
            pos_path = os.path.join(res_path, position.name)
            os.makedirs(pos_path, exist_ok=exist_ok)

        for bar in bars2:
            trader.on_bar(bar)
            for position in trader.positions:
                pos_path = os.path.join(res_path, position.name)

                if position.operates and position.operates[-1]['dt'] == bar.dt:
                    op = position.operates[-1]
                    _dt = op['dt'].strftime('%Y%m%d#%H%M')
                    file_name = f"{op['op'].value}_{_dt}_{op['bid']}_{x_round(op['price'], 2)}_{op['op_desc']}.html"
                    file_html = os.path.join(pos_path, file_name)
                    trader.take_snapshot(file_html)
                    logger.info(f'{file_html}')

        file_trader = os.path.join(res_path, "trader.ct")
        try:
            dill_dump(trader, file_trader)
            logger.info(f"交易对象保存到：{file_trader}")
        except Exception as e:
            logger.error(f"交易对象保存失败：{e}；通常的原因是交易对象中包含了不支持序列化的对象，比如函数")
        return trader


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


@deprecated(reason="更新为 Position + CzscTrader 执行")
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


@deprecated(reason="更新为 Position + CzscTrader 执行")
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


@deprecated(reason="更新为 Position + CzscTrader 执行")
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



