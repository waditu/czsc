# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: 验证信号计算的准确性，仅适用于缠论笔相关的信号，
          技术指标构建的信号，用这个工具检查不是那么方便
"""
import os
import sys
sys.path.insert(0, '..')
os.environ['czsc_verbose'] = '1'

from collections import OrderedDict
from czsc import CZSC
from czsc.utils import create_single_signal
from czsc.traders.base import check_signals_acc
from czsc.connectors import research


def bar_zdt_V230331(c: CZSC, **kwargs) -> OrderedDict:
    """计算倒数第di根K线的涨跌停信息

    参数模板："{freq}_D{di}_涨跌停V230331"

    **信号逻辑：**

    - close等于high大于等于前一根K线的close，近似认为是涨停；反之，跌停。

    **信号列表：**

    - Signal('15分钟_D1_涨跌停V230331_涨停_任意_任意_0')
    - Signal('15分钟_D1_涨跌停V230331_跌停_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs:
        - di: 倒数第 di 根 K 线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}_涨跌停V230331".split("_")
    v1 = "其他"
    if len(c.bars_raw) < di + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2 = c.bars_raw[-di], c.bars_raw[-di - 1]
    if b1.close == b1.high >= b2.close:
        v1 = "涨停"
    elif b1.close == b1.low <= b2.close:
        v1 = "跌停"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


symbols = research.get_symbols('A股主要指数')
bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

signals_config = [
    {'name': "czsc.signals.bar_end_V221111", 'freq': '15分钟', 'freq1': '30分钟'},
    # {'name': bar_zdt_V230331, 'freq': '60分钟'},
]

if __name__ == '__main__':
    check_signals_acc(bars, signals_config=signals_config)

    # 也可以指定信号的K线周期，比如只检查日线信号
    # check_signals_acc(bars, get_signals, freqs=['日线'])






