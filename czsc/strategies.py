# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 13:24
describe: 提供一些策略的编写案例

以 trader_ 开头的是择时交易策略案例
"""
import os
import shutil
import pandas as pd
from copy import deepcopy
from abc import ABC, abstractmethod
from loguru import logger
from czsc import signals
from czsc.objects import RawBar, List, Operate, Signal, Factor, Event, Position
from collections import OrderedDict
from czsc.traders.base import CzscTrader
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

    @property
    def base_freq(self):
        """基础 K 线周期"""
        return self.sorted_freqs[0]

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

    def init_trader(self, bars: List[RawBar], **kwargs) -> CzscTrader:
        """使用策略定义初始化一个 CzscTrader 对象

        **注意：** 这里会将所有持仓策略在 sdt 之后的交易信号计算出来并缓存在持仓策略实例内部，所以初始化的过程本身也是回测的过程。

        :param bars: 基础周期K线
        :param kwargs:
            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量
        :return: 完成策略初始化后的 CzscTrader 对象
        """
        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions))
        for bar in bars2:
            trader.on_bar(bar)
        return trader

    def backtest(self, bars: List[RawBar], **kwargs) -> CzscTrader:
        trader = self.init_trader(bars, **kwargs)
        return trader

    def dummy(self, sigs: List[dict], **kwargs) -> CzscTrader:
        """使用信号缓存进行策略回测

        :param sigs: 信号缓存，一般指 generate_czsc_signals 函数计算的结果缓存
        :return: 完成策略回测后的 CzscTrader 对象
        """
        trader = CzscTrader(positions=deepcopy(self.positions))
        for sig in sigs:
            trader.on_sig(sig)
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
        if kwargs.get('refresh', False):
            shutil.rmtree(res_path, ignore_errors=True)

        exist_ok = kwargs.get("exist_ok", False)
        if os.path.exists(res_path) and not exist_ok:
            logger.warning(f"结果文件夹存在且不允许覆盖：{res_path}，如需执行，请先删除文件夹")
            return
        os.makedirs(res_path, exist_ok=exist_ok)

        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions))
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

