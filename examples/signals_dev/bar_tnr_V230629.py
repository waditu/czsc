import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import math
import numpy as np
import pandas as pd
from collections import OrderedDict
from czsc import CZSC
from loguru import logger
from czsc.signals.tas import update_atr_cache
from czsc.utils import create_single_signal, get_sub_elements


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def bar_tnr_V230629(c: CZSC, **kwargs) -> OrderedDict:
    """趋势噪音指标（TNR，Trend to Noise Rate）分层

    参数模板："{freq}_D{di}TNR{timeperiod}_趋势V230629"

    **信号逻辑：**

    TNR计算公式：取N根K线，首尾两个close的绝对差值 除以 相邻两个close的绝对差值累计。
    
    取最近100个bar的TNR进行分层。

    **信号列表：**

    - Signal('15分钟_D1TNR14_趋势V230629_第7层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第6层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第8层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第9层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第10层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第5层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第2层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第1层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第3层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第4层_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: TNR指标的参数

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    freq = c.freq.value

    # 更新缓存
    cache_key = f"TNR{timeperiod}"
    for i, bar in enumerate(c.bars_raw, 0):
        if cache_key in bar.cache:
            continue
        if i < timeperiod:
            bar.cache[cache_key] = 0
        else:
            _bars = c.bars_raw[max(0, i - timeperiod):i + 1]
            sum_abs = sum([abs(_bars[j].close - _bars[j - 1].close) for j in range(1, len(_bars))])
            bar.cache[cache_key] = 0 if sum_abs == 0 else abs(_bars[-1].close - _bars[0].close) / sum_abs

    k1, k2, k3 = f"{freq}_D{di}TNR{timeperiod}_趋势V230629".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    tnr = [bar.cache[cache_key] for bar in bars]
    lev = pd.qcut(tnr, 10, labels=False, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"第{int(lev+1)}层")



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[10]
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': bar_tnr_V230629, 'freq': '15分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
