# coding: utf-8
from collections import OrderedDict
from czsc import signals
from czsc.analyze import CZSC, Operate
from czsc.objects import Event, Factor, Signal


# ======================================================================================================================
# 股票策略编写案例

freqs_share_f15_v1 = ('1分钟', '5分钟', '15分钟',)

def get_signals_share_f15_v1(c: CZSC) -> OrderedDict:
    """在 CZSC 对象上计算实盘交易过程需要用到的信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    s.update(signals.get_s_like_bs(c, 1))
    return s


def get_events_share_f15_v1():
    """股票15分钟策略的交易事件"""
    events = [
        # 开多
        Event(name="三买", operate=Operate.LO, factors=[
            Factor(name="15分钟三买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
        ]),

        # 平多
        Event(name="一卖", operate=Operate.LE, factors=[
            Factor(name="15分钟一卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟一卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
        ]),
        Event(name="二卖", operate=Operate.LE, factors=[
            Factor(name="15分钟二卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
        ]),
        Event(name="三卖", operate=Operate.LE, factors=[
            Factor(name="15分钟三卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
        ]),
    ]
    return events


