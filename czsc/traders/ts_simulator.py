# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/5 23:09
describe: 基于Tushare数据的仿真跟踪
"""
import os
import dill
import inspect
import traceback
import pandas as pd
from tqdm import tqdm
from typing import Callable, List

from .. import envs
from ..data import TsDataCache, freq_cn2ts
from ..utils import x_round, BarGenerator
from ..objects import cal_break_even_point
from ..objects import PositionLong, PositionShort, RawBar
from .advanced import CzscAdvancedTrader


class TradeSimulator:
    """交易策略仿真跟踪"""

    def __init__(self, dc: TsDataCache, strategy: Callable, res_path=None):
        self.name = self.__class__.__name__
        self.dc = dc
        self.strategy = strategy
        self.tactic = strategy()
        self.base_freq = self.tactic['base_freq']

        self.data_path = dc.data_path
        if not res_path:
            self.res_path = os.path.join(self.data_path, f"{strategy.__name__}_mbl{envs.get_min_bi_len()}")
        else:
            self.res_path = res_path
        os.makedirs(self.res_path, exist_ok=True)
        os.makedirs(os.path.join(self.res_path, 'traders'), exist_ok=True)

        file_strategy = os.path.join(self.res_path, f'{strategy.__name__}_strategy.txt')
        with open(file_strategy, 'w', encoding='utf-8') as f:
            f.write(inspect.getsource(strategy))
        print(f"strategy saved into {file_strategy}")

    def get_bars(self, ts_code: str, asset: str, sdt=None) -> List[RawBar]:
        """获取指定周期K线序列

        :param ts_code: 标的代码
        :param asset: 资产类别
        :param sdt: 开始时间
        :return:
        """
        base_freq = self.base_freq
        dc = self.dc
        freq = freq_cn2ts[base_freq]
        sdt = dc.sdt if not sdt else sdt
        if "分钟" in base_freq:
            bars = dc.pro_bar_minutes(ts_code, sdt, dc.edt, freq=freq, asset=asset, adj='hfq', raw_bar=True)
        else:
            bars = dc.pro_bar(ts_code, sdt, dc.edt, freq=freq, asset=asset, adj='hfq', raw_bar=True)
        return bars

    def get_file_trader(self, ts_code, asset):
        return os.path.join(self.res_path, f"traders/{ts_code}_{asset}.cat")

    def create_trader(self, ts_code, asset="E"):
        """创建单个标的交易员

        :param ts_code:
        :param asset:
        :return:
        """
        strategy = self.strategy

        # 解析策略参数
        tactic = strategy()
        base_freq = tactic['base_freq']
        freqs = tactic['freqs']
        get_signals = tactic['get_signals']

        long_states_pos = tactic.get("long_states_pos", None)
        long_events = tactic.get("long_events", None)
        long_min_interval = tactic.get("long_min_interval", None)

        short_states_pos = tactic.get("short_states_pos", None)
        short_events = tactic.get("short_events", None)
        short_min_interval = tactic.get("short_min_interval", None)
        signals_n = tactic.get("signals_n", 0)
        T0 = tactic.get("T0", False)
        init_bars_number = tactic.get("init_bars_number", 500)

        if long_states_pos:
            long_pos = PositionLong(ts_code, T0=T0, long_min_interval=long_min_interval,
                                    hold_long_a=long_states_pos['hold_long_a'],
                                    hold_long_b=long_states_pos['hold_long_b'],
                                    hold_long_c=long_states_pos['hold_long_c'])
            assert long_events is not None
        else:
            long_pos = None
            long_events = None

        if short_states_pos:
            short_pos = PositionShort(ts_code, T0=T0, short_min_interval=short_min_interval,
                                      hold_short_a=short_states_pos['hold_short_a'],
                                      hold_short_b=short_states_pos['hold_short_b'],
                                      hold_short_c=short_states_pos['hold_short_c'])
            assert short_events is not None
        else:
            short_pos = None
            short_events = None

        # 获取K线，创建交易员
        bars = self.get_bars(ts_code, asset)
        bg = BarGenerator(base_freq, freqs, max_count=5000)
        for bar in bars[:init_bars_number]:
            bg.update(bar)

        trader = CzscAdvancedTrader(bg, get_signals, long_events=long_events, long_pos=long_pos,
                                    short_events=short_events, short_pos=short_pos, signals_n=signals_n)
        for bar in tqdm(bars[init_bars_number:], desc=f"{ts_code} trader"):
            trader.update(bar)

        file_trader = self.get_file_trader(ts_code, asset)
        dill.dump(trader, open(file_trader, 'wb'))
        return trader

    def update_trader(self, ts_code, asset="E"):
        file_trader = self.get_file_trader(ts_code, asset)
        if os.path.exists(file_trader):
            trader: CzscAdvancedTrader = dill.load(open(file_trader, 'rb'))
        else:
            trader: CzscAdvancedTrader = self.create_trader(ts_code, asset)

        bars = self.get_bars(ts_code, asset, trader.end_dt)
        bars = [x for x in bars if x.dt > trader.bg.end_dt]
        for bar in bars:
            trader.update(bar)

        dill.dump(trader, open(file_trader, 'wb'))


