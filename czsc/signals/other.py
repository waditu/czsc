# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/7 19:05
"""
from datetime import datetime
from collections import OrderedDict
from czsc import CZSC, Signal
from deprecated import deprecated


@deprecated(reason="请使用 czsc.signals.bar.bar_end_V221111 替代", version='1.0.0')
def get_s_raw_bar_end(c: CZSC, k1='60分钟') -> OrderedDict:
    """原始分钟K线结束，c 必须是基础周期的 CZSC 对象"""
    s = OrderedDict()
    k2, k3 = "K线", "结束"
    assert "分钟" in k1

    m = int(k1.replace("分钟", ""))
    dt: datetime = c.bars_raw[-1].dt
    if dt.minute % m == 0:
        v = "是"
    else:
        v = "否"

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v)
    s[signal.key] = signal.value
    return s


@deprecated(reason="请使用 czsc.signals.bar.bar_operate_span_V221111 替代", version='1.0.0')
def get_s_op_time_span(c: CZSC, op: str = '开多', time_span=("14:00", "14:50")) -> OrderedDict:
    """日内操作时间区间，c 必须是基础周期的 CZSC 对象"""
    s = OrderedDict()
    dt: datetime = c.bars_raw[-1].dt
    k1 = f"{op}时间范围"
    assert len(time_span) == 2
    k2, k3 = time_span

    if k2 <= dt.strftime("%H:%M") <= k3:
        v = "是"
    else:
        v = "否"

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v)
    s[signal.key] = signal.value
    return s


@deprecated(reason="请使用 czsc.signals.bar.bar_operate_span_V221111 替代", version='1.0.0')
def get_s_zdt(c: CZSC, di=1) -> OrderedDict:
    """计算倒数第di根K线的涨跌停信息

    任何K线，只要收盘价是最高价，那就不能买，只要收盘价是最低价，就不能卖，
    这是用来规避回测中的一些问题的辅助函数。
    """
    s = OrderedDict()
    k1 = str(c.freq.value)
    k2 = f"倒{di}K"
    k3 = "ZDT"
    if len(c.bars_raw) < di + 2:
        v1 = "非涨跌停"
    else:
        bar = c.bars_raw[-di]
        if bar.close == bar.high:
            v1 = "涨停"
        elif bar.close == bar.low:
            v1 = "跌停"
        else:
            v1 = "非涨跌停"

    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s
