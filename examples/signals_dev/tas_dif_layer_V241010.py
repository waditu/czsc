import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, Direction
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal


def tas_dif_layer_V241010(c: CZSC, **kwargs) -> OrderedDict:
    """DIF分三层：零轴附近，上方远离，下方远离

    参数模板："{freq}_DIF分层W{w}T{t}_完全分类V241010"

    **信号逻辑：**

    DIF分层，要求如下。

    1，取最近 w 根K线，获取 diffs 序列
    2. 计算 diffs 的最大绝对值 r，作为波动率的标准
    3. 如果最近一个 diff 在 t * r 的范围内，则认为是零轴附近
    4. 如果最近一个 diff > 0 且在 t * r 的范围外，则认为是多头远离；反之，空头远离

    **信号列表：**

    - Signal('60分钟_DIF分层W100T50_完全分类V241010_零轴附近_任意_任意_0')
    - Signal('60分钟_DIF分层W100T50_完全分类V241010_空头远离_任意_任意_0')
    - Signal('60分钟_DIF分层W100T50_完全分类V241010_多头远离_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 100))  # K线数量
    t = int(kwargs.get("t", 30))  # 零轴附近的阈值，相比与 max(diffs) 的比例

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_DIF分层W{w}T{t}_完全分类V241010".split("_")
    v1 = "其他"
    key = update_macd_cache(c)
    if len(c.bars_raw) < w + 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = c.bars_raw[-w:]
    diffs = [x.cache[key]["dif"] for x in bars]

    r = max([abs(x) for x in diffs]) / 100
    if diffs[-1] < 0 and abs(diffs[-1]) > r * t:
        v1 = "空头远离"
    elif diffs[-1] > 0 and abs(diffs[-1]) > r * t:
        v1 = "多头远离"
    else:
        v1 = "零轴附近"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": tas_dif_layer_V241010, "freq": "60分钟", "t": 30}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
