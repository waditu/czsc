# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq
from ..factors.utils import match_factor

# ======================================================================================================================
def future_bi_end_f30_base(s: [Dict, OrderedDict]):
    """期货30分钟笔结束"""
    v = Factors.Other.value
    for f_ in [Freq.F30.value, Freq.F5.value, Freq.F1.value]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    long_opens = {
        Factors.L2A0.value: [
            [f"{Freq.F30.value}_倒1表里关系#{Signals.BD0.value}"],
        ]
    }

    for name, factors in long_opens.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name

    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    long_exits = {
        Factors.S2A0.value: [
            [f"{Freq.F30.value}_倒1表里关系#{Signals.BU0.value}"],
        ]
    }

    for name, factors in long_exits.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name
    return v


future_bi_end_f30 = future_bi_end_f30_base
# ======================================================================================================================

def share_bi_end_f30_base(s: [Dict, OrderedDict]):
    """股票30分钟笔结束"""
    v = Factors.Other.value
    for f_ in [Freq.F30.value, Freq.F5.value, Freq.F1.value]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v
    # 平多仓因子
    # --------------------------------------------------------------------------------------------------------------
    long_exits = {
        Factors.S2A0.value: [
            [f"{Freq.F30.value}_倒1表里关系#{Signals.BU0.value}"],
        ]
    }

    for name, factors in long_exits.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name

    # 开多仓因子
    # --------------------------------------------------------------------------------------------------------------
    long_opens = {
        Factors.L2A0.value: [
            [f"{Freq.F30.value}_倒1表里关系#{Signals.BD0.value}"],
        ]
    }

    for name, factors in long_opens.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name
    return v


share_bi_end_f30 = share_bi_end_f30_base
# ======================================================================================================================


