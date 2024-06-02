import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def pressure_support_V240222(c: CZSC, **kwargs) -> OrderedDict:
    """支撑压力线辅助V240222

    参数模板："{freq}_D{di}W{w}高低点验证_支撑压力V240222"

    **信号逻辑：**

    给定窗口内，当前价格与前高前低的关系，判断当前价格的压力和支撑。以高点验证压力位为例：

    1. 当前高点与前高的差值在 x 个标准差以内
    2. 当前高点与前高分别在窗口的两端
    3. 中间的最低价与高点的差值在 y 个标准差以外

    **信号列表：**

    - Signal('60分钟_D1W20高低点验证_支撑压力V240222_支撑位_任意_任意_0')
    - Signal('60分钟_D1W20高低点验证_支撑压力V240222_压力位_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 20))
    assert w > 10, "参数 w 必须大于10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}高低点验证_支撑压力V240222".split("_")
    v1 = "其他"
    if len(c.bars_raw) < w + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=w)
    max_high = max([x.high for x in bars])
    min_low = min([x.low for x in bars])

    n = int(len(bars) * 0.2)
    left_bars = bars[:n]
    right_bars = bars[-n:]
    gap = np.std([abs(x.high - x.low) for x in bars])

    if max_high - min_low < gap * 0.3 * w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    left_high = max([x.high for x in left_bars])
    right_high = max([x.high for x in right_bars])
    if max_high == max(left_high, right_high) and max_high - min(left_high, right_high) < gap:
        v1 = "压力位"

    left_low = min([x.low for x in left_bars])
    right_low = min([x.low for x in right_bars])
    if min_low == min(left_low, right_low) and max(left_low, right_low) - min_low < gap:
        v1 = "支撑位"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": pressure_support_V240222, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
