# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq

# ======================================================================================================================
def future_bi_end_f30_base(s: [Dict, OrderedDict]):
    """期货30分钟笔结束"""
    v = Factors.Other.value
    freq = Freq.F30.value
    sub_freqs = [Freq.F5.value, Freq.F1.value]

    for f_ in [freq] + sub_freqs:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    if s[f'{freq}_倒1表里关系'] == Signals.BD0.value and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    if s[f'{freq}_倒1表里关系'] == Signals.BU0.value and s[f'{freq}_倒1空头区间']:
        v = Factors.S2A0.value
    return v


future_bi_end_f30 = future_bi_end_f30_base
# ======================================================================================================================

def share_bi_end_f60_base(s: [Dict, OrderedDict]):
    """股票60分钟笔结束"""
    v = Factors.Other.value
    freq = Freq.F60.value
    sub_freqs = [Freq.F15.value, Freq.F5.value]

    for f_ in [freq] + sub_freqs:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v
    # 平多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    if s[f'{freq}_倒1表里关系'] == Signals.BU0.value and s[f'{freq}_倒1空头区间']:
        v = Factors.S2A0.value

    # 开多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    if s[f'{freq}_倒1表里关系'] == Signals.BD0.value and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value
    return v

def share_bi_end_f60_v1(s: [Dict, OrderedDict]):
    """股票60分钟笔结束"""
    v = Factors.Other.value
    freq = Freq.F60.value
    sub_freqs = [Freq.F15.value, Freq.F5.value]

    for f_ in [freq] + sub_freqs:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 平多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    for freq in sub_freqs:
        if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
            v = Factors.S1A0.value

    # 开多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    if s[f'{freq}_倒1表里关系'] == Signals.BD0.value and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value
    return v


share_bi_end_f60 = share_bi_end_f60_v1
# ======================================================================================================================


