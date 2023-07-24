from collections import OrderedDict
import numpy as np
import pandas as pd
import talib as ta
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def obvm_line_V230610(c: CZSC, **kwargs) -> OrderedDict:
    """OBV能量指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_OBV能量V230610"

    **信号逻辑：**

    OBV 指标把成交量分为正的成交量（价格上升时的成交量）和负的
    成交量（价格下降时）的成交量。OBV 就是分了正负之后的成交量
    的累计和。

    首先，根据传入的参数 di、n 和 m，从 CZSC 对象中获取对应的 K 线数据，然后计算 OBV 序列。
    接着，使用 talib 库中的 EMA 函数计算 OBV 序列的短期和长期指数移动平均线，
    最后根据两条移动平均线的大小关系判断看多或看空信号。
    
    **信号列表：**

    - Signal('日线_D1N10M30_OBV能量V230610_看空_任意_任意_0')
    - Signal('日线_D1N10M30_OBV能量V230610_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param n: short窗口大小。
        - :param m: long窗口大小。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 10))
    m = int(kwargs.get("m", 30))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_OBV能量V230610".split('_')
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

    if len(c.bars_raw) < di + max(n, m) + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=max(n, m) + 10)
    obv_seq = np.array([x.cache[cache_key] for x in bars], dtype=np.float64)

    ema_n1 = ta.EMA(obv_seq, n)[-1]
    ema_n2 =ta.EMA(obv_seq, m)[-1]

    v1 =  "看多" if ema_n1 > ema_n2 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': obvm_line_V230610, 'freq': '日线', 'di': 1},
        # {'name': 'czsc.signals.tas_ma_base_V221101', 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()