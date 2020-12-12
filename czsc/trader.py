# coding: utf-8
from datetime import datetime
import traceback
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from .signals import KlineSignals
from .data.jq import get_kline
from .data import freq_map
from .utils.plot import ka_to_echarts


class CzscTrader:
    """缠中说禅股票 选股/择时"""
    def __init__(self, symbol):
        """
        :param symbol:
        """
        self.symbol = symbol
        self.__generate_signals()
        self.freqs = ['1分钟', '5分钟', '30分钟', '日线']

    def __generate_signals(self):
        self.signals = {"symbol": self.symbol}
        self.kas = dict()
        for freq in ['1min', '5min', '30min', 'D']:
            try:
                kline = get_kline(symbol=self.symbol, end_date=datetime.now(), freq=freq, count=300)
                ks = KlineSignals(kline, name=freq_map.get(freq, "本级别"), bi_mode="new", max_count=300, use_xd=False)
                self.signals.update(ks.get_signals())
                self.kas[freq_map.get(freq, "本级别")] = ks
            except:
                traceback.print_exc()
        self.end_dt = self.kas['1分钟'].end_dt
        self.latest_price = self.kas['1分钟'].kline_raw[-1]['close']

    def run_selector(self):
        """执行选股：优先输出大级别的机会"""
        s = self.signals
        if s['30分钟_第N笔涨跌力度'] == '向下笔新低盘背' or s['5分钟_五笔趋势类背驰'] == 'down':
            if s['日线_三笔回调构成第三买卖点'] == '三买':
                return "日线三笔回调构成第三买点"

            if s["日线_第N笔第三买卖"] == '三买':
                return "日线第三买点"

            if s['日线_五笔趋势类背驰'] == 'down':
                return "日线五笔下跌趋势类背驰"

            if s['日线_第N笔出井'] == "向下小井" and s['日线_第N-2笔出井'] == "向下小井":
                return "日线连续两次向下小井"

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
        tab = Tab(page_title="{}的交易快照@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = ka_to_echarts(self.kas[freq], width, height)
            tab.add(chart, freq)

        headers = ["名称", "数据"]
        rows = [[k, v] for k, v in self.signals.items()]
        table = Table()
        table.add(headers, rows)
        table.set_global_opts(title_opts=ComponentTitleOpts(title="缠论信号", subtitle=""))
        tab.add(table, "信号表")
        tab.render(file_html)

    def long_open(self):
        """执行开仓择时"""
        s = self.signals

    def long_close(self):
        """执行平仓择时"""
        s = self.signals
