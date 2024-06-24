from collections import OrderedDict

import numpy as np

from copy import deepcopy
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def bar_td9_V240616(c: CZSC, **kwargs) -> OrderedDict:
    """神奇九转计数

    参数模板："{freq}_神奇九转N{n}_BS辅助V240616"

    **信号逻辑：**

    1. 当前收盘价大于前4根K线的收盘价，+1，否则-1
    2. 如果最后一根K线为1，且连续值计数大于等于N，卖点；如果最后一根K线为-1，且连续值计数小于等于-N，买点

    **信号列表：**

    - Signal('60分钟_神奇九转N9_BS辅助V240616_买点_9转_任意_0')
    - Signal('60分钟_神奇九转N9_BS辅助V240616_卖点_9转_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - n: int, default 9, 连续转折次数

    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 9))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_神奇九转N{n}_BS辅助V240616".split("_")
    v1 = "其他"

    # 更新缓存
    cache_key = "bar_td9_V240616"
    for i, bar in enumerate(c.bars_raw):
        if i < 4 or hasattr(bar.cache, cache_key):
            continue

        if bar.close > c.bars_raw[i - 4].close:
            bar.cache[cache_key] = 1
        elif bar.close < c.bars_raw[i - 4].close:
            bar.cache[cache_key] = -1
        else:
            bar.cache[cache_key] = 0

    if len(c.bars_raw) < 30 + n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    v2 = "任意"
    bars = get_sub_elements(c.bars_raw, di=1, n=n * 2)
    if bars[-1].cache[cache_key] == 1:
        count = 0
        for bar in bars[::-1]:
            if bar.cache[cache_key] != 1:
                break
            count += 1
        if count >= n:
            v1 = "卖点"
            v2 = f"{count}转"

    elif bars[-1].cache[cache_key] == -1:
        count = 0
        for bar in bars[::-1]:
            if bar.cache[cache_key] != -1:
                break
            count += 1
        if count >= n:
            v1 = "买点"
            v2 = f"{count}转"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_td9_V240616, "freq": "60分钟"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
