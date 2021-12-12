# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:43
"""
from collections import OrderedDict
from czsc import signals
from czsc.enum import Freq, Direction
from czsc.analyze import CZSC, Operate
from czsc.objects import Event, Factor, Signal


class TacticShareA:
    """A股交易策略A（股票、可转债、ETF）"""
    freqs = ['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线']

    def __init__(self):
        self.name = "TSA"

    @staticmethod
    def get_signals(c: CZSC) -> OrderedDict:
        """通用信号获取"""
        s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
        s.update(signals.get_s_bar_end(c))
        s.update(signals.get_s_k(c))
        s.update(signals.get_s_three_bi(c, di=1))
        s.update(signals.get_s_base_xt(c, di=1))
        s.update(signals.get_s_like_bs(c, di=1))
        s.update(signals.get_s_d0_bi(c))

        s.update(signals.get_s_macd(c, di=1))
        s.update(signals.get_s_sma(c, di=1, t_seq=(5, 10, 20, 60)))
        return s

    @staticmethod
    def like_bs_rt_v1():
        """股票5分钟策略的交易事件"""
        op_freq = Freq.F15

        freqs = ['1分钟', '5分钟', '15分钟', '30分钟', '60分钟']

        def get_signals(c: CZSC) -> OrderedDict:
            s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
            s.update(signals.get_s_like_bs(c, di=1))
            s.update(signals.get_s_bar_end(c))
            s.update(signals.get_s_d0_bi(c))
            if c.freq == Freq.F60:
                s.update(signals.get_s_macd(c, di=1))
            return s

        def get_events():
            events = [
                Event(name="开多", operate=Operate.LO, factors=[
                    Factor(name="5分钟三买", signals_all=[
                        Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0"),
                        Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),

                        Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                        Signal("60分钟_倒1K_DIF方向_向上_任意_任意_0"),
                    ]),
                    Factor(name="15分钟三买", signals_all=[
                        Signal("15分钟_倒1笔_类买卖点_类三买_任意_任意_0"),

                        Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                        Signal("60分钟_倒1K_DIF方向_向上_任意_任意_0"),
                    ]),
                    Factor(name="30分钟三买", signals_all=[
                        Signal("30分钟_倒1笔_类买卖点_类三买_任意_任意_0"),
                        Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),

                        Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                        Signal("60分钟_倒1K_DIF方向_向上_任意_任意_0"),
                    ]),
                ]),

                Event(name="平多", operate=Operate.LE, factors=[
                    Factor(name="5分钟一卖", signals_all=[
                        Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0"),
                        Signal("5分钟_倒1K_结束_是_任意_任意_0"),
                    ]),
                    Factor(name="15分钟一卖", signals_all=[
                        Signal("15分钟_倒1笔_类买卖点_类一卖_任意_任意_0"),
                        Signal("15分钟_倒1K_结束_是_任意_任意_0"),
                    ]),
                    Factor(name="30分钟一卖", signals_all=[
                        Signal("30分钟_倒1笔_类买卖点_类一卖_任意_任意_0"),
                        Signal("30分钟_倒1K_结束_是_任意_任意_0"),
                    ]),
                    Factor(name="5分钟二卖", signals_all=[
                        Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0"),
                        Signal("5分钟_倒1K_结束_是_任意_任意_0"),
                    ]),

                    Factor(name="60分钟DIF空头", signals_all=[
                        Signal("60分钟_倒1K_DIF多空_空头_任意_任意_0"),
                        Signal("60分钟_倒1K_结束_是_任意_任意_0"),
                    ]),
                ]),
            ]
            return events
        return op_freq, freqs, get_signals, get_events
