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
from typing import Callable, List, AnyStr, Union, Optional
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from czsc.analyze import CZSC
from czsc.objects import Position, RawBar, Signal
from czsc.utils.bar_generator import BarGenerator
from czsc.utils.cache import home_path
from czsc.utils import sorted_freqs, import_by_name
from czsc.traders.sig_parse import get_signals_freqs


class CzscSignals:
    """缠中说禅技术分析理论之多级别信号计算"""

    def __init__(self, bg: Optional[BarGenerator] = None, **kwargs):
        """

        :param bg: K线合成器
        """
        self.name = "CzscSignals"
        # cache 是信号计算过程的缓存容器，需要信号计算函数自行维护
        self.cache = OrderedDict()
        self.kwargs = kwargs
        self.signals_config = kwargs.get("signals_config", [])

        if bg:
            self.bg = bg
            assert bg.symbol, "bg.symbol is None"
            self.symbol = bg.symbol
            self.base_freq = bg.base_freq
            self.freqs = list(bg.bars.keys())
            self.kas = {freq: CZSC(b) for freq, b in bg.bars.items()}

            last_bar = self.kas[self.base_freq].bars_raw[-1]
            self.end_dt, self.bid, self.latest_price = last_bar.dt, last_bar.id, last_bar.close
            self.s = OrderedDict()
            self.s.update(self.get_signals_by_conf())
            self.s.update(last_bar.__dict__)
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

    def get_signals_by_conf(self):
        """通过信号参数配置获取信号

        信号参数配置，格式如下：

            signals_config = [
                {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 1, 'ma_type': 'SMA', 'timeperiod': 5},
                {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 5, 'ma_type': 'SMA', 'timeperiod': 5},
                {'name': 'czsc.signals.tas_double_ma_V221203', 'freq': '日线', 'di': 1, 'ma_seq': (5, 20), 'th': 100},
                {'name': 'czsc.signals.tas_double_ma_V221203', 'freq': '日线', 'di': 5, 'ma_seq': (5, 20), 'th': 100},
            ]

        :return: 信号字典
        """
        s = OrderedDict()
        if not self.signals_config:
            return s

        for param in self.signals_config:
            param = dict(param)
            sig_name = param.pop('name')
            sig_func = import_by_name(sig_name) if isinstance(sig_name, str) else sig_name

            freq = param.pop('freq', None)
            if freq in self.kas:    # 如果指定了 freq，那么就使用 CZSC 对象作为输入
                s.update(sig_func(self.kas[freq], **param))
            else:                   # 否则使用 CAT 作为输入
                s.update(sig_func(self, **param))
        return s

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
        self.s = OrderedDict()
        self.s.update(self.get_signals_by_conf())
        self.s.update(last_bar.__dict__)


def generate_czsc_signals(bars: List[RawBar], signals_config: List[dict],
                          sdt: Union[AnyStr, datetime] = "20170101", init_n: int = 500, df=False, **kwargs):
    """使用 CzscSignals 生成信号

    :param bars: 基础周期 K 线序列
    :param signals_config: 信号函数配置，格式如下：
        signals_config = [
            {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 1, 'ma_type': 'SMA', 'timeperiod': 5},
            {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 5, 'ma_type': 'SMA', 'timeperiod': 5},
            {'name': 'czsc.signals.tas_double_ma_V221203', 'freq': '日线', 'di': 1, 'ma_seq': (5, 20), 'th': 100},
            {'name': 'czsc.signals.tas_double_ma_V221203', 'freq': '日线', 'di': 5, 'ma_seq': (5, 20), 'th': 100},
        ]
    :param sdt: 信号计算开始时间
    :param init_n: 用于 BarGenerator 初始化的基础周期K线数量
    :param df: 是否返回 df 格式的信号计算结果，默认 False
    :return: 信号计算结果
    """
    freqs = get_signals_freqs(signals_config)
    freqs = [freq for freq in freqs if freq != bars[0].freq.value]
    sdt = pd.to_datetime(sdt)                       # type: ignore
    bars_left = [x for x in bars if x.dt < sdt]     # type: ignore
    if len(bars_left) <= init_n:
        bars_left = bars[:init_n]
        bars_right = bars[init_n:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]   # type: ignore

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
    cs = CzscSignals(bg, signals_config=signals_config, **kwargs)
    cs.cache.update({'gsc_kwargs': kwargs})
    for bar in tqdm(bars_right, desc=f'generate signals of {bg.symbol}'):
        cs.update_signals(bar)
        _sigs.append(dict(cs.s))

    if df:
        return pd.DataFrame(_sigs)
    else:
        return _sigs


