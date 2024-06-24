import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger


def cxt_decision_V240612(c: CZSC, **kwargs) -> OrderedDict:
    """以最近W根K线的高低点附近N个价位作为决策区域

    参数模板："{freq}_W{w}N{n}高低点_决策区域V240612"

    **信号逻辑：**

    1. 取最近W根K线的高点和低点，分别找出第N个价位，作为决策区域的上下界；
    2. 当前K线的最高价超过决策区域的上界，开空；
    3. 当前K线的最低价低于决策区域的下界，开多；

    **信号列表：**

    - Signal('15分钟_W10N5高低点_决策区域V240612_开多_任意_任意_0')
    - Signal('15分钟_W10N5高低点_决策区域V240612_开空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 10))
    n = int(kwargs.get("n", 9))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_W{w}N{n}高低点_决策区域V240612".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 120:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=100)
    prices = [x.close for x in bars] + [x.high for x in bars] + [x.low for x in bars] + [x.open for x in bars]
    prices = list(set(prices))

    w_bars = get_sub_elements(c.bars_raw, di=1, n=w)

    max_high = max([x.high for x in w_bars])
    min_low = min([x.low for x in w_bars])
    last_bar = c.bars_raw[-1]

    # 低点上方的第N个价位
    min_low_upper = sorted([x for x in prices if x >= min_low])
    low_range = min_low_upper[n] if len(min_low_upper) > n else min_low_upper[-1]

    # 高点下方的第N个价位
    max_high_lower = sorted([x for x in prices if x <= max_high], reverse=True)
    high_range = max_high_lower[n] if len(max_high_lower) > n else max_high_lower[-1]

    if last_bar.close < low_range and last_bar.low != min_low:
        v1 = "开多"

    if last_bar.close > high_range and last_bar.high != max_high:
        v1 = "开空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_decision_V240612, "freq": "15分钟", "n": 5}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
