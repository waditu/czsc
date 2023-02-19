# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/24 22:20
describe: 简单的单仓位策略执行
"""
import os
import webbrowser
import numpy as np
import pandas as pd
from tqdm import tqdm
from loguru import logger
from datetime import datetime, timedelta
from deprecated import deprecated
from collections import OrderedDict
from typing import Callable, List, AnyStr, Union
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from czsc.analyze import CZSC
from czsc.objects import Position, RawBar, Signal
from czsc.utils.bar_generator import BarGenerator
from czsc.utils.cache import home_path


class CzscSignals:
    """缠中说禅技术分析理论之多级别信号计算"""

    def __init__(self, bg: BarGenerator = None, get_signals: Callable = None):
        """

        :param bg: K线合成器
        :param get_signals: 信号计算函数
        """
        self.name = "CzscSignals"
        self.get_signals: Callable = get_signals
        # cache 是信号计算过程的缓存容器，需要信号计算函数自行维护
        self.cache = OrderedDict()

        if bg:
            self.bg = bg
            assert bg.symbol, "bg.symbol is None"
            self.symbol = bg.symbol
            self.base_freq = bg.base_freq
            self.freqs = list(bg.bars.keys())
            self.kas = {freq: CZSC(b) for freq, b in bg.bars.items()}

            last_bar = self.kas[self.base_freq].bars_raw[-1]
            self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
            if self.get_signals:
                self.s = self.get_signals(self)
                self.s.update(last_bar.__dict__)
            else:
                self.s = OrderedDict()
        else:
            self.bg = None
            self.symbol = None
            self.base_freq = None
            self.freqs = None
            self.kas = None
            self.end_dt, self.bid, self.latest_price = None, None, None
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
            chart = ka.to_echarts(width, height)
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

    def update_signals(self, bar: RawBar):
        """输入基础周期已完成K线，更新信号，更新仓位"""
        self.bg.update(bar)
        for freq, b in self.bg.bars.items():
            self.kas[freq].update(b[-1])

        self.symbol = bar.symbol
        last_bar = self.kas[self.base_freq].bars_raw[-1]
        self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close

        if self.get_signals:
            self.s = self.get_signals(self)
            self.s.update(last_bar.__dict__)


def generate_czsc_signals(bars: List[RawBar], get_signals: Callable, freqs: List[AnyStr],
                          sdt: Union[AnyStr, datetime] = "20170101", init_n: int = 500, df=False, **kwargs):
    """使用 CzscSignals 生成信号

    :param bars: 基础周期 K 线序列
    :param get_signals: 信号计算函数
    :param freqs: K 线周期序列，不需要填写基础周期
    :param sdt: 信号计算开始时间
    :param init_n: 用于 BarGenerator 初始化的基础周期K线数量
    :param df: 是否返回 df 格式的信号计算结果，默认 False
    :return: 信号计算结果
    """
    sdt = pd.to_datetime(sdt)
    bars_left = [x for x in bars if x.dt < sdt]
    if len(bars_left) <= init_n:
        bars_left = bars[:init_n]
        bars_right = bars[init_n:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]

    if len(bars_right) == 0:
        logger.warning("右侧K线为空，无法进行信号生成", category=RuntimeWarning)
        if df:
            return pd.DataFrame()
        else:
            return []

    base_freq = str(bars[0].freq.value)
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=kwargs.get("bg_max_count", 5000))
    for bar in bars_left:
        bg.update(bar)

    _sigs = []
    cs = CzscSignals(bg, get_signals)
    for bar in tqdm(bars_right, desc=f'generate signals of {bg.symbol}'):
        cs.update_signals(bar)
        _sigs.append(dict(cs.s))

    if df:
        return pd.DataFrame(_sigs)
    else:
        return _sigs


def check_signals_acc(bars: List[RawBar], get_signals: Callable, delta_days: int = 5, **kwargs) -> None:
    """人工验证形态信号识别的准确性的辅助工具：

    输入基础周期K线和想要验证的信号，输出信号识别结果的快照

    :param bars: 原始K线
    :param get_signals: 需要验证的信号列表
    :param delta_days: 两次相同信号之间的间隔天数
    :return: None
    """
    base_freq = str(bars[-1].freq.value)
    assert bars[2].dt > bars[1].dt > bars[0].dt and bars[2].id > bars[1].id, "bars 中的K线元素必须按时间升序"
    if len(bars) < 600:
        return

    if not kwargs.get('freqs', None):
        sorted_freqs = ['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线']
        freqs = sorted_freqs[sorted_freqs.index(base_freq) + 1:]
    else:
        freqs = kwargs['freqs']

    df = generate_czsc_signals(bars, get_signals, freqs, df=True, **kwargs)
    s_cols = [x for x in df.columns if len(x.split("_")) == 3]
    signals = []
    for col in s_cols:
        signals.extend([Signal(f"{col}_{v}") for v in df[col].unique() if "其他" not in v])

    print(f"signals: {'+' * 100}")
    for row in signals:
        print(f"- {row}")

    bars_left = bars[:500]
    bars_right = bars[500:]
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    ct = CzscSignals(bg, get_signals)
    last_dt = {signal.key: ct.end_dt for signal in signals}

    for bar in tqdm(bars_right, desc=f'signals of {bg.symbol}'):
        ct.update_signals(bar)

        for signal in signals:
            html_path = os.path.join(home_path, signal.key)
            os.makedirs(html_path, exist_ok=True)
            if bar.dt - last_dt[signal.key] > timedelta(days=delta_days) and signal.is_match(ct.s):
                file_html = f"{bar.symbol}_{signal.key}_{ct.s[signal.key]}_{bar.dt.strftime('%Y%m%d_%H%M')}.html"
                file_html = os.path.join(html_path, file_html)
                print(file_html)
                ct.take_snapshot(file_html)
                last_dt[signal.key] = bar.dt


class CzscTrader(CzscSignals):
    """缠中说禅技术分析理论之多级别联立交易决策类（支持多策略独立执行）"""

    def __init__(self, bg: BarGenerator = None, get_signals: Callable = None, positions: List[Position] = None):
        super().__init__(bg, get_signals=get_signals)
        self.positions = positions

    def update(self, bar: RawBar) -> None:
        """输入基础周期已完成K线，更新信号，更新仓位

        :param bar: 基础周期已完成K线
        :return: None
        """
        self.update_signals(bar)
        if self.positions:
            for position in self.positions:
                position.update(self.s)

    def on_sig(self, sig: dict) -> None:
        """通过信号字典直接交易

        主要用于快速回测场景

        :param sig: 信号字典
        :return: None
        """
        self.s = sig
        self.symbol, self.end_dt = self.s['symbol'], self.s['dt']
        self.bid, self.latest_price = self.s['id'], self.s['close']
        if self.positions:
            for position in self.positions:
                position.update(self.s)

    def on_bar(self, bar: RawBar) -> None:
        """输入基础周期已完成K线，更新信号，更新仓位

        :param bar: 基础周期已完成K线
        :return: None
        """
        self.update(bar)

    def get_ensemble_pos(self, method: Union[AnyStr, Callable] = "mean"):
        """获取多个仓位的集成仓位

        :param method: 多个仓位集成一个仓位的方法，可选值 mean, vote, max；也可以传入一个回调函数

            假设有三个仓位对象，当前仓位分别是 1, 1, -1
            mean - 平均仓位，pos = np.mean([1, 1, -1]) = 0.33
            vote - 投票表决，pos = 1
            max  - 取最大，pos = 1

            对于传入回调函数的情况，输入是 self.positions

        :return: pos, 集成仓位
        """
        if not self.positions:
            return 0

        if isinstance(method, str):
            method = method.lower()
            pos_seq = [x.pos for x in self.positions]

            if method == 'mean':
                pos = np.mean(pos_seq)
            elif method == 'vote':
                pos = np.sign(sum(pos_seq))
            elif method == 'max':
                pos = max(pos_seq)
            else:
                raise ValueError

        else:
            pos = method(self.positions)

        return pos

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
                for pos in self.positions:
                    for op in pos.operates:
                        if op['dt'] >= ka.bars_raw[0].dt:
                            _op = dict(op)
                            _op['op_desc'] = f"{pos.name} | {_op['op_desc']}"
                            bs.append(_op)

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

