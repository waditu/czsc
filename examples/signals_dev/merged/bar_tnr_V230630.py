import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import math
import numpy as np
from collections import OrderedDict
from czsc import CZSC
from loguru import logger
from czsc.signals.tas import update_atr_cache
from czsc.utils import create_single_signal, get_sub_elements


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def bar_tnr_V230630(c: CZSC, **kwargs) -> OrderedDict:
    """趋势噪音指标（TNR，Trend to Noise Rate）

    参数模板："{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630"

    **信号逻辑：**

    TNR计算公式：取N根K线，首尾两个close的绝对差值 除以 相邻两个close的绝对差值累计。

    噪音变化判断，如果 t 时刻的 TNR > 过去k个TNR的均值，则说明噪音在减少，此时趋势较强；反之，噪音在增加，此时趋势较弱。

    **信号列表：**

    - Signal('15分钟_D1TNR14K3_趋势V230630_噪音减少_任意_任意_0')
    - Signal('15分钟_D1TNR14K3_趋势V230630_噪音增加_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: TNR指标的参数
        - k: 过去k个TNR的均值

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    k = int(kwargs.get('k', 3))
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

    k1, k2, k3 = f"{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=k)
    delta_tnr = bars[-1].cache[cache_key] - np.mean([bar.cache[cache_key] for bar in bars])
    v1 = "噪音减少" if delta_tnr > 0 else "噪音增加"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[10]
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': bar_tnr_V230630, 'freq': '15分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
