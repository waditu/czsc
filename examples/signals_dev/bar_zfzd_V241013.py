import numpy as np
from collections import OrderedDict

import pandas as pd

from czsc.analyze import CZSC
from czsc.utils import create_single_signal


def bar_zfzd_V241013(c: CZSC, **kwargs) -> OrderedDict:
    """窄幅震荡形态：窗口内任意两根K线都要有重叠

    参数模板："{freq}_窄幅震荡N{n}_形态V241013"

    **信号逻辑：**

    1. 取最近 n 根K线，这 n 根K线的 最高价最小值 >= 最低价最大值，即有重叠

    **信号列表：**

    - Signal('60分钟_窄幅震荡N5_形态V241013_满足_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 5))  # 窗口大小

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_窄幅震荡N{n}_形态V241013".split("_")
    v1 = "其他"

    if len(c.bars_raw) < n + 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = c.bars_raw[-n:]
    zg = min([x.high for x in bars])
    zd = max([x.low for x in bars])
    if zg >= zd:
        v1 = "满足"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": bar_zfzd_V241013, "freq": "60分钟", "n": 5}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
