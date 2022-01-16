# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 17:09
describe: 支持分批买入卖出的高级交易员
"""
import os
import webbrowser
from typing import Callable, List
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from ..analyze import CZSC
from ..objects import PositionLong, PositionShort, Operate, Event, RawBar
from ..utils.bar_generator import BarGenerator
from ..utils.cache import home_path


class CzscAdvancedTrader:
    """缠中说禅技术分析理论之多级别联立交易决策类（支持分批开平仓 / 支持从任意周期开始交易）"""

    def __init__(self,
                 bg: BarGenerator,
                 get_signals: Callable,
                 long_events: List[Event] = None,
                 long_pos: PositionLong = None,
                 short_events: List[Event] = None,
                 short_pos: PositionShort = None,
                 max_bi_count: int = 50,
                 bi_min_len: int = 7,
                 signals_n: int = 0,
                 verbose: bool = False,
                 ):
        """

        :param bg: K线合成器
        :param get_signals: 自定义的单级别信号计算函数
        :param long_events: 自定义的多头交易事件组合，推荐平仓事件放到前面
        :param long_pos: 多头仓位对象
        :param short_events: 自定义的空头交易事件组合，推荐平仓事件放到前面
        :param short_pos: 空头仓位对象
        :param max_bi_count: 单个级别最大保存笔的数量
        :param bi_min_len: 一笔最小无包含K线数量
        :param signals_n: 见 `CZSC` 对象
        :param verbose: 是否显示更多信息，默认为False
        """
        self.name = "CzscAdvancedTrader"
        self.bg = bg
        self.base_freq = bg.base_freq
        self.freqs = list(bg.bars.keys())
        self.long_events = long_events
        self.long_pos = long_pos
        self.short_events = short_events
        self.short_pos = short_pos
        self.verbose = verbose
        self.kas = {freq: CZSC(b, max_bi_count=max_bi_count,
                               get_signals=get_signals, signals_n=signals_n,
                               bi_min_len=bi_min_len, verbose=verbose)
                    for freq, b in bg.bars.items()}
        self.s = self._cal_signals()

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

    def take_snapshot(self, file_html=None, width: str = "1400px", height: str = "580px"):
        """获取快照

        :param file_html: 交易快照保存的 html 文件名
        :param width: 图表宽度
        :param height: 图表高度
        :return:
        """
        tab = Tab(page_title="{}@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = self.kas[freq].to_echarts(width, height)
            tab.add(chart, freq)

        for freq in self.freqs:
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if k.startswith("{}_".format(freq))])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, "{}信号表".format(freq))

        t2 = Table()
        ths_ = [["同花顺F10",  "http://basic.10jqka.com.cn/{}".format(self.symbol[:6])]]
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k] + ths_)
        t2.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅因子表", subtitle=""))
        tab.add(t2, "因子表")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        file_html = os.path.join(home_path, "temp_czsc_advanced_trader.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def _cal_signals(self):
        """计算信号"""
        base_freq = self.base_freq
        self.symbol = self.kas[base_freq].symbol
        self.end_dt = self.kas[base_freq].bars_raw[-1].dt
        self.bid = self.kas[base_freq].bars_raw[-1].id
        self.latest_price = self.kas[base_freq].bars_raw[-1].close

        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update(ks.signals)

        s.update(self.kas[base_freq].bars_raw[-1].__dict__)
        return s

    def update(self, bar: RawBar):
        """输入1分钟K线，更新信号，更新仓位"""
        self.bg.update(bar)
        for freq, b in self.bg.bars.items():
            self.kas[freq].update(b[-1])
        self.s = self._cal_signals()
        dt = self.end_dt
        price = self.latest_price
        bid = self.bid

        # 遍历 long_events，更新 long_pos
        if self.long_events:
            assert isinstance(self.long_pos, PositionLong), "long_events 必须配合 PositionLong 使用"

            op = Operate.HO
            op_desc = ""

            for event in self.long_events:
                m, f = event.is_match(self.s)
                if m:
                    op = event.operate
                    op_desc = f"{event.name}@{f}"
                    break

            self.long_pos.update(dt, op, price, bid, op_desc)

        # 遍历 short_events，更新 short_pos
        if self.short_events:
            assert isinstance(self.short_pos, PositionShort), "short_events 必须配合 PositionShort 使用"

            op = Operate.HO
            op_desc = ""

            for event in self.short_events:
                m, f = event.is_match(self.s)
                if m:
                    op = event.operate
                    op_desc = f"{event.name}@{f}"
                    break

            self.short_pos.update(dt, op, price, bid, op_desc)


