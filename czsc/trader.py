# coding: utf-8
import pandas as pd
from datetime import datetime
from .factors import KlineGeneratorBy1Min, CzscFactors
from .data.jq import get_kline
from .enum import FdNine, FdFive, FdSeven, FdThree, Factors

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
        self.freqs = ['1分钟', '5分钟', '30分钟', '日线']

    def __generate_factors(self):
        symbol = self.symbol
        max_count = self.max_count
        end_date = self.end_date

        kg = KlineGeneratorBy1Min(max_count=max_count*2, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '日线'])
        k1min = get_kline(symbol, end_date=end_date, freq="1min", count=max_count)
        k5min = get_kline(symbol, end_date=end_date, freq="5min", count=max_count)
        k15min = get_kline(symbol, end_date=end_date, freq="15min", count=max_count)
        k30min = get_kline(symbol, end_date=end_date, freq="30min", count=max_count)
        kd = get_kline(symbol, end_date=end_date, freq="D", count=max_count)
        kg.init_kline("1分钟", k1min)
        kg.init_kline("5分钟", k5min)
        kg.init_kline("15分钟", k15min)
        kg.init_kline("30分钟", k30min)
        kg.init_kline("日线", kd)
        kf = CzscFactors(kg, max_count=max_count)
        self.kf = kf
        self.s = kf.s
        self.end_dt = self.kf.end_dt

    def run_selector(self):
        """执行选股：优先输出大级别的机会"""
        s = self.s
        if s['日线右侧多头因子'] in [Factors.DLA1.value, Factors.DLA2.value, Factors.DLA3.value, Factors.DLA4.value]:
            return s['日线右侧多头因子']

        ka = self.kf.kas['30分钟']
        max_high = max([x.high for x in ka.bi_list[-10:]])

        # third_bs = ["三买A1", "三买B1", "三买C1", "三买D1"]
        if "三买" in s['30分钟_第N笔的五笔形态']:
            if s['1分钟_第N笔的七笔形态'] == FdSeven.L3A1.value:
                return "30分钟第三买点且BaA式右侧底A"
            elif max_high == ka.bi_list[-2].high:
                return "30分钟第三买点且第4笔创近9笔新高"
            else:
                return "30分钟第三买点"

        # nine_values = [x.value for x in FdNine.__members__.values() if x.name[0] in ["L", "S"]]
        # seven_values = [x.value for x in FdSeven.__members__.values() if x.name[0] in ["L", "S"]]
        # if s['30分钟_第N笔的七笔形态'] in seven_values:
        #     return "30分钟_第N笔的七笔形态_{}".format(s['30分钟_第N笔的七笔形态'])
        # if s['30分钟_第N笔的九笔形态'] in nine_values:
        #     return "30分钟_第N笔的九笔形态_{}".format(s['30分钟_第N笔的九笔形态'])
        return "other"

    def run_history(self):
        """对已经完成的三买走势进行研究"""
        s = self.s
        if "三买" in s['30分钟_第N-2笔的五笔形态']:
            return "30分钟第N-2笔第三买点"
        return "other"

    def take_snapshot(self, file_html, width="1400px", height="680px"):
        self.kf.take_snapshot(file_html, width, height)
