import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def cxt_second_bs_V240524(c: CZSC, **kwargs) -> OrderedDict:
    """中枢视角下的并列二买

    参数模板："{freq}_D{di}W{w}T{t}_第二买卖点V240524"

    **信号逻辑：**

    1. 取最近 15 笔；
    2. 如果当前笔是向下笔，且向下笔的底分型区间与前面的15笔中存在 t 个以上的分型区间重合，则认为是并列二买；

    **信号列表：**

    - Signal('60分钟_D1W15T2_第二买卖点V240524_二买_任意_任意_0')
    - Signal('60分钟_D1W15T2_第二买卖点V240524_二卖_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 15))  # 中枢窗口
    t = int(kwargs.get("t", 2))  # 重合次数
    assert w > 5, "参数 w 必须大于5"
    assert t >= 2, "参数 t 必须大于等于2"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}T{t}_第二买卖点V240524".split("_")
    v1 = "其他"
    if len(c.bi_list) < w + di + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=w)
    last: BI = bis[-1]
    last_fx_high = last.fx_b.high
    last_fx_low = last.fx_b.low

    if last.direction.value == "向下" and last.length >= 7:
        zs_count = 0
        for bi in bis[:-1]:
            # bi 的结束分型区间与 last 的分型区间有重合
            if bi.length >= 7 and max(bi.fx_b.low, last_fx_low) < min(bi.fx_b.high, last_fx_high):
                zs_count += 1

        if zs_count >= t:
            v1 = "二买"

    if last.direction.value == "向上" and last.length >= 7:
        zs_count = 0
        for bi in bis[:-1]:
            # bi 的结束分型区间与 last 的分型区间有重合
            if bi.length >= 7 and max(bi.fx_b.low, last_fx_low) < min(bi.fx_b.high, last_fx_high):
                zs_count += 1

        if zs_count >= t:
            v1 = "二卖"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_second_bs_V240524, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
