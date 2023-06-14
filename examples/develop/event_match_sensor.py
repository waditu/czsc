# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/15 12:54
describe: Event Match Sensor
"""
import sys
sys.path.insert(0, '..')
sys.path.insert(0, '../..')

from copy import deepcopy
from czsc.objects import Event
from typing import List, Union, Dict, Callable
from czsc.traders.sig_parse import get_signals_freqs
from czsc.traders.base import generate_czsc_signals


class EventMatchSensor:
    def __init__(self, 
                 event: Union[Dict, Event], 
                 symbols: List[str], 
                 read_bars: Callable, **kwargs) -> None:
        """
        事件匹配传感器

        :param event: 事件配置
        :param symbols: 事件匹配的标的
        :param read_bars: 读取K线数据的函数，函数签名如下：
            read_bars(symbol, freq, sdt, edt, fq='前复权', **kwargs) -> List[RawBar]
        :param kwargs: 读取K线数据的函数的参数
        """
        self.symbols = symbols
        self.read_bars = read_bars
        self.event = Event.load(event) if isinstance(event, dict) else event

        self.signals_module = kwargs.pop("signals_module", "czsc.signals")
        self.signals_config = self.event.get_signals_config(signals_module=self.signals_module)
        self.freqs = get_signals_freqs(self.signals_config)
        self.base_freq = self.freqs[0]

        self.bar_sdt = kwargs.pop("bar_sdt", "2017-01-01")
        self.sdt = kwargs.pop("sdt", "2018-01-01")
        self.edt = kwargs.pop("edt", "2022-01-01")
        self.kwargs = kwargs


    def single_symbol(self, symbol):
        """单个symbol的事件匹配"""
        bars = self.read_bars(symbol, freq=self.base_freq, sdt=self.bar_sdt, edt=self.edt, **self.kwargs)
        sigs = generate_czsc_signals(bars, deepcopy(self.signals_config), sdt=self.sdt, df=True)
        sigs[['event_match', 'factor']] = sigs.apply(self.event.is_match, axis=1, result_type="expand")
        return sigs

