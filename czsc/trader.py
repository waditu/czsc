# coding: utf-8
import pandas as pd
from datetime import datetime
from .factors import KlineGeneratorBy1Min, CzscFactors
from .data.jq import get_kline, get_kline_period
from .data import freq_map, freq_inv
from .enum import Signals, Factors

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
        kg = KlineGeneratorBy1Min(max_count=max_count*2, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
        for freq in kg.freqs:
            bars = get_kline(symbol, end_date=self.end_date, freq=freq_inv[freq], count=max_count)
            kg.init_kline(freq, bars)
        kf = CzscFactors(kg)
        self.kf = kf
        self.s = kf.s
        self.freqs = kg.freqs

    def __repr__(self):
        return "<CzscTrader of {} @ {}>".format(self.symbol, self.kf.end_dt)

    def run_selector(self):
        """输出日线笔因子"""
        s = self.s
        factors_d = [x.value for x in Factors.__members__.values() if x.name[:2] == 'C6']
        if s['日线笔因子'] in factors_d:
            return s['日线笔因子']
        return "other"

    def run_history(self):
        """查看第N-3笔的历史形态"""
        s = self.s
        nine_values = [x.value for x in Signals.__members__.values() if x.name[:3] in ["X9L", "X9S"]]
        seven_values = [x.value for x in Signals.__members__.values() if x.name[:3] in ["X7L", "X7S"]]
        five_values = [x.value for x in Signals.__members__.values() if x.name[:3] in ["X5L", "X5S"]]

        for freq in ["30分钟", "日线"]:
            if s['{}_倒4的九笔形态'.format(freq)] in nine_values:
                return "{}_倒4的九笔形态_{}".format(freq, s['{}_倒4的九笔形态'.format(freq)])

            if s['{}_倒4的七笔形态'.format(freq)] in seven_values:
                return "{}_倒4的七笔形态_{}".format(freq, s['{}_倒4的七笔形态'.format(freq)])

            if s['{}_倒4的五笔形态'.format(freq)] in five_values:
                return "{}_倒4的五笔形态_{}".format(freq, s['{}_倒4的五笔形态'.format(freq)])
        return "other"

    def take_snapshot(self, file_html, width="1400px", height="680px"):
        self.kf.take_snapshot(file_html, width, height)

    def open_in_browser(self, width="1400px", height="580px"):
        self.kf.open_in_browser(width, height)

    def update_factors(self):
        """更新K线数据到最新状态"""
        bars = get_kline_period(symbol=self.symbol, start_date=self.kf.end_dt, end_date=datetime.now(), freq="1min")
        if not bars:
            return
        for bar in bars:
            self.kf.update_factors([bar])
        self.s = self.kf.s


