# coding: utf-8
from datetime import datetime
from .factors import KlineFactors, KlineGeneratorBy1Min
from .data.jq import get_kline

class CzscTrader:
    """缠中说禅股票 选股/择时"""
    def __init__(self, symbol, max_count=1000):
        """
        :param symbol:
        """
        self.symbol = symbol
        self.max_count = max_count
        self.__generate_factors()
        self.freqs = ['1分钟', '5分钟', '30分钟', '日线']

    def __generate_factors(self):
        symbol = self.symbol
        max_count = self.max_count
        end_date = datetime.now()
        kg = KlineGeneratorBy1Min(max_count=max_count*2, freqs=['1分钟', '5分钟', '30分钟', '日线'])
        k1min = get_kline(symbol, end_date=end_date, freq="1min", count=max_count)
        k5min = get_kline(symbol, end_date=end_date, freq="5min", count=max_count)
        k30min = get_kline(symbol, end_date=end_date, freq="30min", count=max_count)
        kd = get_kline(symbol, end_date=end_date, freq="D", count=max_count)
        kg.init_kline("1分钟", k1min.to_dict("records"))
        kg.init_kline("5分钟", k5min.to_dict("records"))
        kg.init_kline("30分钟", k30min.to_dict("records"))
        kg.init_kline("日线", kd.to_dict("records"))
        kf = KlineFactors(kg, bi_mode="new", max_count=max_count)
        self.kf = kf
        self.s = kf.s
        self.end_dt = self.kf.end_dt

    def run_selector(self):
        """执行选股：优先输出大级别的机会"""
        s = self.s

        if s['30分钟_最近两个笔中枢状态'] == '向下':
            return "30分钟最近两个笔中枢向下"

        if s['30分钟_第N笔涨跌力度'] == '向下笔新低盘背' or s['5分钟_五笔趋势类背驰'] == 'down':
            if s["日线_第N笔第三买卖"] == '三买':
                return "日线第三买点"

            if s['日线_五笔趋势类背驰'] == 'down':
                return "日线五笔下跌趋势类背驰"

            if s['日线_第N笔出井'] == "向下小井" and (s['日线_第N-2笔出井'] == "向下小井"
                                            or s['日线_第N-2笔涨跌力度'] == '向下笔新低盘背'):
                return "日线向下小井"

            if s['日线_第N笔出井'] == "向下大井":
                return "日线向下大井"

        if s['5分钟_第N笔涨跌力度'] == '向下笔新低盘背' or s['1分钟_五笔趋势类背驰'] == 'down':
            if s['30分钟_三笔回调构成第三买卖点'] == '三买':
                return "30分钟三笔回调构成第三买点"

            if s["30分钟_第N笔第三买卖"] == '三买':
                return "30分钟第三买点"

            if s['30分钟_五笔趋势类背驰'] == 'down':
                return "30分钟五笔下跌趋势类背驰"
        return "other"

    def take_snapshot(self, file_html, width="950px", height="480px"):
        self.kf.take_snapshot(file_html, width, height)

    def long_open(self):
        """执行开仓择时"""
        s = self.signals

    def long_close(self):
        """执行平仓择时"""
        s = self.signals
