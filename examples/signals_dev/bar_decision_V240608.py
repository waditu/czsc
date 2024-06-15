from collections import OrderedDict

import numpy as np

from copy import deepcopy
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def bar_decision_V240608(c: CZSC, **kwargs) -> OrderedDict:
    """W窗口内最近N根K线放量后进行决策，如果是多头放量，开空，如果是空头放量，开多

    参数模板："{freq}_W{w}N{n}Q{q}放量_决策区域V240608"

    **信号逻辑：**

    1. 看多：第二根K线收盘价在第一根K线的最高价上方
    2. 看空：第二根K线收盘价在第一根K线的最低价下方
    3. 中性：其他情况

    **信号列表：**

    - Signal('60分钟_W300N20Q70放量_决策区域V240608_看空_任意_任意_0')
    - Signal('60分钟_W300N20Q70放量_决策区域V240608_放量_任意_任意_0')
    - Signal('60分钟_W300N20Q70放量_决策区域V240608_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - w: int, default 300, 窗口大小
        - n: int, default 20, 最近N根K线
        - q: int, default 80, 分位数，取值范围 0-100，表示取最近 w 根K线的成交量的 q 分位数

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 300))
    n = int(kwargs.get("n", 10))
    q = int(kwargs.get("q", 80))  # 分位数，取值范围 0-100，表示取最近 w 根K线的成交量的 q 分位数
    assert w > n > 3, "参数 w 必须大于 n，且 n 必须大于 0"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_W{w}N{n}Q{q}放量_决策区域V240608".split("_")
    v1 = "其他"
    if len(c.bars_raw) < w + n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    w_bars = get_sub_elements(c.bars_raw, di=1, n=w)
    n_bars = get_sub_elements(c.bars_raw, di=1, n=n)
    n_bars = deepcopy(n_bars)
    n_diff = n_bars[-1].close - n_bars[0].open

    # 找出 n_bars 中成交量最大的3根K线
    n_bars.sort(key=lambda x: x.vol, reverse=True)
    n_bars = n_bars[:3]

    # 计算 w_bars 中成交量的 q 分位数
    qth = np.quantile([x.vol for x in w_bars], q / 100)
    vol_match = all([x.vol > qth for x in n_bars])
    if vol_match and n_diff > 0:
        v1 = "看空"
    if vol_match and n_diff < 0:
        v1 = "看多"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_decision_V240608, "freq": "60分钟", "q": 80},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
