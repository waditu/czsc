# -*- coding: utf-8 -*-
# @Time    : 2023/6/18 16:11
# @Author  : 琅盎
# @FileName: BIAS_V1.py
# @Software: PyCharm
from collections import OrderedDict
import numpy as np
from datetime import datetime
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal, freq_end_time


def bar_end_V221211(c: CZSC, freq1='60分钟', **kwargs) -> OrderedDict:
    """判断分钟 K 线是否结束

    参数模板："{freq}_{freq1}结束_BS辅助221211"

    **信号逻辑：**

    以 freq 为基础周期，freq1 为大周期，判断 freq1 K线是否结束。
    如果结束，返回信号值为 "闭合"，否则返回 "未闭x"，x 为未闭合的次数。

    **信号列表：**

    - Signal('15分钟_60分钟结束_BS辅助221211_未闭1_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_未闭2_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_未闭3_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_闭合_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param freq1: 分钟周期名称
    :return: s
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{freq1}结束_BS辅助221211".split('_')
    assert "分钟" in freq1

    c1_dt = freq_end_time(c.bars_raw[-1].dt, freq1)
    i = 0
    for bar in c.bars_raw[::-1]:
        _edt = freq_end_time(bar.dt, freq1)
        if _edt != c1_dt:
            break
        i += 1

    if c1_dt == c.bars_raw[-1].dt:
        v = "闭合"
    else:
        v = "未闭{}".format(i)
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': bar_end_V221211, 'freq': '15分钟', 'freq1': '60分钟', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config, delta_days=0)

if __name__ == '__main__':
    main()