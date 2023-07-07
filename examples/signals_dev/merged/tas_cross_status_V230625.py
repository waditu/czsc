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


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def tas_cross_status_V230625(c: CZSC, **kwargs) -> OrderedDict:
    """指定金死叉数值信号函数, 以此来确定MACD交易区间    贡献者：谌意勇

    参数模板："{freq}_D{di}N{n}MD{md}J{j}S{s}_MACD交叉数量V230625"

    **信号逻辑：**

    1、通过指定jc或者sc数值来确定为哪第几次金叉或死叉之后的信号。两者最少要指定一个，并且指定其中一个时，另外一个需为0.

    **信号列表：**

    - Signal('15分钟_D1N100MD1J3S0_MACD交叉数量V230625_0轴下第3次金叉以后_任意_任意_0')
    - Signal('15分钟_D1N100MD1J3S0_MACD交叉数量V230625_0轴上第3次金叉以后_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - j: 金叉数值
        - s: 死叉数值
        - n: 从dik往前数n根k线（此数值不需要精确，函数会自动截取最后上下0轴以后的数据）
        - md: 抖动过滤参数,金死叉之间格距离小于此数值，将被忽略（去除一些杂波扰动因素,最小值不小于1
                0轴上下金死叉状态信息，与其他信号加以辅助操作。

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    j = int(kwargs.get('j', 0))
    s = int(kwargs.get('s', 0))
    n = int(kwargs.get('n', 100))
    md = int(kwargs.get('md', 1))
    freq = c.freq.value
    cache_key = update_macd_cache(c, **kwargs)
    assert j * s == 0, "金叉死叉参数错误, j和s必须有一个为0"

    k1, k2, k3 = f"{freq}_D{di}N{n}MD{md}J{j}S{s}_MACD交叉数量V230625".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + n + 1:
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
        if jc >= j and s == 0:
            v1 = f'0轴下第{j}次金叉以后'
        elif j == 0 and sc >= s:
            v1 = f'0轴下第{s}次死叉以后'

    elif dif[-1] > 0 and dea[-1] > 0:
        if jc >= j and s == 0:
            v1 = f'0轴上第{j}次金叉以后'
        elif j == 0 and sc >= s:
            v1 = f'0轴上第{s}次死叉以后'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': tas_cross_status_V230625, 'freq': '15分钟', 'di': 1, 'j': 3}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