def check_signals_acc(bars: List[RawBar], signals_config: List[dict], delta_days: int = 5, **kwargs) -> None:
    """人工验证形态信号识别的准确性的辅助工具：

    输入基础周期K线和想要验证的信号，输出信号识别结果的快照

    :param bars: 原始K线
    :param signals_config: 需要验证的信号列表
    :param delta_days: 两次相同信号之间的间隔天数
    :return: None
    """
    base_freq = str(bars[-1].freq.value)
    assert bars[2].dt > bars[1].dt > bars[0].dt and bars[2].id > bars[1].id, "bars 中的K线元素必须按时间升序"
    if len(bars) < 600:
        return

    df = generate_czsc_signals(bars, signals_config=signals_config, df=True, **kwargs)
    s_cols = [x for x in df.columns if len(x.split("_")) == 3]
    signals = []
    for col in s_cols:
        print('=' * 100, "\n", df[col].value_counts())
        signals.extend([Signal(f"{col}_{v}") for v in df[col].unique() if "其他" not in v])

    print(f"signals: {'+' * 100}")
    for row in signals:
        print(f"- {row}")

    bars_left = bars[:500]
    bars_right = bars[500:]
    freqs = get_signals_freqs(signals_config)
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    ct = CzscSignals(bg, signals_config=signals_config, **kwargs)
    last_dt = {signal.key: ct.end_dt for signal in signals}

    for bar in tqdm(bars_right, desc=f'signals of {bg.symbol}'):
        ct.update_signals(bar)

        for signal in signals:
            html_path = os.path.join(home_path, signal.key)
            os.makedirs(html_path, exist_ok=True)
            if bar.dt - last_dt[signal.key] > timedelta(days=delta_days) and signal.is_match(ct.s):
                file_html = f"{bar.symbol}_{bar.dt.strftime('%Y%m%d_%H%M')}_{signal.key}_{ct.s[signal.key]}.html"
                file_html = os.path.join(html_path, file_html)
                print(file_html)
                ct.take_snapshot(file_html, height=kwargs.get("height", "680px"))
                last_dt[signal.key] = bar.dt


def get_unique_signals(bars: List[RawBar], signals_config: List[dict], **kwargs):
    """获取信号函数中定义的所有信号列表

    :param bars: 基础K线数据
    :param signals_config: 信号函数配置
    :param kwargs:
    :return:
    """
    assert bars[2].dt > bars[1].dt > bars[0].dt and bars[2].id > bars[1].id, "bars 中的K线元素必须按时间升序"
    if len(bars) < 600:
        return []

    df = generate_czsc_signals(bars, signals_config=signals_config, df=True, **kwargs)
    _res = []
    for col in [x for x in df.columns if len(x.split("_")) == 3]:
        _res.extend([f"{col}_{v}" for v in df[col].unique() if "其他" not in v])
    return _res


class CzscTrader(CzscSignals):
    """缠中说禅技术分析理论之多级别联立交易决策类（支持多策略独立执行）"""

    def __init__(self, bg: Optional[BarGenerator] = None, positions: Optional[List[Position]] = None,
                 ensemble_method: Union[AnyStr, Callable] = "mean", **kwargs):
        """

        :param bg: bar generator 对象
        :param get_signals: 信号计算函数，输入是 CzscSignals 对象，输出是信号字典
        :param ensemble_method: 多个仓位集成一个仓位的方法，可选值 mean, vote, max；也可以传入一个回调函数

            假设有三个仓位对象，当前仓位分别是 1, 1, -1
            mean - 平均仓位，pos = np.mean([1, 1, -1]) = 0.33
            vote - 投票表决，pos = 1
            max  - 取最大，pos = 1

            对于传入回调函数的情况，函数的输入为 dict，key 为 position.name，value 为 position.pos, 样例输入：
            {'多头策略A': 1, '多头策略B': 1, '空头策略A': -1}
        """
        self.positions = positions
        if self.positions:
            _pos_names = [x.name for x in self.positions]
            assert len(_pos_names) == len(set(_pos_names)), "仓位策略名称不能重复"
        self.__ensemble_method = ensemble_method
        self.name = "CzscTrader"
        super().__init__(bg, **kwargs)

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

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

    @property
    def pos_changed(self) -> bool:
        """判断仓位是否发生变化

        :return: True/False
        """
        if not self.positions:
            return False
        return any([position.pos_changed for position in self.positions])

    def get_ensemble_pos(self, method: Union[AnyStr, Callable] = None) -> float:
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

        method = self.__ensemble_method if not method else method
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
            pos = method({x.name: x.pos for x in self.positions})

        return pos

    def get_position(self, name: str) -> Optional[Position]:
        """获取指定名称的仓位策略对象

        :param name: 仓位名称
        :return: Position
        """
        if not self.positions:
            return None

        for position in self.positions:
            if position.name == name:
                return position

        return None

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
            if freq == self.base_freq and self.positions:
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

    def get_ensemble_weight(self, method: Optional[Union[AnyStr, Callable]] = None):
        """获取 CzscTrader 中所有 positions 按照 method 方法集成之后的权重

        :param method: str or callable
            集成方法，可选值包括：'mean', 'max', 'min', 'vote'
            也可以传入自定义的函数，函数的输入为 dict，key 为 position.name，value 为 position.pos, 样例输入：
                {'多头策略A': 1, '多头策略B': 1, '空头策略A': -1}
        :param kwargs:
        :return: pd.DataFrame
            columns = ['dt', 'symbol', 'weight', 'price']
        """
        from czsc.traders.weight_backtest import get_ensemble_weight
        method = self.__ensemble_method if not method else method
        return get_ensemble_weight(self, method)

    def weight_backtest(self, **kwargs):
        """执行仓位集成权重的回测

        :param kwargs:

            - method: str or callable，集成方法，参考 get_ensemble_weight 方法
            - digits: int，权重小数点后保留的位数，例如 2 表示保留两位小数
            - fee_rate: float，手续费率，例如 0.0002 表示万二
            - res_path: str，回测结果保存路径

        :return: 回测结果
        """
        from czsc.traders.weight_backtest import WeightBacktest

        method = kwargs.get("method", self.__ensemble_method)
        digits = kwargs.get("digits", 2)
        fee_rate = kwargs.get("fee_rate", 0.0002)
        res_path = kwargs.get("res_path", "./weight_backtest")
        dfw = self.get_ensemble_weight(method)
        wb = WeightBacktest(dfw, digits=digits, fee_rate=fee_rate, res_path=res_path)
        _res = wb.backtest()
        return _res
