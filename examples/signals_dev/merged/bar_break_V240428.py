import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def bar_break_V240428(c: CZSC, **kwargs) -> OrderedDict:
    """极值突破

    参考资料：
    1. [后浪“拍死”前浪的日内波动极值策略](https://zhuanlan.zhihu.com/p/390025811)
    2. 罗军，广发证券，2011，《基于日内波动极值的股指期货趋势跟随系统》

    参数模板："{freq}_D{di}W{w}_事件V240428"

    **信号逻辑：**

    以60分钟级别为例，计算过程如下：
    1. 获取w根K线的最高价和最低价，分别记为H和L；
    2. 当前K线的收盘价，记为C；大于H时，触发收盘新高信号；小于L时，触发收盘新低信号。

    **信号列表：**

    - Signal('60分钟_D1W20_事件V240428_收盘新低_任意_任意_0')
    - Signal('60分钟_D1W20_事件V240428_收盘新高_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: int, default 1, 周期偏移量
        - w: int, default 60, 计算多项式拟合的K线数量

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 20))

    assert di > 0, "参数 di 必须大于 0"
    assert w >= 10, "参数 w 必须大于等于 10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}_事件V240428".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 7 + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=w)

    if bars[-1].close > max([x.high for x in bars[:-1]]):
        v1 = "收盘新高"
    elif bars[-1].close < min([x.low for x in bars[:-1]]):
        v1 = "收盘新低"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_break_V240428, "freq": "60分钟"},
        # {"name": bar_plr_V240427, "freq": "60分钟", "m": "空头"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
