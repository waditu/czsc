# -*- coding: utf-8 -*-
# @Time    : 2023/6/18 15:51
# @Author  : 琅盎
# @FileName: DEMA.py
# @Software: PyCharm
from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def dema_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """DEMA短线趋势指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_DEMA短线趋势V230605"

    **信号逻辑：**
    
    DEMA指标是一种趋势指标，用于衡量价格趋势的方向和强度。
    与其他移动平均线指标相比，DEMA指标更加灵敏，能够更快地反应价格趋势的变化，因此在短期交易中具有一定的优势。
    当收盘价大于DEMA看多， 当收盘价小于DEMA看空

    **信号列表：**

    - Signal('日线_D1N5_DEMA短线趋势V230605_看多_任意_任意_0')
    - Signal('日线_D1N5_DEMA短线趋势V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为5

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_DEMA短线趋势V230605".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + 2*n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    short_bars = get_sub_elements(c.bars_raw, di=di, n=n)
    long_bars = get_sub_elements(c.bars_raw, di=di, n=n * 2)
    dema = np.mean([x.close for x in short_bars]) * 2 - np.mean([x.close for x in long_bars])

    v1 = "看多" if short_bars[-1].close > dema else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': dema_up_dw_line_V230605, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config)


if __name__ == '__main__':
    main()