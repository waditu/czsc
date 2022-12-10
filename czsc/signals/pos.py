# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/4/13 15:03
describe: 持仓相关信号
"""
from collections import OrderedDict
from czsc.objects import Operate, Signal, PositionLong
from czsc.traders.advanced import CzscAdvancedTrader


def get_s_long01(cat: CzscAdvancedTrader, th=300):
    """多头持仓信号：亏损"""
    pos = cat.long_pos
    k1, k2, k3 = '多头', '亏损', f'超{th}BP'
    s = OrderedDict()
    v1 = '否'
    if pos.pos > 0:
        latest_price = cat.latest_price
        last_o = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]
        last_o_price = last_o['price']
        yk = (latest_price - last_o_price) / last_o_price
        if yk * 10000 < -th:
            v1 = '是'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def get_s_long02(cat: CzscAdvancedTrader, th=300):
    """多头持仓信号：回撤"""
    pos = cat.long_pos
    k1, k2, k3 = '多头', '回撤', f'超{th}BP'
    s = OrderedDict()
    v1 = '否'
    if pos.pos > 0 and cat.latest_price <= pos.long_high:
        hc = abs(cat.latest_price / pos.long_high - 1)
        if hc * 10000 > th:
            v1 = '是'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def get_s_long03(cat: CzscAdvancedTrader, th=100):
    """多头持仓信号：持仓时间"""
    pos = cat.long_pos
    k1, k2, k3 = '多头', '持仓时间', f'超{th}根基础K线'
    s = OrderedDict()
    v1 = '否'
    if pos.pos > 0:
        lo_bid = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]['bid']
        bid = cat.bg.bars[cat.base_freq][-1].id
        if bid - lo_bid > th:
            v1 = '是'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def get_s_long04(cat: CzscAdvancedTrader, th=5):
    """多头持仓信号：持仓亏损时间"""
    pos = cat.long_pos
    k1, k2, k3 = '多头', '持仓亏损时间', f'超{th}根基础K线'
    s = OrderedDict()
    v1 = '否'
    if pos.pos > 0:
        lo = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]
        hold_bars = [x for x in cat.kas[cat.base_freq].bars_raw[-(th+50):] if x.id >= lo['bid']]
        loss_bars = [1 if x.close < lo['price'] else 0 for x in hold_bars]
        if sum(loss_bars) > th:
            v1 = '是'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def get_s_long05(cat: CzscAdvancedTrader, span="月", th=500):
    """多头持仓信号：周期累计亏损"""
    pos: PositionLong = cat.long_pos
    k1, k2, k3 = '多头', f'本{span}累计亏损', f'超{th}BP'
    s = OrderedDict()

    if span == '周':
        dt_fmt = '%Y年%W周'
    elif span == '月':
        dt_fmt = '%Y年%m月'
    else:
        raise ValueError
    dt_ = cat.end_dt.strftime(dt_fmt)
    pairs = [x for x in pos.pairs if x['平仓时间'].strftime(dt_fmt) == dt_]

    v1 = '否'
    if sum([x['盈亏比例'] for x in pairs]) < -th / 10000:
        v1 = '是'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def get_s_long06(cat: CzscAdvancedTrader, th=500):
    """多头持仓信号：最大盈亏

    在多头持仓期间的最低价与成本价之间的盈亏计算；主要用于买入后盈亏到一定程度，启动保护措施
    """
    pos = cat.long_pos
    k1, k2, k3 = '多头', '最大盈亏', f'超{th}BP'
    s = OrderedDict()
    v1 = v2 = '其他'

    if pos.pos > 0:
        lo = [x for x in pos.operates[-50:] if x['op'] == Operate.LO][-1]
        buy_price = lo['price']
        hold_bars = [x for x in cat.kas[cat.base_freq].bars_raw[-100:] if x.id >= lo['bid']]
        min_price = min([x.low for x in hold_bars])
        max_price = max([x.high for x in hold_bars])
        cur_price = hold_bars[-1].close

        if cur_price > buy_price * 1.01:
            v1 = "是" if (max_price / buy_price - 1) * 10000 > th else "否"
            v2 = "盈利"
        else:
            v1 = '是' if (min_price / buy_price - 1) * 10000 < -th else "否"
            v2 = "亏损"

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s

