import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.signals.tas import update_cci_cache
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger


def cci_decision_V240620(c: CZSC, **kwargs) -> OrderedDict:
    """根据CCI指标逆势用法，判断买卖决策区域

    参数模板："{freq}_N{n}CCI_决策区域V240620"

    **信号逻辑：**

    取最近N根K线，如果最小的CCI值小于 -100，开多；如果最大的CCI值大于 100，开空。

    **信号列表：**

    - Signal('15分钟_N4CCI_决策区域V240620_开多_2次_任意_0')
    - Signal('15分钟_N4CCI_决策区域V240620_开多_1次_任意_0')
    - Signal('15分钟_N4CCI_决策区域V240620_开空_1次_任意_0')
    - Signal('15分钟_N4CCI_决策区域V240620_开空_2次_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    n = int(kwargs.get("n", 2))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}CCI_决策区域V240620".split("_")
    v1 = "其他"
    cache_key = update_cci_cache(c, timeperiod=14)
    if len(c.bars_raw) < 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    cci_seq = [x.cache[cache_key] for x in c.bars_raw[-n:]]
    short_cci = [x for x in cci_seq if x > 100]
    long_cci = [x for x in cci_seq if x < -100]

    v2 = "任意"
    if min(cci_seq) < -100:
        v1 = "开多"
        v2 = f"{len(long_cci)}次"
    if max(cci_seq) > 100:
        v1 = "开空"
        v2 = f"{len(short_cci)}次"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cci_decision_V240620, "freq": "15分钟", "n": 4}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
