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
from czsc.analyze import CZSC
from czsc.objects import PositionLong, PositionShort, Operate, Event, RawBar
from czsc.utils import BarGenerator, x_round
from czsc.utils.cache import home_path


class CzscAdvancedTrader:
    """缠中说禅技术分析理论之多级别联立交易决策类（支持分批开平仓 / 支持从任意周期开始交易）"""

    def __init__(self, bg: BarGenerator, strategy: Callable = None):
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
        tactic = self.strategy(self.symbol) if strategy else {}
        self.tactic = tactic
        self.base_freq = bg.base_freq
        self.freqs = list(bg.bars.keys())
        self.get_signals: Callable = tactic.get('get_signals')
        self.long_events: List[Event] = tactic.get('long_events', None)
        self.long_pos: PositionLong = tactic.get('long_pos', None)
        self.long_holds = []                    # 记录基础周期结束时间对应的多头仓位信息
        self.short_events: List[Event] = tactic.get('short_events', None)
        self.short_pos: PositionShort = tactic.get('short_pos', None)
        self.short_holds = []                   # 记录基础周期结束时间对应的空头仓位信息
        self.kas = {freq: CZSC(b) for freq, b in bg.bars.items()}

        # cache 是信号计算过程的缓存容器，需要信号计算函数自行维护
        self.cache = OrderedDict()

        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
        if self.get_signals:
            self.s = self.get_signals(self)
            self.s.update(last_bar.__dict__)
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
            ka: CZSC = self.kas[freq]
            bs = None
            if freq == self.base_freq:
                # 在基础周期K线上加入最近的操作记录
                bs = []
                if self.long_pos:
                    for op in self.long_pos.operates[-10:]:
                        if op['dt'] >= ka.bars_raw[0].dt:
                            bs.append(op)

                if self.short_pos:
                    for op in self.short_pos.operates[-10:]:
                        if op['dt'] >= ka.bars_raw[0].dt:
                            bs.append(op)

            chart = ka.to_echarts(width, height, bs)
            tab.add(chart, freq)

        signals = {k: v for k, v in self.s.items() if len(k.split("_")) == 3}
        for freq in self.freqs:
            # 按各周期K线分别加入信号表
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
            # 加入时间、持仓状态之类的其他信号
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
            self.s.update(last_bar.__dict__)

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


class CzscDummyTrader:
    """虚拟交易员，直接输入信号驱动，不需要输入K线

    缠中说禅技术分析理论之多级别联立交易决策类（支持分批开平仓 / 支持从任意周期开始交易）"""

    def __init__(self, dfs, strategy: Callable):
        """

        :param dfs: 信号数据
        :param strategy: 择时策略描述函数
            注意，strategy 函数必须是仅接受一个 symbol 参数的函数
        """
        self.name = "CzscDummyTrader"
        self.symbol = dfs.iloc[0]['symbol']
        self.strategy = strategy
        tactic = self.strategy(self.symbol)
        self.tactic = tactic
        self.long_events = tactic.get('long_events', None)
        self.long_pos: PositionLong = tactic.get('long_pos', None)
        self.long_holds = []                    # 记录基础周期结束时间对应的多头仓位信息
        self.short_events = tactic.get('short_events', None)
        self.short_pos: PositionShort = tactic.get('short_pos', None)
        self.short_holds = []                   # 记录基础周期结束时间对应的空头仓位信息
        self.end_dt, self.bid, self.latest_price = None, None, None
        rows = dfs.to_dict('records')
        for row in rows:
            self.update(row)

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

    def update(self, s: dict):
        """输入基础周期已完成K线，更新信号，更新仓位"""
        symbol = s['symbol']
        n1b = s['close'] / self.latest_price - 1 if self.latest_price else 0
        self.end_dt, self.bid, self.latest_price = s['dt'], s['id'], s['close']
        dt, bid, price = self.end_dt, self.bid, self.latest_price

        if self.long_events:
            assert isinstance(self.long_pos, PositionLong), "long_events 必须配合 PositionLong 使用"
            op, op_desc = Operate.HO, ""
            for event in self.long_events:
                m, f = event.is_match(s)
                if m:
                    op = event.operate
                    op_desc = f"{event.name}@{f}"
                    break

            self.long_pos.update(dt, op, price, bid, op_desc)
            if self.long_holds:
                self.long_holds[-1]['n1b'] = n1b
            self.long_holds.append({'dt': dt, 'symbol': symbol, 'long_pos': self.long_pos.pos, 'n1b': 0})

        # 遍历 short_events，更新 short_pos
        if self.short_events:
            assert isinstance(self.short_pos, PositionShort), "short_events 必须配合 PositionShort 使用"
            op, op_desc = Operate.HO, ""
            for event in self.short_events:
                m, f = event.is_match(s)
                if m:
                    op = event.operate
                    op_desc = f"{event.name}@{f}"
                    break

            self.short_pos.update(dt, op, price, bid, op_desc)
            if self.short_holds:
                self.short_holds[-1]['n1b'] = -n1b
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
