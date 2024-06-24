import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def cxt_overlap_V240612(c: CZSC, **kwargs) -> OrderedDict:
    """顺畅笔的顶底分型构建支撑压力位

    参数模板："{freq}_SNR顺畅N{n}_支撑压力V240612"

    **信号逻辑：**

    前面N笔中走势最顺畅的笔，顶底分型是重要支撑压力位，可以作为决策点。

    1. 取最近 N 笔，找出SNR最大的笔 B1；
    2. 如果当前笔是向下笔，且向下笔的底分型区间与B1的顶/底分型区间有重合，那么认为当前位置是支撑位；

    **信号列表：**

    - Signal('60分钟_SNR顺畅N9_支撑压力V240612_支撑_顺畅笔底分型_任意_0')
    - Signal('60分钟_SNR顺畅N9_支撑压力V240612_压力_顺畅笔底分型_任意_0')
    - Signal('60分钟_SNR顺畅N9_支撑压力V240612_支撑_顺畅笔顶分型_任意_0')
    - Signal('60分钟_SNR顺畅N9_支撑压力V240612_压力_顺畅笔顶分型_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 7))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_SNR顺畅N{n}_支撑压力V240612".split("_")
    v1 = "其他"
    if len(c.bi_list) < n + 2 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=3, n=n)
    bis = [x for x in bis if len(x.raw_bars) >= 9]
    if len(bis) == 0:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    max_snr_bi = max(bis, key=lambda x: x.SNR)
    if max_snr_bi.SNR < 0.7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if max_snr_bi.direction == Direction.Down:
        fxg = max_snr_bi.fx_a
        fxd = max_snr_bi.fx_b
    else:
        fxg = max_snr_bi.fx_b
        fxd = max_snr_bi.fx_a

    def is_price_overlap(h1, l1, h2, l2):
        """判断两个价格区间是否有重合"""
        return True if max(l1, l2) < min(h1, h2) else False

    last_bi = c.bi_list[-1]
    v2 = "任意"
    if last_bi.direction == Direction.Down:
        if is_price_overlap(fxg.high, fxg.low, last_bi.fx_b.high, last_bi.fx_b.low):
            v1 = "支撑"
            v2 = "顺畅笔顶分型"
        if is_price_overlap(fxd.high, fxd.low, last_bi.fx_b.high, last_bi.fx_b.low):
            v1 = "支撑"
            v2 = "顺畅笔底分型"

    if last_bi.direction == Direction.Up:
        if is_price_overlap(fxg.high, fxg.low, last_bi.fx_b.high, last_bi.fx_b.low):
            v1 = "压力"
            v2 = "顺畅笔顶分型"

        if is_price_overlap(fxd.high, fxd.low, last_bi.fx_b.high, last_bi.fx_b.low):
            v1 = "压力"
            v2 = "顺畅笔底分型"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_overlap_V240612, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
