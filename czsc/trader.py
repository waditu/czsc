# coding: utf-8
import pandas as pd
from datetime import datetime
from .factors import KlineGeneratorBy1Min, CzscFactors
from .data.jq import get_kline
from .data import freq_map, freq_inv
from .enum import FdNine, FdFive, FdSeven, FdThree, Factors
from .objects import RawBar

class CzscTrader:
    """缠中说禅股票 选股/择时"""
    def __init__(self, symbol, max_count=1000, end_date=None):
        """
        :param symbol:
        """
        self.symbol = symbol
        if end_date:
            self.end_date = pd.to_datetime(end_date)
        else:
            self.end_date = datetime.now()
        self.max_count = max_count
        self.__generate_factors()

    def __generate_factors(self):
        symbol = self.symbol
        max_count = self.max_count
        end_date = self.end_date

        kg = KlineGeneratorBy1Min(max_count=max_count*2, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
        for freq in kg.freqs:
            bars = get_kline(symbol, end_date=end_date, freq=freq_inv[freq], count=max_count)
            kg.init_kline(freq, bars)
        kf = CzscFactors(kg, max_count=max_count)
        self.kf = kf
        self.s = kf.s
        self.end_dt = self.kf.end_dt
        self.freqs = kg.freqs

    def run_selector(self):
        """执行选股：优先输出大级别的机会"""
        s = self.s
        factors_d = [Factors.DLA1.value, Factors.DLA2.value, Factors.DLA3.value,
                     Factors.DLA4.value, Factors.DLA5.value,
                     Factors.DLB1.value, Factors.DLB2.value]
        if s['日线右侧多头因子'] in factors_d:
            return s['日线右侧多头因子']
        return "other"

    def run_history(self):
        """查看第N-3笔的历史形态"""
        s = self.s
        nine_values = [x.value for x in FdNine.__members__.values() if x.name[0] in ["L", "S"]]
        seven_values = [x.value for x in FdSeven.__members__.values() if x.name[0] in ["L", "S"]]
        five_values = [x.value for x in FdFive.__members__.values() if x.name[0] in ["L", "S"]]

        for freq in ["30分钟", "日线"]:
            if s['{}_第N-3笔的五笔形态'.format(freq)] in five_values:
                return "{}_第N-3笔的五笔形态_{}".format(freq, s['{}_第N-3笔的五笔形态'.format(freq)])

            if s['{}_第N-3笔的七笔形态'.format(freq)] in seven_values:
                return "{}_第N-3笔的七笔形态_{}".format(freq, s['{}_第N-3笔的七笔形态'.format(freq)])

            if s['{}_第N-3笔的九笔形态'.format(freq)] in nine_values:
                return "{}_第N-3笔的九笔形态_{}".format(freq, s['{}_第N-3笔的九笔形态'.format(freq)])
        return "other"

    def take_snapshot(self, file_html, width="1400px", height="680px"):
        self.kf.take_snapshot(file_html, width, height)

    def monitor(self, bar: RawBar):
        """盘中实时监控函数"""
        pass

