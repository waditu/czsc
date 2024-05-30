import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def pressure_support_V240530(c: CZSC, **kwargs) -> OrderedDict:
    """支撑压力线辅助V240530

    参数模板："{freq}_D{di}W{w}N{n}_支撑压力V240530"

    **信号逻辑：**

    对于给定K线，判断是否存在支撑压力线，判断逻辑如下：

    1. 寻找关键K线的高低点，关键K线为最近w根K线中与其他K线重叠次数最多的K线
    2. 当前K线收盘价在关键K线最高价的正负5个价位左右，认为是压力位；反之，认为是支撑位

    **信号列表：**

    - Signal('60分钟_D1W20N5_支撑压力V240530_支撑位_任意_任意_0')
    - Signal('60分钟_D1W20N5_支撑压力V240530_压力位_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 20))
    n = int(kwargs.get("n", 5))
    assert w > 10, "参数 w 必须大于10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}N{n}_支撑压力V240530".split("_")
    v1 = "其他"
    if len(c.bars_raw) < w + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=w)

    # 获取关键K线的高低点
    bar_overlap_count = {}
    for i in range(len(bars)):
        bar = bars[i]
        overlap_count = 0
        for j in range(len(bars)):
            if i == j:
                continue
            bar2 = bars[j]
            # 判断两根K线是否重叠
            if max(bar.low, bar2.low) < min(bar.high, bar2.high):
                overlap_count += 1
        bar_overlap_count[i] = overlap_count

    # 如果最大重叠次数小于总数的一半，认为没有关键K线
    if max(bar_overlap_count.values()) < 0.5 * w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    key_bar = bars[max(bar_overlap_count, key=bar_overlap_count.get)]
    # 获取窗口内的 unique price 列表
    prices = [y for x in c.bars_raw for y in [x.open, x.close, x.high, x.low]]
    prices = sorted(list(set(prices)))
    high_idx = prices.index(key_bar.high)
    low_idx = prices.index(key_bar.low)
    # 处理边界情况
    if high_idx < n or low_idx < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if high_idx + n >= len(prices) or low_idx + n >= len(prices):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 判断压力位：当前收盘价在关键K线最高价的正负5个价位左右
    pressure_h = prices[high_idx + n]
    pressure_l = prices[high_idx - n]

    if pressure_h > bars[-1].close > pressure_l:
        v1 = "压力位"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 判断支撑位：当前收盘价在关键K线最低价的正负5个价位左右
    support_h = prices[low_idx + n]
    support_l = prices[low_idx - n]
    if support_h > bars[-1].close > support_l:
        v1 = "支撑位"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": pressure_support_V240530, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
