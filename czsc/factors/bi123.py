# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq

# ======================================================================================================================
def future_bi123_f15_base(s: [Dict, OrderedDict]):
    """期货15分钟123C"""
    v = Factors.Other.value
    freq = Freq.F30.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    # 倒1一买
    d1_b1 = [Signals.LB0.value, Signals.LC0.value, Signals.LC1.value, Signals.LD0.value,
             Signals.LE0.value, Signals.LE1.value, Signals.LF0.value]
    # d1_b1 = [Signals.LB0.value, Signals.LC0.value, Signals.LD0.value,
    #          Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    # 平多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    # 倒1一卖
    # d1_s1 = [
    #     Signals.SA0.value, Signals.SB0.value, Signals.SC0.value, Signals.SC1.value,
    #     Signals.SD0.value, Signals.SE0.value, Signals.SE1.value, Signals.SF0.value
    # ]
    # d1_s1 = [
    #     Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
    #     Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    # ]
    # if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
    #     v = Factors.S1A0.value
    return v

def future_bi123_f15_v1(s: [Dict, OrderedDict]):
    """期货15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_b1 = [Signals.LB0.value, Signals.LD0.value, Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LG0.value] and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
        v = Factors.S1A0.value
    return v

def future_bi123_f15_v2(s: [Dict, OrderedDict]):
    """期货15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_b1 = [Signals.LB0.value, Signals.LD0.value, Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LG0.value, Signals.LH0.value] and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LI0.value] and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
        v = Factors.S1A0.value
    return v

def future_bi123_f15_v3(s: [Dict, OrderedDict]):
    """期货15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v
    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    for freq in [Freq.F5.value, Freq.F1.value]:
        if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
            v = Factors.S1A0.value

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_b1 = [Signals.LB0.value, Signals.LD0.value, Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LG0.value, Signals.LH0.value] \
            and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LI0.value] and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value
    return v


future_bi123_f15 = future_bi123_f15_base
# ======================================================================================================================
def share_bi123_f15_base(s: [Dict, OrderedDict]):
    """股票15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    # 倒1一买
    d1_b1 = [Signals.LB0.value, Signals.LC0.value, Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    # 倒1一卖
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
        v = Factors.S1A0.value
    return v

def share_bi123_f15_v1(s: [Dict, OrderedDict]):
    """股票15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v
    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_s1 = [
        Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
        Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    ]
    for freq in [Freq.F5.value, Freq.F1.value]:
        if s[f'{freq}_倒1形态'] in d1_s1 and s[f'{freq}_倒1空头区间']:
            v = Factors.S1A0.value

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    d1_b1 = [Signals.LB0.value, Signals.LD0.value, Signals.LE0.value, Signals.LF0.value]
    if s[f'{freq}_倒1形态'] in d1_b1 and s[f'{freq}_倒1多头区间']:
        v = Factors.L1A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LG0.value, Signals.LH0.value] \
            and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value

    if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
            and s[f'{freq}_倒1形态'] in [Signals.LI0.value] and s[f'{freq}_倒1多头区间']:
        v = Factors.L2A0.value
    return v


share_bi123_f15 = share_bi123_f15_v1
# ======================================================================================================================
