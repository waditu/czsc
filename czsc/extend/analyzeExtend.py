from czsc import CZSC, CzscTrader
from czsc.objects import *
from czsc.enum import Freq
import pandas as pd
from czsc.analyze import KlineGenerator
from czsc.data.jq import get_kline
from czsc.data.base import freq_inv
from czsc.signals import get_default_signals
from typing import Union
from abc import abstractmethod


class CZSCExtendTrader(CzscTrader):
    def __init__(self, symbol, max_count=1000, end_date=None,
                 freq_list: List[Union[str, Freq]] = ["1分钟", "5分钟", "30分钟", "日线"]):
        self.symbol = symbol
        if end_date:
            self.end_date = pd.to_datetime(end_date)
        else:
            self.end_date = datetime.now()
        self.max_count = max_count
        kg = KlineGenerator(max_count=max_count, freqs=freq_list)
        self._init_kline_data(symbol=symbol, kg=kg, freq_list=freq_list, max_count=max_count)
        super(CZSCExtendTrader, self).__init__(kg, get_signals=get_default_signals, events=[])

    @abstractmethod
    def _init_kline_data(self, symbol: str, kg: KlineGenerator, freq_list: List[Union[str, Freq]] = None,
                         max_count: int = 1000):
        """
        设置数据获取方式
        :param symbol:
        :param kg:
        :param freq_list:
        :param max_count:
        :return:
        """
        for freq in kg.freqs:
            bars = get_kline(symbol, end_date=self.end_date, freq=freq_inv[freq], count=max_count)
            kg.init_kline(freq, bars)
