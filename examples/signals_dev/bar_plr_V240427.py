import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def bar_plr_V240427(c: CZSC, **kwargs) -> OrderedDict:
    """盈亏比计算

    plr 是 Profit Loss Ratio 的缩写，即盈亏比。盈亏比是一个用于衡量投资者在投资活动中获得的盈利与损失之间的比率的指标。

    参数模板："{freq}_D{di}W{w}T{t}M{m}_盈亏比V240427"

    **信号逻辑：**

    以多头的阴亏比为例，计算过程如下：
    1. 找到最近的一个最低点，记为 L；
    2. 在最低点 L 之前的K线中，找到第一个最高点，记为 H；
    3. 计算 H 到 L 之间的盈亏比，记为 plr；

    **信号列表：**

    - Signal('60分钟_D1W60T20M多头_盈亏比V240427_不满足_任意_任意_0')
    - Signal('60分钟_D1W60T20M多头_盈亏比V240427_满足_任意_任意_0')
    - Signal('60分钟_D1W60T20M空头_盈亏比V240427_不满足_任意_任意_0')
    - Signal('60分钟_D1W60T20M空头_盈亏比V240427_满足_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: int, default 1, 周期偏移量
        - w: int, default 60, 计算盈亏比的K线数量
        - t: int, default 20, 盈亏比阈值，plr > t / 10 时满足信号条件
        - m: str, default "多头", 信号方向，"多头" 或 "空头"

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 60))
    t = int(kwargs.get("t", 20))
    m = str(kwargs.get("m", "多头"))

    assert m in ["多头", "空头"], "参数 m 必须是 多头 或 空头"
    assert di > 0, "参数 di 必须大于 0"
    assert w >= 10, "参数 w 必须大于等于 10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}T{t}M{m}_盈亏比V240427".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 7 + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=w)

    if m == "多头":
        low_bar = min(bars, key=lambda x: x.low)
        if bars.index(low_bar) == 0:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        high_bar = max(bars[: bars.index(low_bar)], key=lambda x: x.high)
        profit = high_bar.high - bars[-1].close
        loss = bars[-1].close - low_bar.low
        plr = profit / loss if loss > 0 else 0
        v1 = "满足" if plr > t / 10 else "不满足"

    if m == "空头":
        high_bar = max(bars, key=lambda x: x.high)
        if bars.index(high_bar) == 0:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        low_bar = min(bars[: bars.index(high_bar)], key=lambda x: x.low)
        profit = bars[-1].close - low_bar.low
        loss = high_bar.high - bars[-1].close
        plr = profit / loss if loss > 0 else 0
        v1 = "满足" if plr > t / 10 else "不满足"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_plr_V240427, "freq": "60分钟"},
        {"name": bar_plr_V240427, "freq": "60分钟", "m": "空头"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
