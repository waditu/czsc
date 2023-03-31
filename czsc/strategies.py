# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 13:24
describe: 提供一些策略的编写案例

以 trader_ 开头的是择时交易策略案例
"""
import os
import time
import shutil
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from abc import ABC, abstractmethod
from loguru import logger
from czsc import signals
from czsc.objects import RawBar, List, Operate, Signal, Factor, Event, Position
from collections import OrderedDict
from czsc.traders.base import CzscTrader, get_signals_by_conf
from czsc.traders.sig_parse import get_signals_freqs, get_signals_config
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
        self.signals_module_name = kwargs.get('signals_module_name', 'czsc.signals')

    @property
    def symbol(self):
        """交易标的"""
        return self.kwargs['symbol']

    @property
    def unique_signals(self):
        """所有持仓策略中的交易信号列表"""
        sig_seq = []
        for pos in self.positions:
            sig_seq.extend(pos.unique_signals)
        return list(set(sig_seq))

    @property
    def signals_config(self):
        """K线周期列表"""
        return get_signals_config(self.unique_signals, self.signals_module_name)

    @property
    def freqs(self):
        """K线周期列表"""
        return get_signals_freqs(self.unique_signals)

    @property
    def sorted_freqs(self):
        """排好序的 K 线周期列表"""
        return freqs_sorted(self.freqs)

    @property
    def base_freq(self):
        """基础 K 线周期"""
        return self.sorted_freqs[0]

    def get_signals(self, cat: CzscTrader, **kwargs) -> OrderedDict:
        """交易信号计算函数"""
        return OrderedDict()

    @abstractmethod
    def positions(self) -> List[Position]:
        """持仓策略列表"""
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
        base_freq = str(bars[0].freq.value)
        bg: BarGenerator = kwargs.get('bg', None)
        if base_freq in self.sorted_freqs:
            freqs = self.sorted_freqs[1:]
        else:
            freqs = self.sorted_freqs

        if bg is None:
            sdt = pd.to_datetime(kwargs.get('sdt', '20200101'))
            n = int(kwargs.get('n', 500))
            bg = BarGenerator(base_freq, freqs=freqs)

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
        trader = CzscTrader(bg=bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions),
                            signals_config=deepcopy(self.signals_config), **kwargs)
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
        sleep_time = kwargs.get('sleep_time', 0)
        sleep_step = kwargs.get('sleep_step', 1000)

        trader = CzscTrader(positions=deepcopy(self.positions))
        for i, sig in tqdm(enumerate(sigs), desc=f"回测 {self.symbol} {self.sorted_freqs}"):
            trader.on_sig(sig)

            if i % sleep_step == 0:
                time.sleep(sleep_time)

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
        trader = CzscTrader(bg=bg, get_signals=deepcopy(self.get_signals), positions=deepcopy(self.positions),
                            signals_config=deepcopy(self.signals_config), **kwargs)
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

    def get_signals(self, cat, **kwargs) -> OrderedDict:
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


class CzscStrategyExample2(CzscStrategyBase):
    """仅传入Positions就完成策略创建"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def positions(self):
        return [self.create_pos_a(), Position.load(self.create_pos_b())]

    def create_pos_a(self):
        opens = [
            Event(name='开多', operate=Operate.LO, factors=[
                Factor(name="15分钟向下笔停顿", signals_all=[
                    Signal("15分钟_D0停顿分型_BE辅助V230106_看多_强_任意_0"),
                ])
            ]),
            Event(name='开空', operate=Operate.SO, factors=[
                Factor(name="15分钟向上笔停顿", signals_all=[
                    Signal("15分钟_D0停顿分型_BE辅助V230106_看空_强_任意_0"),
                ])
            ]),
        ]
        pos = Position(name="15分钟笔停顿", symbol=self.symbol, opens=opens, exits=None,
                       interval=0, timeout=20, stop_loss=100, T0=True)
        return pos

    def create_pos_b(self):
        """从 json文件 / dict 中加载 Position"""
        return {'symbol': self.symbol,
                'name': '15分钟笔停顿B',
                'opens': [{'name': '开多',
                           'operate': '开多',
                           'signals_all': [],
                           'signals_any': [],
                           'signals_not': [],
                           'factors': [{'name': '15分钟向下笔停顿',
                                        'signals_all': ['15分钟_D0停顿分型_BE辅助V230106_看多_强_任意_0'],
                                        'signals_any': [],
                                        'signals_not': []}]},
                          {'name': '开空',
                           'operate': '开空',
                           'signals_all': [],
                           'signals_any': [],
                           'signals_not': [],
                           'factors': [{'name': '15分钟向上笔停顿',
                                        'signals_all': ['15分钟_D0停顿分型_BE辅助V230106_看空_强_任意_0'],
                                        'signals_any': [],
                                        'signals_not': []}]}],
                'exits': [],
                'interval': 0,
                'timeout': 20,
                'stop_loss': 100,
                'T0': True}


class CzscStocksBeta(CzscStrategyBase):
    """CZSC 股票 Beta 策略"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_signals(self, cat, **kwargs) -> OrderedDict:
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
        """60分钟MACD金叉

        **策略描述：**

        1. 60分钟MACD金叉开多
        2. 60分钟MACD死叉平多
        """
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
        """5日线多头

        **策略特征：**


        """
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
