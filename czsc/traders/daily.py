# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/1 22:20
describe: 日线交易员
"""
import os
import webbrowser
from deprecated import deprecated
from typing import Callable, List
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from ..analyze import CZSC, Freq, Event, RawBar
from ..utils.kline_generator import KlineGeneratorD
from ..utils.bar_generator import BarGenerator
from ..utils.cache import home_path


@deprecated(reason="可以用 CzscAdvancedTrader 对这里的功能实现替代", version='1.0.0')
class CzscDailyTrader:
    """缠中说禅技术分析理论之日线多级别联立交易决策类"""

    def __init__(self, kg: [KlineGeneratorD, BarGenerator], get_signals: Callable, events: List[Event] = None):
        """

        :param kg: K线合成器
        :param get_signals: 自定义的单级别信号计算函数
        :param events: 自定义的交易事件组合，推荐平仓事件放到前面
        """
        self.name = "CzscDailyTrader"
        self.kg = kg
        self.freqs = kg.freqs
        self.events = events
        self.kas = {k: CZSC(b[-1000:], max_bi_count=50, get_signals=get_signals) for k, b in self.kg.bars.items()}
        self.s = self._cal_signals()

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

    def take_snapshot(self, file_html=None, width="1400px", height="580px"):
        """获取快照

        :param file_html: str
            交易快照保存的 html 文件名
        :param width: str
            图表宽度
        :param height: str
            图表高度
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
        file_html = os.path.join(home_path, "temp_czsc_daily_trader.html")
        print(file_html)
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def _cal_signals(self):
        """计算信号"""
        self.symbol = self.kas["日线"].symbol
        self.end_dt = self.kas["日线"].bars_raw[-1].dt
        self.latest_price = self.kas["日线"].bars_raw[-1].close

        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update(ks.signals)

        s.update(self.kas['日线'].bars_raw[-1].__dict__)
        return s

    def update(self, bar: RawBar):
        """更新信号，计算下一个操作动作

        :param bar: 单根K线对象
        :return: 操作提示
        """
        assert bar.freq == Freq.D
        self.kg.update(bar)
        for freq, bar in self.kg.bars.items():
            self.kas[freq].update(bar[-1])
        self.s = self._cal_signals()

