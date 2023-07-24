from collections import OrderedDict
import numpy as np
import pandas as pd
import talib as ta
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def obv_up_dw_line_V230719(c: CZSC, **kwargs) -> OrderedDict:
    """OBV能量指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719"

    **信号逻辑：**

    OBV 指标把成交量分为正的成交量（价格上升时的成交量）和负的成交量（价格下降时）的成交量。
    OBV 就是分了正负之后的成交量的累计和。

    1. 先定义OBVM，OBVM是 OBV 7天的指数平均。
    2. 再定义一条信号线Signal line，这条线是OBVM 10天的指数平均。

    其中的「7天」和「10天」都是参数，根据你的交易时间级别设置，设置的越小，OBVM对成交量的变化越敏感，
    产生的交易信号也就越多。

    开多仓的规则：当OBVM上穿Signal line，开多仓；当OBVM下穿Signal line，平仓。这个规则只捕捉上涨趋势。

    **信号列表：**

    - Signal('日线_D1N7M10MO3_OBV能量V230719_看多_任意_任意_0')
    - Signal('日线_D1N7M10MO3_OBV能量V230719_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param n: short窗口大小。
        - :param m: long窗口大小。
        - :param max_overlap: 信号计算时，最大重叠K线数量。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 7))
    m = int(kwargs.get("m", 10))
    max_overlap = int(kwargs.get("max_overlap", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719".split('_')
    v1 = "其他"

    # 计算OBV，缓存到bar.cache中
    cache_key = "OBV"
    for i in range(1, len(c.bars_raw)):
        bar1, bar2 = c.bars_raw[i - 1], c.bars_raw[i]
        if cache_key not in bar1.cache:
            last_obv = bar1.vol if bar1.close > bar1.open else -bar1.vol
            bar1.cache[cache_key] = last_obv
        else:
            last_obv = bar1.cache[cache_key]

        if cache_key not in bar2.cache:
            cur_obv = bar2.vol if bar2.close > bar2.open else -bar2.vol
            bar2.cache[cache_key] = last_obv + cur_obv

    min_k_num = di + max(n, m) + max_overlap + 10
    if len(c.bars_raw) < min_k_num:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=min_k_num)
    obv_seq = np.array([x.cache[cache_key] for x in bars], dtype=np.float64)
    obvm = ta.EMA(obv_seq, n)
    sig_ = ta.EMA(obvm, m)

    if obvm[-1] > sig_[-1] and obvm[-max_overlap] < sig_[-max_overlap]:
        v1 = "看多"
    elif obvm[-1] < sig_[-1] and obvm[-max_overlap] > sig_[-max_overlap]:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': obv_up_dw_line_V230719, 'freq': '日线', 'di': 1},
        # {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()