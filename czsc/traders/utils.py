# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/12 21:49
"""
import os
import pandas as pd
from tqdm import tqdm
from typing import List, Callable

from ..utils import x_round
from ..utils.bar_generator import BarGenerator
from ..objects import PositionLong, PositionShort, RawBar
from .advanced import CzscAdvancedTrader


freq_cn2ts = {"1分钟": "1min", "5分钟": "5min", "15分钟": "15min", "30分钟": "30min",
              '60分钟': "60min", "日线": "D", "周线": "W", "月线": "M"}


def trader_fast_backtest(bars: List[RawBar],
                         init_n: int,
                         strategy: Callable,
                         html_path: str = None,
                         max_bi_count: int = 50,
                         bi_min_len: int = 7,
                         signals_n: int = 0,
                         T0: bool = False,
                         ):
    """纯 CTA 择时系统快速回测，多空交易通通支持

    :param bars: 原始K线序列
    :param init_n: 用于初始化 BarGenerator 的K线数量
    :param strategy: 策略定义函数
    :param html_path: 交易快照保存路径，默认为 None 的情况下，不保存快照
        注意，保存HTML交易快照非常耗时，建议只用于核对部分标的的交易买卖点时进行保存
    :param max_bi_count: 最大保存的笔数量
        默认值为 50，仅使用内置的信号和因子，不需要调整这个参数。
        如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
    :param bi_min_len: 笔的最小长度，包括左右分型，默认值为 7，是缠论原文老笔定义的长度
    :param signals_n: 缓存n个历史时刻的信号，0 表示不缓存；缓存的数据，主要用于计算信号连续次数
    :param T0: 是否允许T0交易
    :return: 操作列表，交易对，性能评估
    """
    ts_code = bars[0].symbol
    tactic = strategy()

    base_freq = tactic['base_freq']
    freqs = tactic['freqs']
    get_signals = tactic['get_signals']

    long_states_pos = tactic.get("long_states_pos", None)
    long_events = tactic.get("long_events", None)
    long_min_interval = tactic.get("long_min_interval", None)

    short_states_pos = tactic.get("short_states_pos", None)
    short_events = tactic.get("short_events", None)
    short_min_interval = tactic.get("short_min_interval", None)

    bg = BarGenerator(base_freq, freqs, max_count=5000)
    for bar in bars[:init_n]:
        bg.update(bar)

    if long_states_pos:
        long_pos = PositionLong(ts_code, T0=T0, long_min_interval=long_min_interval,
                                hold_long_a=long_states_pos['hold_long_a'],
                                hold_long_b=long_states_pos['hold_long_b'],
                                hold_long_c=long_states_pos['hold_long_c'])
        assert long_events is not None
    else:
        long_pos = None
        long_events = None

    if short_states_pos:
        short_pos = PositionShort(ts_code, T0=T0, short_min_interval=short_min_interval,
                                  hold_short_a=short_states_pos['hold_short_a'],
                                  hold_short_b=short_states_pos['hold_short_b'],
                                  hold_short_c=short_states_pos['hold_short_c'])
        assert short_events is not None
    else:
        short_pos = None
        short_events = None

    ct = CzscAdvancedTrader(bg, get_signals,
                            long_events=long_events, long_pos=long_pos,
                            short_events=short_events, short_pos=short_pos,
                            signals_n=signals_n, max_bi_count=max_bi_count, bi_min_len=bi_min_len)

    signals = []
    long_holds = []
    short_holds = []
    for bar in tqdm(bars[init_n:], desc=f"{ts_code} bt"):
        ct.update(bar)
        signals.append(ct.s)
        if ct.long_pos:
            long_holds.append({'dt': ct.end_dt, 'symbol': ct.symbol, 'long_pos': ct.long_pos.pos})
            if ct.long_pos.pos_changed and html_path:
                op = ct.long_pos.operates[-1]
                file_name = f"{op['op'].value}_{op['bid']}_{x_round(op['price'], 2)}_{op['op_desc']}.html"
                file_html = os.path.join(html_path, file_name)
                ct.take_snapshot(file_html)
                print(f'snapshot saved into {file_html}')

        if ct.short_pos:
            short_holds.append({'dt': ct.end_dt, 'symbol': ct.symbol, 'short_pos': ct.short_pos.pos})
            if ct.short_pos.pos_changed and html_path:
                op = ct.short_pos.operates[-1]
                file_name = f"{op['op'].value}_{op['bid']}_{x_round(op['price'], 2)}_{op['op_desc']}.html"
                file_html = os.path.join(html_path, file_name)
                ct.take_snapshot(file_html)
                print(f'snapshot saved into {file_html}')

    p = {"开始时间": bars[init_n].dt.strftime("%Y-%m-%d %H:%M"),
         "结束时间": bars[-1].dt.strftime("%Y-%m-%d %H:%M"),
         "基准收益": round(bars[-1].close / bars[init_n].close - 1, 4)}

    res = {"signals": signals}
    if ct.long_pos:
        df_holds = pd.DataFrame(long_holds)
        cover = df_holds['long_pos'].mean()
        res['long_holds'] = df_holds
        res['long_operates'] = ct.long_pos.operates
        res['long_pairs'] = ct.long_pos.pairs
        res['long_performance'] = ct.long_pos.evaluate_operates()
        res['long_performance'].update(dict(p))
        res['long_performance'].update({"覆盖率": x_round(cover, 4)})

    if ct.short_pos:
        df_holds = pd.DataFrame(short_holds)
        cover = df_holds['short_pos'].mean()
        res['short_holds'] = pd.DataFrame(short_holds)
        res['short_operates'] = ct.short_pos.operates
        res['short_pairs'] = ct.short_pos.pairs
        res['short_performance'] = ct.short_pos.evaluate_operates()
        res['short_performance'].update(dict(p))
        res['short_performance'].update({"覆盖率": x_round(cover, 4)})

    return res

