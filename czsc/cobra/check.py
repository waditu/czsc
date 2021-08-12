# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/7/16 11:43
"""

import os
from tqdm import tqdm
from typing import Dict, List, Callable
from datetime import timedelta

from ..objects import RawBar, Signal, Factor, Event, Freq
from ..analyze import KlineGenerator, CzscTrader
from ..signals import get_default_signals
from ..utils.cache import home_path


def check_signals_acc(f1_raw_bars: List[RawBar],
                      signals: List[Signal],
                      get_signals: Callable = get_default_signals) -> None:
    """人工验证形态信号识别的准确性的辅助工具：
    输入1分钟K线和想要验证的信号，输出信号识别结果的快照

    :param f1_raw_bars: 1分钟原始K线
    :param signals: 需要验证的信号列表
    :param get_signals: 信号计算函数
    :return:
    """

    assert len(f1_raw_bars) > 50000, "1分钟K线数量至少是5万根"
    assert f1_raw_bars[0].freq == Freq.F1 \
           and f1_raw_bars[2].dt > f1_raw_bars[1].dt > f1_raw_bars[0].dt \
           and f1_raw_bars[2].id > f1_raw_bars[1].id, "f1_raw_bars 中的K线元素必须是1分钟周期，且按时间升序"

    dt_fmt = "%Y%m%d_%H%M"
    kg = KlineGenerator(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in f1_raw_bars[:30000]:
        kg.update(row)

    ct = CzscTrader(kg, get_signals=get_signals, events=[])
    last_dt = {signal.key: ct.end_dt for signal in signals}

    for row in tqdm(f1_raw_bars[30000:], desc='generate_snapshots'):
        if isinstance(row, Dict):
            bar = RawBar(symbol=row['symbol'], open=round(row['open'], 2), dt=row['dt'], vol=row['vol'],
                         close=round(row['close'], 2), high=round(row['high'], 2), low=round(row['low'], 2))
        else:
            bar = row
        ct.check_operate(bar)

        for signal in signals:
            html_path = os.path.join(home_path, signal.key)
            os.makedirs(html_path, exist_ok=True)
            if bar.dt - last_dt[signal.key] > timedelta(days=5) and signal.is_match(ct.s):
                file_html = os.path.join(html_path, f"{bar.symbol}_{signal.value}_{bar.dt.strftime(dt_fmt)}.html")
                print(file_html)
                ct.take_snapshot(file_html)
                last_dt[signal.key] = bar.dt

