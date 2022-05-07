# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/7 17:09
describe: 支持分批买入卖出的高级交易员
"""
import os
import webbrowser
import pandas as pd
from collections import OrderedDict
from typing import Callable, List
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from ..analyze import CZSC, signals_counter
from ..objects import PositionLong, PositionShort, Operate, Event, RawBar
from ..utils import BarGenerator, x_round
from ..utils.cache import home_path
from .. import envs


class CzscAdvancedTraderBackup:
    """缠中说禅技术分析理论之多级别联立交易决策类（支持分批开平仓 / 支持从任意周期开始交易）"""

    def __init__(self,
                 bg: BarGenerator,
                 get_signals: Callable,
                 long_events: List[Event] = None,
                 long_pos: PositionLong = None,
                 short_events: List[Event] = None,
                 short_pos: PositionShort = None,
                 signals_n: int = 0,
                 ):
        """

        :param bg: K线合成器
        :param get_signals: 自定义信号计算函数
        :param long_events: 自定义的多头交易事件组合，推荐平仓事件放到前面
        :param long_pos: 多头仓位对象
        :param short_events: 自定义的空头交易事件组合，推荐平仓事件放到前面
        :param short_pos: 空头仓位对象
        :param signals_n: 缓存n个历史时刻的信号，0 表示不缓存；缓存的数据，主要用于计算信号连续次数
        """
        self.name = "CzscAdvancedTrader"
        self.bg = bg
        self.symbol = bg.symbol
        self.base_freq = bg.base_freq
        self.freqs = list(bg.bars.keys())
        self.get_signals = get_signals
        self.long_events = long_events
        self.long_pos = long_pos
        self.long_holds = []                    # 记录基础周期结束时间对应的多头仓位信息
        self.short_events = short_events
        self.short_pos = short_pos
        self.short_holds = []                   # 记录基础周期结束时间对应的空头仓位信息
        self.signals_n = signals_n
        self.signals_list = []
        self.verbose = envs.get_verbose()
        self.kas = {freq: CZSC(b) for freq, b in bg.bars.items()}

        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
        self.s = self.get_signals(self)

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

        signals = {k: v for k, v in self.s.items() if len(k.split("_")) == 3}
        for freq in self.freqs:
            freq_signals = {k: signals[k] for k in signals.keys() if k.startswith("{}_".format(freq))}
            for k in freq_signals.keys():
                signals.pop(k)
            if len(freq_signals) <= 0:
                continue
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in freq_signals.items()])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, f"{freq}信号")

        if len(signals) > 0:
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in signals.items()])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, "其他信号")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        file_html = os.path.join(home_path, "temp_czsc_advanced_trader.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def update(self, bar: RawBar):
        """输入基础周期已完成K线，更新信号，更新仓位"""
        self.bg.update(bar)
        for freq, b in self.bg.bars.items():
            self.kas[freq].update(b[-1])

        self.symbol = symbol = bar.symbol
        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
        dt, bid, price = self.end_dt, self.bid, self.latest_price
        self.s = self.get_signals(self)
        if self.signals_n > 0:
            self.signals_list.append(self.s)
            self.signals_list = self.signals_list[-self.signals_n:]
            self.s.update(signals_counter(self.signals_list))

        last_n1b = last_bar.close / self.kas[self.base_freq].bars_raw[-2].close - 1
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
            if self.long_holds:
                self.long_holds[-1]['n1b'] = last_n1b
            self.long_holds.append({'dt': dt, 'symbol': symbol, 'long_pos': self.long_pos.pos, 'n1b': 0})

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
            if self.short_holds:
                self.short_holds[-1]['n1b'] = -last_n1b
            self.short_holds.append({'dt': dt, 'symbol': symbol, 'short_pos': self.short_pos.pos, 'n1b': 0})

    @property
    def results(self):
        """汇集回测相关结果"""
        res = {}
        ct = self
        dt_fmt = "%Y-%m-%d %H:%M"
        if ct.long_pos:
            df_holds = pd.DataFrame(ct.long_holds)

            p = {"开始时间": df_holds['dt'].min().strftime(dt_fmt),
                 "结束时间": df_holds['dt'].max().strftime(dt_fmt),
                 "基准收益": x_round(df_holds['n1b'].sum(), 4),
                 "覆盖率": x_round(df_holds['long_pos'].mean(), 4)}

            df_holds['持仓收益'] = df_holds['long_pos'] * df_holds['n1b']
            df_holds['累计基准'] = df_holds['n1b'].cumsum()
            df_holds['累计收益'] = df_holds['持仓收益'].cumsum()

            res['long_holds'] = df_holds
            res['long_operates'] = ct.long_pos.operates
            res['long_pairs'] = ct.long_pos.pairs
            res['long_performance'] = ct.long_pos.evaluate_operates()
            res['long_performance'].update(dict(p))

        if ct.short_pos:
            df_holds = pd.DataFrame(ct.short_holds)

            p = {"开始时间": df_holds['dt'].min().strftime(dt_fmt),
                 "结束时间": df_holds['dt'].max().strftime(dt_fmt),
                 "基准收益": x_round(df_holds['n1b'].sum(), 4),
                 "覆盖率": x_round(df_holds['short_pos'].mean(), 4)}

            df_holds['持仓收益'] = df_holds['short_pos'] * df_holds['n1b']
            df_holds['累计基准'] = df_holds['n1b'].cumsum()
            df_holds['累计收益'] = df_holds['持仓收益'].cumsum()

            res['short_holds'] = df_holds
            res['short_operates'] = ct.short_pos.operates
            res['short_pairs'] = ct.short_pos.pairs
            res['short_performance'] = ct.short_pos.evaluate_operates()
            res['short_performance'].update(dict(p))

        return res


class CzscAdvancedTrader:
    """缠中说禅技术分析理论之多级别联立交易决策类（支持分批开平仓 / 支持从任意周期开始交易）"""

    def __init__(self, bg: BarGenerator, strategy: Callable):
        """

        :param bg: K线合成器
        :param strategy: 择时策略描述函数
            注意，strategy 函数必须是仅接受一个 symbol 参数的函数
        """
        self.name = "CzscAdvancedTrader"
        self.bg = bg
        assert bg.symbol, "bg.symbol is None"
        self.symbol = bg.symbol
        self.strategy = strategy
        tactic = self.strategy(self.symbol)
        self.tactic = tactic
        self.base_freq = bg.base_freq
        self.freqs = list(bg.bars.keys())
        self.get_signals = tactic['get_signals']
        self.long_events = tactic['long_events']
        self.long_pos: PositionLong = tactic['long_pos']
        self.long_holds = []                    # 记录基础周期结束时间对应的多头仓位信息
        self.short_events = tactic['short_events']
        self.short_pos: PositionShort = tactic['short_pos']
        self.short_holds = []                   # 记录基础周期结束时间对应的空头仓位信息
        self.signals_n = tactic['signals_n']
        self.signals_list = []
        self.verbose = envs.get_verbose()
        self.kas = {freq: CZSC(b) for freq, b in bg.bars.items()}

        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
        if self.get_signals:
            self.s = self.get_signals(self)
        else:
            self.s = OrderedDict()

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

        signals = {k: v for k, v in self.s.items() if len(k.split("_")) == 3}
        for freq in self.freqs:
            freq_signals = {k: signals[k] for k in signals.keys() if k.startswith("{}_".format(freq))}
            for k in freq_signals.keys():
                signals.pop(k)
            if len(freq_signals) <= 0:
                continue
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in freq_signals.items()])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, f"{freq}信号")

        if len(signals) > 0:
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in signals.items()])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, "其他信号")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        file_html = os.path.join(home_path, "temp_czsc_advanced_trader.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def update(self, bar: RawBar):
        """输入基础周期已完成K线，更新信号，更新仓位"""
        self.bg.update(bar)
        for freq, b in self.bg.bars.items():
            self.kas[freq].update(b[-1])

        self.symbol = symbol = bar.symbol
        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
        dt, bid, price = self.end_dt, self.bid, self.latest_price

        if self.get_signals:
            self.s = self.get_signals(self)

        if self.signals_n > 0:
            self.signals_list.append(self.s)
            self.signals_list = self.signals_list[-self.signals_n:]
            self.s.update(signals_counter(self.signals_list))

        last_n1b = last_bar.close / self.kas[self.base_freq].bars_raw[-2].close - 1
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
            if self.long_holds:
                self.long_holds[-1]['n1b'] = last_n1b
            self.long_holds.append({'dt': dt, 'symbol': symbol, 'long_pos': self.long_pos.pos, 'n1b': 0})

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
            if self.short_holds:
                self.short_holds[-1]['n1b'] = -last_n1b
            self.short_holds.append({'dt': dt, 'symbol': symbol, 'short_pos': self.short_pos.pos, 'n1b': 0})

    @property
    def results(self):
        """汇集回测相关结果"""
        res = {}
        ct = self
        dt_fmt = "%Y-%m-%d %H:%M"
        if ct.long_pos:
            df_holds = pd.DataFrame(ct.long_holds)

            p = {"开始时间": df_holds['dt'].min().strftime(dt_fmt),
                 "结束时间": df_holds['dt'].max().strftime(dt_fmt),
                 "基准收益": x_round(df_holds['n1b'].sum(), 4),
                 "覆盖率": x_round(df_holds['long_pos'].mean(), 4)}

            df_holds['持仓收益'] = df_holds['long_pos'] * df_holds['n1b']
            df_holds['累计基准'] = df_holds['n1b'].cumsum()
            df_holds['累计收益'] = df_holds['持仓收益'].cumsum()

            res['long_holds'] = df_holds
            res['long_operates'] = ct.long_pos.operates
            res['long_pairs'] = ct.long_pos.pairs
            res['long_performance'] = ct.long_pos.evaluate_operates()
            res['long_performance'].update(dict(p))

        if ct.short_pos:
            df_holds = pd.DataFrame(ct.short_holds)

            p = {"开始时间": df_holds['dt'].min().strftime(dt_fmt),
                 "结束时间": df_holds['dt'].max().strftime(dt_fmt),
                 "基准收益": x_round(df_holds['n1b'].sum(), 4),
                 "覆盖率": x_round(df_holds['short_pos'].mean(), 4)}

            df_holds['持仓收益'] = df_holds['short_pos'] * df_holds['n1b']
            df_holds['累计基准'] = df_holds['n1b'].cumsum()
            df_holds['累计收益'] = df_holds['持仓收益'].cumsum()

            res['short_holds'] = df_holds
            res['short_operates'] = ct.short_pos.operates
            res['short_pairs'] = ct.short_pos.pairs
            res['short_performance'] = ct.short_pos.evaluate_operates()
            res['short_performance'].update(dict(p))

        return res


def create_advanced_trader(bg: BarGenerator, raw_bars: List[RawBar], strategy: Callable) -> CzscAdvancedTrader:
    """为交易策略 tactic 创建对应的 trader

    :param bg: K线生成器
    :param raw_bars: 用来初始化 trader 的K线
    :param strategy: 择时交易策略
    :return: trader
    """
    trader = CzscAdvancedTrader(bg, strategy)
    for bar in raw_bars:
        trader.update(bar)
    return trader

