import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def cxt_decision_V240526(c: CZSC, **kwargs) -> OrderedDict:
    """根据最后一根K线与最后一笔的分型区间，构建交易决策区域

    参数模板："{freq}_分型区域N{n}_决策区域V240526"

    **信号逻辑：**

    1. 取最近一根K线和最后一笔的结束分型
    2. 取100根K线，计算 unique price 序列
    3. 如果当前K线的收盘价在结束分型的 N 个 unique price 之间，认为是一个交易决策区域

    **信号列表：**

    - Signal('60分钟_分型区域N9_决策区域V240526_开多_任意_任意_0')
    - Signal('60分钟_分型区域N9_决策区域V240526_开空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 9))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_分型区域N{n}_决策区域V240526".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 120:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=100)
    prices = [x.close for x in bars] + [x.high for x in bars] + [x.low for x in bars] + [x.open for x in bars]
    prices = list(set(prices))

    bi = c.bi_list[-1]
    bar = c.bars_raw[-1]
    if bi.direction == Direction.Up:
        in_prices = [x for x in prices if bar.close <= x <= bi.fx_b.high]
        if len(in_prices) <= n:
            v1 = "开空"

    elif bi.direction == Direction.Down:
        in_prices = [x for x in prices if bi.fx_b.low <= x <= bar.close]
        if len(in_prices) <= n:
            v1 = "开多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_decision_V240526, "freq": "15分钟", "n": 20}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
