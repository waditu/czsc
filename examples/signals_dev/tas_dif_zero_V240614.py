import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, Direction
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal


def tas_dif_zero_V240614(c: CZSC, **kwargs) -> OrderedDict:
    """DIFF 远离零轴后靠近零轴，形成买卖点

    参数模板："{freq}_DIF靠近零轴W{w}T{t}_BS辅助V240614"

    **信号逻辑：**

    买点的定位以DIF为主，要求如下。

    1，取最近 w 根K线，获取 diffs 序列
    2. 如果所有 diff 都大于 0，且最近一个 diff 在 0.5倍标准差范围内，且最大值大于均值加标准差，则认为是买点

    **信号列表：**

    - Signal('60分钟_DIF靠近零轴W20T50_BS辅助V240614_卖点_任意_任意_0')
    - Signal('60分钟_DIF靠近零轴W20T50_BS辅助V240614_买点_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无

        - t: DIF波动率的倍数，除以100，默认为50

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 20))  # K线数量
    t = int(kwargs.get("t", 50))  # 波动率的倍数，除以100

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_DIF靠近零轴W{w}T{t}_BS辅助V240614".split("_")
    v1 = "其他"
    key = update_macd_cache(c)
    if len(c.bars_raw) < 110:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = c.bars_raw[-w:]
    diffs = [x.cache[key]["dif"] for x in bars]
    delta = np.std(diffs) * t / 100
    max_diff = max(diffs)
    min_diff = min(diffs)
    abs_mean_diff = abs(np.mean(diffs))
    std_diff = np.std(diffs)

    if all(x > 0 for x in diffs) and delta > diffs[-1] > -delta and max_diff > abs_mean_diff + std_diff:
        v1 = "买点"

    if all(x < 0 for x in diffs) and -delta < diffs[-1] < delta and min_diff < -(abs_mean_diff + std_diff):
        v1 = "卖点"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": tas_dif_zero_V240614, "freq": "60分钟", "t": 50}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
