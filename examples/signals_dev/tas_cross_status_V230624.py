import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import pandas as pd
import numpy as np
from collections import OrderedDict
from czsc import CZSC
from czsc.signals.tas import update_macd_cache, update_ma_cache
from czsc.utils import get_sub_elements, create_single_signal, fast_slow_cross
from czsc.utils.sig import cross_zero_axis, cal_cross_num
from czsc.objects import Direction
from typing import List, Union



def tas_cross_status_V230624(c: CZSC, **kwargs) -> OrderedDict:
    """指定金死叉数值信号函数,以此来确定MACD交易区间    贡献者：谌意勇

    参数模板："{freq}_D{di}N{n}MD{md}_MACD交叉数量V230624"

    **信号逻辑：**

    1、通过指定0轴上下金死叉数量，来选择自己想要的指标形态，通过配合其他信号函数出信号
    2、金叉数量和死叉数量要注意连续对应。0轴上一定是第一次先死叉，再金叉，死叉的数值同
        金叉数值相比永远是相等或者大1，不能出现>=2的情况，0轴下则反之。

    **信号列表：**

    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴上金叉第1次_0轴上死叉第1次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴上金叉第1次_0轴上死叉第2次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第0次_0轴下死叉第0次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第1次_0轴下死叉第0次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第1次_0轴下死叉第1次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第2次_0轴下死叉第1次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第2次_0轴下死叉第2次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第3次_0轴下死叉第2次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴上金叉第0次_0轴上死叉第0次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴上金叉第0次_0轴上死叉第1次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第3次_0轴下死叉第3次_任意_0')
    - Signal('日线_D1N100MD1_MACD交叉数量V230624_0轴下金叉第4次_0轴下死叉第3次_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - n: 从dik往前数n根k线（此数值不需要精确，函数会自动截取最后上下0轴以后的数据）
        - md: 抖动过滤参数,金死叉之间格距离小于此数值，将被忽略（去除一些杂波扰动因素,最小值不小于1）
                0轴上下金死叉状态信息，与其他信号加以辅助操作。

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 100))
    md = int(kwargs.get('md', 1))  # md 是 min distance 的缩写，表示金死叉之间格距离小于此数值，将被忽略（去除一些杂波扰动因素,最小值不小于1）
    assert md >= 1, "md必须大于等于1"
    freq = c.freq.value
    cache_key = update_macd_cache(c, **kwargs)

    k1, k2, k3 = f"{freq}_D{di}N{n}MD{md}_MACD交叉数量V230624".split('_')
    v1 = "其他"
    v2 = "其他"
    if len(c.bars_raw) < n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    dif = [x.cache[cache_key]['dif'] for x in bars]
    dea = [x.cache[cache_key]['dea'] for x in bars]
    num_k = cross_zero_axis(dif, dea)
    dif_temp = get_sub_elements(dif, di=1, n=num_k)
    dea_temp = get_sub_elements(dea, di=1, n=num_k)
    cross = fast_slow_cross(dif_temp, dea_temp)

    jc, sc = cal_cross_num(cross, md)

    if dif[-1] < 0 and dea[-1] < 0:
        v1 = f'0轴下金叉第{jc}次'
        v2 = f'0轴下死叉第{sc}次'

    elif dif[-1] > 0 and dea[-1] > 0:
        v1 = f'0轴上金叉第{jc}次'
        v2 = f'0轴上死叉第{sc}次'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': tas_cross_status_V230624, 'freq': '日线', 'di': 1, 'th': 5}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
