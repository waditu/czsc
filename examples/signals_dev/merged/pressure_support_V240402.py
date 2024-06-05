import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def pressure_support_V240402(c: CZSC, **kwargs) -> OrderedDict:
    """支撑压力线辅助V240402

    参数模板："{freq}_D{di}W{w}_支撑压力V240402"

    **信号逻辑：**

    对于给定K线，判断是否存在支撑压力线，判断逻辑如下：

    1. 当前收盘价 +- 0.5倍波动率范围内有5个以上的分型高低点
    2. 当前收盘价在最近20根K线的最高价附近，认为是压力位；反之，认为是支撑位

    **信号列表：**

    - Signal('60分钟_D1W60_支撑压力V240402_压力位_任意_任意_0')
    - Signal('60分钟_D1W60_支撑压力V240402_支撑位_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 60))
    assert w > 10, "参数 w 必须大于10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}_支撑压力V240402".split("_")
    v1 = "其他"
    if len(c.bars_raw) < w + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    fxs = c.fx_list[-50:]
    bars = get_sub_elements(c.bars_raw, di=di, n=w)
    gap = np.std([abs(x.high - x.low) for x in bars])
    max_high = max([x.high for x in bars])
    min_low = min([x.low for x in bars])

    # 当前收盘价 +- 0.5倍波动率范围内有5个以上的分型高低点
    near_fx = [fx for fx in fxs if fx.low <= bars[-1].close <= fx.high]
    if len(near_fx) < 5 or max_high - min_low < gap * 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    hl_gap = max_high - min_low
    if bars[-1].close > max_high - hl_gap * 0.2:
        v1 = "压力位"

    if bars[-1].close < min_low + hl_gap * 0.2:
        v1 = "支撑位"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": pressure_support_V240402, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
