import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import pandas as pd
import numpy as np
from collections import OrderedDict
from czsc import CZSC
from loguru import logger
from czsc.signals.tas import update_macd_cache, update_ma_cache
from czsc.utils import get_sub_elements, create_single_signal, fast_slow_cross
from czsc.utils.sig import cross_zero_axis, cal_cross_num
from czsc.objects import Direction
from typing import List, Union


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def tas_low_trend_V230627(c: CZSC, **kwargs) -> OrderedDict:
    """阴跌趋势、小阳趋势

    参数模板："{freq}_D{di}N{n}TH{th}_趋势230627"

    **信号逻辑：**

    1、阴跌趋势：在连续N根K线上rolling计数，如果当前最低价小于rolling min close，min_count + 1
        ，当 min_count > 0.8 * n 且 N根K线中振幅超过TH的K线数量小于0.2 * N，则为阴跌趋势；
    2. 小阳趋势：在连续N根K线上rolling计数，如果当前最高价大于rolling max close，max_count + 1
        ，当 max_count > 0.8 * n 且 N根K线中振幅超过TH的K线数量小于0.2 * N，则为小阳趋势；

    **信号列表：**

    - Signal('15分钟_D1N13TH500_趋势230627_阴跌趋势_任意_任意_0')
    - Signal('15分钟_D1N13TH500_趋势230627_小阳趋势_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - n: 从dik往前数n根k线（此数值不需要精确，函数会自动截取最后上下0轴以后的数据）
        - th: 实体振幅阈值，单位为 BP

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 13))
    th = int(kwargs.get('th', 300))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}TH{th}_趋势230627".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + n + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n+5)
    solid_zf = [abs(x.close / x.open - 1) * 10000 for x in bars[5:]]
    if len([x for x in solid_zf if x > th]) > max(0.2 * n, 3):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    min_count = 0
    max_count = 0
    for i in range(5, len(bars)):
        bar, w5 = bars[i], bars[:i]
        if bar.low <= min([x.close for x in w5]):
            min_count += 1
        if bar.high >= max([x.close for x in w5]):
            max_count += 1

    if min_count >= 0.8 * n:
        v1 = "阴跌趋势"
    if max_count >= 0.8 * n:
        v1 = "小阳趋势"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': tas_low_trend_V230627, 'freq': '日线', 'di': 1, 'th': 500, 'n': 21}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
