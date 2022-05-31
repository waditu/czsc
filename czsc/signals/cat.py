# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/4/4 22:43
describe: 以 CzscAdvancedTrader 作为输入的信号计算
"""
from typing import List, Union
from collections import OrderedDict
from czsc.objects import Freq, Operate, Direction, BI, FakeBI, Signal, PositionLong, PositionShort
from czsc.traders.advanced import CzscAdvancedTrader


def get_s_position(cat: CzscAdvancedTrader, pos: [PositionLong, PositionShort]):
    """计算持仓信号

    :return:
    """
    if isinstance(pos, PositionLong):
        k1 = "多头"
    elif isinstance(pos, PositionShort):
        k1 = "空头"
    else:
        raise ValueError

    s = OrderedDict()
    default_signals = [
        Signal(k1=k1, k2="最大", k3='盈利', v1="其他", v2="其他", v3="其他"),
        Signal(k1=k1, k2="最大", k3='回撤', v1="其他", v2="其他", v3="其他"),
        Signal(k1=k1, k2="最大", k3='回撤盈利比', v1="其他", v2="其他", v3="其他"),

        Signal(k1=k1, k2="累计", k3='盈亏', v1="其他", v2="其他", v3="其他"),
        Signal(k1=k1, k2="持仓", k3='时间', v1="其他", v2="其他", v3="其他"),
        Signal(k1=k1, k2="持仓", k3='基础K线数量', v1="其他", v2="其他", v3="其他"),
    ]
    for signal_ in default_signals:
        s[signal_.key] = signal_.value

    if pos.pos == 0:
        return s

    base_freq = cat.base_freq
    latest_price = cat.latest_price
    bid = cat.bg.bars[base_freq][-1].id
    end_dt = cat.bg.bars[base_freq][-1].dt

    if isinstance(pos, PositionLong):
        last_o = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]
        last_o_price = last_o['price']
        yl = pos.long_high / last_o_price - 1                   # 最大盈利
        hc = abs(latest_price / pos.long_high - 1)              # 最大回撤
        yk = (latest_price - last_o_price) / last_o_price       # 累计盈亏
    else:
        last_o = [x for x in pos.operates[-50:] if x['op'] == Operate.SO][-1]
        last_o_price = last_o['price']
        yl = last_o_price / pos.short_low - 1                   # 最大盈利
        hc = abs(pos.short_low / latest_price - 1)              # 最大回撤
        yk = (last_o_price - latest_price) / last_o_price       # 累计盈亏

    last_o_dt = last_o['dt']
    last_o_bid = last_o['bid']

    hc_yl_rate = hc / (yl + 0.000001)                   # 最大回撤盈利比
    hold_time = (end_dt - last_o_dt).total_seconds()   # 持仓时间，单位：秒
    hold_nbar = bid - last_o_bid                       # 持仓基础K线数量
    assert yl >= 0 and hc >= 0 and hc_yl_rate >= 0

    # ----------------------------------------------------------------------------------
    if yl > 0.15:
        v1 = "超过1500BP"
    elif yl > 0.1:
        v1 = "超过1000BP"
    elif yl > 0.08:
        v1 = "超过800BP"
    elif yl > 0.05:
        v1 = "超过500BP"
    elif yl > 0.03:
        v1 = "超过300BP"
    else:
        v1 = "低于300BP"
    v = Signal(k1=k1, k2="最大", k3='盈利', v1=v1)
    s[v.key] = v.value

    # ----------------------------------------------------------------------------------
    if hc > 0.15:
        v1 = "超过1500BP"
    elif hc > 0.1:
        v1 = "超过1000BP"
    elif hc > 0.08:
        v1 = "超过800BP"
    elif hc > 0.05:
        v1 = "超过500BP"
    elif hc > 0.03:
        v1 = "超过300BP"
    else:
        v1 = "低于300BP"
    v = Signal(k1=k1, k2="最大", k3='回撤', v1=v1)
    s[v.key] = v.value

    # ----------------------------------------------------------------------------------
    if hc_yl_rate > 0.8:
        v1 = "大于08"
    elif hc_yl_rate > 0.6:
        v1 = "大于06"
    elif hc_yl_rate > 0.5:
        v1 = "大于05"
    elif hc_yl_rate > 0.3:
        v1 = "大于03"
    else:
        v1 = "小于03"
    v = Signal(k1=k1, k2="最大", k3='回撤盈利比', v1=v1)
    s[v.key] = v.value

    # ----------------------------------------------------------------------------------
    if yk >= 0:
        v1 = "盈利"
    else:
        v1 = "亏损"

    if abs(yk) > 0.15:
        v2 = "超过1500BP"
    elif abs(yk) > 0.1:
        v2 = "超过1000BP"
    elif abs(yk) > 0.08:
        v2 = "超过800BP"
    elif abs(yk) > 0.05:
        v2 = "超过500BP"
    elif abs(yk) > 0.03:
        v2 = "超过300BP"
    else:
        v2 = "低于300BP"
    v = Signal(k1=k1, k2="累计", k3='盈亏', v1=v1, v2=v2)
    s[v.key] = v.value

    # ----------------------------------------------------------------------------------
    if hold_time > 3600 * 24 * 13:
        v1 = "超过13天"
    elif hold_time > 3600 * 24 * 8:
        v1 = "超过8天"
    elif hold_time > 3600 * 24 * 5:
        v1 = "超过5天"
    elif hold_time > 3600 * 24 * 3:
        v1 = "超过3天"
    else:
        v1 = "低于3天"
    v = Signal(k1=k1, k2="持仓", k3='时间', v1=v1)
    s[v.key] = v.value

    # ----------------------------------------------------------------------------------
    if hold_nbar > 300:
        v1 = "超过300根"
    elif hold_nbar > 200:
        v1 = "超过200根"
    elif hold_nbar > 150:
        v1 = "超过150根"
    elif hold_nbar > 100:
        v1 = "超过100根"
    elif hold_nbar > 50:
        v1 = "超过50根"
    else:
        v1 = "低于50根"
    v = Signal(k1=k1, k2="持仓", k3='基础K线数量', v1=v1)
    s[v.key] = v.value

    return s



