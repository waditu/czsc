# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq

def third_buy_base(s: [Dict, OrderedDict], freqs: List[Freq], sub_freqs: List[Freq]):
    """

    :param s: 信号表
    :param freqs: 本级别名称
    :param sub_freqs: 次级别名称
    :return:
    """
    v = Factors.Other.value

    for freq in freqs + sub_freqs:
        if freq not in s['级别列表']:
            warnings.warn(f"{freq} not in {s['级别列表']}，默认返回 Other")
            return v

    for freq in freqs:
        if s[f'{freq}_倒1形态'] in [Signals.LI0.value]:
            v = Factors.L3A0.value

    for freq in freqs:
        xt = [
            Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
            Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
        ]
        if s[f'{freq}_倒1形态'] in xt:
            v = Factors.S1A0.value

    return v

# ======================================================================================================================
def future_third_buy_f5_base(s):
    """期货5分钟三买"""
    return third_buy_base(s, [Freq.F5.value], [Freq.F1.value])


future_third_buy_f5 = future_third_buy_f5_base
# ======================================================================================================================
def share_third_buy_f5_base(s):
    """股票5分钟三买"""
    return third_buy_base(s, [Freq.F5.value], [Freq.F1.value])

def share_third_buy_f15_base(s):
    """股票15分钟三买"""
    return third_buy_base(s, [Freq.F15.value], [Freq.F1.value])


share_third_buy_f5 = share_third_buy_f5_base
share_third_buy_f15 = share_third_buy_f15_base
# ======================================================================================================================

