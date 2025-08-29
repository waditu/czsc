import numpy as np
from collections import OrderedDict

import pandas as pd

from czsc.analyze import CZSC
from czsc.utils import create_single_signal


def bar_volatility_V241013(c: CZSC, **kwargs) -> OrderedDict:
    """波动率分三层

    参数模板："{freq}_波动率分层W{w}N{n}_完全分类V241013"

    **信号逻辑：**

    波动率分层，要求如下。
    1. 取最近 n 根K线，计算这 n 根K线的最高价和最低价的差值，记为 r
    2. 取最近 w 根K线，将 r 分为三等分，分别为低波动，中波动，高波动

    **信号列表：**

    - Signal('60分钟_波动率分层W200N10_完全分类V241013_低波动_任意_任意_0')
    - Signal('60分钟_波动率分层W200N10_完全分类V241013_中波动_任意_任意_0')
    - Signal('60分钟_波动率分层W200N10_完全分类V241013_高波动_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 200))  # K线数量
    n = int(kwargs.get("n", 10))  # 波动率窗口大小

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_波动率分层W{w}N{n}_完全分类V241013".split("_")
    v1 = "其他"
    key = f"volatility_{n}"
    for bar in c.bars_raw[-n:]:
        if key not in bar.cache:
            n_max_close = max([x.close for x in c.bars_raw[-n:]])
            n_min_close = min([x.close for x in c.bars_raw[-n:]])
            bar.cache[key] = n_max_close - n_min_close

    if len(c.bars_raw) < w + n + 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    vols = [x.cache.get(key, 0) for x in c.bars_raw[-w:]]
    try:
        v1 = pd.qcut(vols, 3, labels=["低波动", "中波动", "高波动"], duplicates="drop")[-1]
    except Exception as e:
        v1 = "其他"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": bar_volatility_V241013, "freq": "60分钟", "n": 10}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
