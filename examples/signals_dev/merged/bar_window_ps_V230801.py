import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from collections import OrderedDict
import pandas as pd
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def bar_window_ps_V230801(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内支撑压力位分位数计算

    参数模板："{freq}_N{n}W{w}_支撑压力位V230801"

    **信号逻辑：**

    1. 计算最近 N 笔的最高价 NH 和最低价 NL，这个可以近似理解成价格的支撑和压力位
    2. 计算并缓存最新K线的收盘价格 C 处于 NH、NL 之间的位置，计算方法为 P = （C - NL）/ (NH - NL)
    3. 取最近 M 个 P 值序列，四舍五入精确到小数点后1位，作为当前K线的分位数

    **信号列表：**

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param w: 评价分位数分布用的窗口大小
        - :param n: 最近N笔

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 5))
    n = int(kwargs.get("n", 8))

    if len(c.bi_list) < n+2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    ubi = c.ubi
    H_line, L_line = max([x.high for x in c.bi_list[-n:]] + [ubi['high']]), min([x.low for x in c.bi_list[-n:]] + [ubi['low']])
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}W{w}_支撑压力位V230801".split('_')
    bars = c.bars_raw[-w:]
    pcts = [int(max((x.close - L_line) / (H_line - L_line), 0) * 10) for x in bars]
    v1, v2, v3 = f"最大N{max(pcts)}", f"最小N{min(pcts)}", f"当前N{pcts[-1]}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': bar_window_ps_V230801, 'freq': '15分钟'},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore

if __name__ == '__main__':
    main()
