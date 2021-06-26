# coding: utf-8
import warnings
from typing import List, Dict, OrderedDict
from ..enum import Signals, Factors, Freq
from ..factors.utils import match_factor

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

    # for freq in freqs:
    #     if s[f'{freq}_倒1形态'] in [Signals.LI0.value]:
    #         v = Factors.L3A0.value
    #
    # for freq in freqs:
    #     xt = [
    #         Signals.SA0.value, Signals.SB0.value, Signals.SC0.value,
    #         Signals.SD0.value, Signals.SE0.value, Signals.SF0.value
    #     ]
    #     if s[f'{freq}_倒1形态'] in xt:
    #         v = Factors.S1A0.value

    return v

# ======================================================================================================================
def future_third_buy_f5_base(s):
    """期货5分钟三买"""
    return third_buy_base(s, [Freq.F5.value], [Freq.F1.value])


future_third_buy_f5 = future_third_buy_f5_base
# ======================================================================================================================
def share_third_buy_f15_base(s):
    """股票15分钟三买E"""
    v = Factors.Other.value

    for f_ in [Freq.F30.value, Freq.F15.value]:
        if f_ not in s['级别列表']:
            warnings.warn(f"{f_} not in {s['级别列表']}，默认返回 Other")
            return v

    # 开多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    long_opens = {
        Factors.L3A0.value: [
            [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.D.value}_倒1形态#{Signals.LH0.value}"],
            [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.D.value}_倒2形态#{Signals.LH0.value}"],

            [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒5形态#{Signals.LA0.value}"],
            [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒4形态#{Signals.SH0.value}"],
            [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒6形态#{Signals.SI0.value}"],
        ]
    }
    for name, factors in long_opens.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name

    # 平多仓因子
    # ------------------------------------------------------------------------------------------------------------------
    long_exits = {
        Factors.S1A0.value: [
            [f"{Freq.F15.value}_倒1形态#{Signals.SA0.value}"],
        ]
    }
    for name, factors in long_exits.items():
        for factor in factors:
            if match_factor(s, factor):
                v = name
    return v


share_third_buy_f15 = share_third_buy_f15_base
# ======================================================================================================================

