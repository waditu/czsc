# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/12 21:49
"""
import os
from tqdm import tqdm
from typing import List, Callable

from ..utils.bar_generator import BarGenerator
from ..objects import PositionLong, RawBar
from .advanced import CzscAdvancedTrader


def fast_back_test(bars: List[RawBar],
                   init_n: int,
                   strategy: Callable,
                   html_path: str = None,
                   max_bi_count: int = 50,
                   bi_min_len: int = 7,
                   signals_n: int = 0,
                   ):
    """快速回测系统（暂时仅支持多头交易回测）

    :param bars: 原始K线序列
    :param init_n: 用于初始化 BarGenerator 的K线数量
    :param strategy: 策略定义函数
    :param html_path: 交易快照保存路径，默认为 None 的情况下，不保存快照
        注意，保存HTML交易快照非常耗时，建议只用于核对部分标的的交易买卖点时进行保存
    :param bi_min_len: 笔的最小长度，包括左右分型，默认值为 7，是缠论原文老笔定义的长度
    :param signals_n: 缓存n个历史时刻的信号，0 表示不缓存；缓存的数据，主要用于计算信号连续次数
    :param max_bi_count: 最大保存的笔数量
        默认值为 50，仅使用内置的信号和因子，不需要调整这个参数。
        如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
    :return: 操作列表，交易对，性能评估
    """
    ts_code = bars[0].symbol
    base_freq, freqs, states_pos, get_signals, get_events = strategy()

    bg = BarGenerator(base_freq, freqs, max_count=5000)
    for bar in bars[:init_n]:
        bg.update(bar)
    long_pos = PositionLong(ts_code, T0=False,
                            hold_long_a=states_pos['hold_long_a'],
                            hold_long_b=states_pos['hold_long_b'],
                            hold_long_c=states_pos['hold_long_c'])
    ct = CzscAdvancedTrader(bg, get_signals, long_events=get_events(), long_pos=long_pos,
                            signals_n=signals_n, max_bi_count=max_bi_count, bi_min_len=bi_min_len)

    for bar in tqdm(bars[init_n:], desc=f"{ts_code} bt"):
        ct.update(bar)
        if ct.long_pos.pos_changed and html_path:
            op = ct.long_pos.operates[-1]
            file_html = os.path.join(html_path, f"{op['bid']}_{op['price']}_{op['op_desc']}.html")
            ct.take_snapshot(file_html)
            print(f'snapshot saved into {file_html}')

    p = {"开始时间": bars[init_n].dt.strftime("%Y-%m-%d %H:%M"),
         "结束时间": bars[-1].dt.strftime("%Y-%m-%d %H:%M"),
         "基准收益": round(bars[-1].close / bars[init_n].close - 1, 4)}
    p.update(ct.long_pos.evaluate_operates())
    return long_pos.operates, long_pos.pairs, p
