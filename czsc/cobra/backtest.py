# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/26 23:18
"""
import traceback
from typing import List, Callable
from tqdm import tqdm

from ..objects import RawBar, Freq
from ..signals import get_default_signals
from ..analyze import CzscTrader, KlineGenerator


def generate_signals(f1_raw_bars: List[RawBar],
                     init_count: int = 50000,
                     get_signals: Callable = get_default_signals) -> List[dict]:
    """输入1分钟K线，生成信号列表

    :param init_count: 用于初始化 kg 的1分钟K线数量，默认值为 50000
    :param f1_raw_bars: 1分钟K线列表，按时间升序
    :param get_signals: 自定义的信号计算函数
    :return: 计算好的信号列表
    """
    symbol = f1_raw_bars[0].symbol
    assert f1_raw_bars[0].freq == Freq.F1 \
           and f1_raw_bars[2].dt > f1_raw_bars[1].dt > f1_raw_bars[0].dt \
           and f1_raw_bars[2].id > f1_raw_bars[1].id, "f1_raw_bars 中的K线元素必须是1分钟周期，且按时间升序"
    assert len(f1_raw_bars) > init_count, "1分钟K线数量少于 init_count，无法进行信号计算"

    kg = KlineGenerator(max_count=5000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for bar in f1_raw_bars[:init_count]:
        kg.update(bar)

    ct = CzscTrader(kg, get_signals, events=[])
    signals = []
    for bar in tqdm(f1_raw_bars[init_count:], desc=f"generate signals of {symbol}"):
        try:
            ct.check_operate(bar)
            res = dict(bar.__dict__)
            res.update(ct.s)
            signals.append(res)
        except:
            traceback.print_exc()
    return signals

