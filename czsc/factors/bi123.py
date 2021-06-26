# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq
from ..factors.utils import match_factor

# ======================================================================================================================
def future_bi123_f15_base(s: [Dict, OrderedDict]):
    """期货15分钟123"""
    v = Factors.Other.value

    for f_ in [Freq.F30.value, Freq.F15.value]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # long_opens = {
    #     Factors.L1A0.value: [
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LB0.value}"],
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LC1.value}"],
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LE0.value}"],
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LE1.value}"],
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LF0.value}"],
    #
    #         [f"{Freq.F15.value}_倒2形态#{Signals.SI0.value}", f"{Freq.F15.value}_倒1三笔#{Signals.X3LE0.value}"],
    #     ],
    #     Factors.L2A0.value: [
    #         [f"{Freq.F15.value}_倒5形态#{Signals.LA0.value}", f"{Freq.F15.value}_倒1形态#{Signals.LG0.value}"],
    #         [f"{Freq.F15.value}_倒5形态#{Signals.LA0.value}", f"{Freq.F15.value}_倒1形态#{Signals.LH0.value}"],
    #     ],
    #     Factors.L3A0.value: [
    #         [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}"],
    #     ]
    # }
    # # 开多仓因子
    # # ------------------------------------------------------------------------------------------------------------------
    # for name, factors in long_opens.items():
    #     for factor in factors:
    #         if match_factor(s, factor):
    #             v = name
    return v


future_bi123_f15 = future_bi123_f15_base
# ======================================================================================================================
def share_bi123_f15_v1(s: [Dict, OrderedDict]):
    """股票15分钟123"""
    v = Factors.Other.value
    freq = Freq.F15.value

    for f_ in [freq]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v
    # # 平多仓因子
    # # --------------------------------------------------------------------------------------------------------------
    # d1_s1 = [
    #     Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
    #     Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    # ]
    # for freq in [Freq.F5.value, Freq.F1.value]:
    #     if s[f'{freq}_倒1形态'] in d1_s1:
    #         v = Factors.S1A0.value
    #
    # # 开多仓因子
    # # --------------------------------------------------------------------------------------------------------------
    # d1_b1 = [Signals.LB0.value, Signals.LD0.value, Signals.LE0.value, Signals.LF0.value]
    # if s[f'{freq}_倒1形态'] in d1_b1:
    #     v = Factors.L1A0.value
    #
    # if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) \
    #         and s[f'{freq}_倒1形态'] in [Signals.LG0.value, Signals.LH0.value]:
    #     v = Factors.L2A0.value
    #
    # if (s[f'{freq}_倒5形态'] in d1_b1 or s[f'{freq}_倒7形态'] in d1_b1) and s[f'{freq}_倒1形态'] in [Signals.LI0.value]:
    #     v = Factors.L2A0.value
    return v


share_bi123_f15 = share_bi123_f15_v1
# ======================================================================================================================
