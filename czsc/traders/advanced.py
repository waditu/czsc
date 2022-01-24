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
from ..objects import PositionLong, PositionShort, Operate, Signal, Event, RawBar
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

    def get_s_position(self, pos: [PositionLong, PositionShort]):
        """计算多头持仓信号

        :return:
        """
        if isinstance(pos, PositionLong):
            k1 = "多头"
        elif isinstance(pos, PositionShort):
            k1 = "空头"
        else:
            raise ValueError

        s = OrderedDict()
        default_signals = [
            Signal(k1=k1, k2="最大", k3='盈利', v1="其他", v2="其他", v3="其他"),
            Signal(k1=k1, k2="最大", k3='回撤', v1="其他", v2="其他", v3="其他"),
            Signal(k1=k1, k2="最大", k3='回撤盈利比', v1="其他", v2="其他", v3="其他"),

            Signal(k1=k1, k2="累计", k3='盈亏', v1="其他", v2="其他", v3="其他"),
            Signal(k1=k1, k2="持仓", k3='时间', v1="其他", v2="其他", v3="其他"),
            Signal(k1=k1, k2="持仓", k3='基础K线数量', v1="其他", v2="其他", v3="其他"),
        ]
        for signal_ in default_signals:
            s[signal_.key] = signal_.value

        if pos.pos == 0:
            return s

        base_freq = self.base_freq
        latest_price = self.latest_price
        bid = self.bg.bars[base_freq][-1].id
        end_dt = self.bg.bars[base_freq][-1].dt

        if isinstance(pos, PositionLong):
            last_o = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]
            last_o_price = last_o['price']
            yl = pos.long_high / last_o_price - 1                   # 最大盈利
            hc = abs(latest_price / pos.long_high - 1)              # 最大回撤
            yk = (latest_price - last_o_price) / last_o_price       # 累计盈亏
        else:
            last_o = [x for x in pos.operates[-50:] if x['op'] == Operate.SO][-1]
            last_o_price = last_o['price']
            yl = last_o_price / pos.short_low - 1                   # 最大盈利
            hc = abs(pos.short_low / latest_price - 1)              # 最大回撤
            yk = (last_o_price - latest_price) / last_o_price       # 累计盈亏

        last_o_dt = last_o['dt']
        last_o_bid = last_o['bid']

        hc_yl_rate = hc / (yl + 0.000001)                   # 最大回撤盈利比
        hold_time = (end_dt - last_o_dt).total_seconds()   # 持仓时间，单位：秒
        hold_nbar = bid - last_o_bid                       # 持仓基础K线数量
        assert yl >= 0 and hc >= 0 and hc_yl_rate >= 0

        # ----------------------------------------------------------------------------------
        if yl > 0.15:
            v1 = "超过1500BP"
        elif yl > 0.1:
            v1 = "超过1000BP"
        elif yl > 0.08:
            v1 = "超过800BP"
        elif yl > 0.05:
            v1 = "超过500BP"
        elif yl > 0.03:
            v1 = "超过300BP"
        else:
            v1 = "低于300BP"
        v = Signal(k1=k1, k2="最大", k3='盈利', v1=v1)
        s[v.key] = v.value

        # ----------------------------------------------------------------------------------
        if hc > 0.15:
            v1 = "超过1500BP"
        elif hc > 0.1:
            v1 = "超过1000BP"
        elif hc > 0.08:
            v1 = "超过800BP"
        elif hc > 0.05:
            v1 = "超过500BP"
        elif hc > 0.03:
            v1 = "超过300BP"
        else:
            v1 = "低于300BP"
        v = Signal(k1=k1, k2="最大", k3='回撤', v1=v1)
        s[v.key] = v.value

        # ----------------------------------------------------------------------------------
        if hc_yl_rate > 0.8:
            v1 = "大于08"
        elif hc_yl_rate > 0.6:
            v1 = "大于06"
        elif hc_yl_rate > 0.5:
            v1 = "大于05"
        elif hc_yl_rate > 0.3:
            v1 = "大于03"
        else:
            v1 = "小于03"
        v = Signal(k1=k1, k2="最大", k3='回撤盈利比', v1=v1)
        s[v.key] = v.value

        # ----------------------------------------------------------------------------------
        if yk >= 0:
            v1 = "盈利"
        else:
            v1 = "亏损"

        if abs(yk) > 0.15:
            v2 = "超过1500BP"
        elif abs(yk) > 0.1:
            v2 = "超过1000BP"
        elif abs(yk) > 0.08:
            v2 = "超过800BP"
        elif abs(yk) > 0.05:
            v2 = "超过500BP"
        elif abs(yk) > 0.03:
            v2 = "超过300BP"
        else:
            v2 = "低于300BP"
        v = Signal(k1=k1, k2="累计", k3='盈亏', v1=v1, v2=v2)
        s[v.key] = v.value

        # ----------------------------------------------------------------------------------
        if hold_time > 3600 * 24 * 13:
            v1 = "超过13天"
        elif hold_time > 3600 * 24 * 8:
            v1 = "超过8天"
        elif hold_time > 3600 * 24 * 5:
            v1 = "超过5天"
        elif hold_time > 3600 * 24 * 3:
            v1 = "超过3天"
        else:
            v1 = "低于3天"
        v = Signal(k1=k1, k2="持仓", k3='时间', v1=v1)
        s[v.key] = v.value

        # ----------------------------------------------------------------------------------
        if hold_nbar > 300:
            v1 = "超过300根"
        elif hold_nbar > 200:
            v1 = "超过200根"
        elif hold_nbar > 150:
            v1 = "超过150根"
        elif hold_nbar > 100:
            v1 = "超过100根"
        elif hold_nbar > 50:
            v1 = "超过50根"
        else:
            v1 = "低于50根"
        v = Signal(k1=k1, k2="持仓", k3='基础K线数量', v1=v1)
        s[v.key] = v.value

        return s

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
        if self.long_pos:
            s.update(self.get_s_position(self.long_pos))
        if self.short_pos:
            s.update(self.get_s_position(self.short_pos))
        return s

    def update(self, bar: RawBar):
        """输入基础周期已完成K线，更新信号，更新仓位"""
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


