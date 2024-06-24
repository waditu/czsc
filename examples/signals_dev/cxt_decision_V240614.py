import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger


def cxt_decision_V240614(c: CZSC, **kwargs) -> OrderedDict:
    """取最近N笔，如果当前笔向下创出新低，且累计成交量最大，开多；如果当前笔向上创出新高，且累计成交量最大，开空

    参数模板："{freq}_放量笔N{n}_决策区域V240614"

    **信号逻辑：**

    取最近N笔，如果当前笔向下创出新低，且累计成交量最大，开多；如果当前笔向上创出新高，且累计成交量最大，开空

    **信号列表：**

    - Signal('15分钟_放量笔N4_决策区域V240614_开多_任意_任意_0')
    - Signal('15分钟_放量笔N4_决策区域V240614_开空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 4))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_放量笔N{n}_决策区域V240614".split("_")
    v1 = "其他"
    if len(c.bi_list) < n + 2 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=1, n=n)
    bis_vol = [x.power_volume for x in bis]
    if bis[-1].power_volume != max(bis_vol):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bis[-1].direction == Direction.Down and bis[-1].low != min([x.low for x in bis]):
        v1 = "开多"

    if bis[-1].direction == Direction.Up and bis[-1].high != max([x.high for x in bis]):
        v1 = "开空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_decision_V240614, "freq": "15分钟", "n": 4}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
