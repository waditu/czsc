import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from collections import OrderedDict
import pandas as pd
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def bar_window_ps_V230731(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内支撑压力位分位数计算，贡献者：chenlei

    参数模板："{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731"

    **信号逻辑：**

    1. 计算最近 N 笔的最高价 NH 和最低价 NL，这个可以近似理解成价格的支撑和压力位
    2. 计算并缓存最新K线的收盘价格 C 处于 NH、NL 之间的位置，计算方法为 P = （C - NL）/ (NH - NL)
    3. 取最近 M 个 P 值序列，按分位数分层，分层数量为 L，分层的最大值为最近的压力，最小值为最近的支撑，当前值为最近的价格位置

    **信号列表：**

    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N5_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N4_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N4_当前N4_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N3_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N2_当前N2_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N1_当前N2_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param w: 评价分位数分布用的窗口大小
        - :param m: 计算分位数所需取K线的数量。
        - :param n: 最近N笔
        - :param l: 分层的数量。

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 5))
    m = int(kwargs.get("m", 40))
    n = int(kwargs.get("n", 8))
    l = int(kwargs.get("l", 5))

    assert m > l * 2 > 2, "参数 m 必须大于 l * 2，且 l 必须大于 2"
    assert w < m, "参数 w 必须小于 m"    
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731".split('_')

    if len(c.bi_list) <  n+2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    # 更新支撑压力位位置
    cache_key_pct = "pct"
    H_line, L_line = max([x.high for x in c.bi_list[-n:]]), min([x.low for x in c.bi_list[-n:]])
    for i, bar in enumerate(c.bars_raw):
        if cache_key_pct in bar.cache:
            continue  
        bar.cache[cache_key_pct] = (bar.close - L_line) / (H_line - L_line)

    fenweis = [x.cache[cache_key_pct] for x in get_sub_elements(c.bars_raw, n=m)]
    layer = pd.qcut(fenweis, l, labels=False, duplicates='drop')
    max_layer = max(layer[-w:]) + 1
    min_layer = min(layer[-w:]) + 1

    v1, v2, v3 = f"压力N{max_layer}", f"支撑N{min_layer}", f"当前N{layer[-1]+1}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': bar_window_ps_V230731, 'freq': '15分钟'},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore

if __name__ == '__main__':
    main()
