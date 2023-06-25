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
from czsc.utils.sig import cross_zero_axis, cal_cross_num, down_cross_count
from czsc.objects import Direction
from typing import List, Union


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------

def tas_cross_status_V230619(c: CZSC, **kwargs) -> OrderedDict:
    """0轴上下金死叉次数计算信号函数 贡献者：谌意勇

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619"

    **信号逻辑：**

    精确确立MACD指标中0轴以上或以下位置第几次金叉和死叉，作为开仓的辅助买点：

    **信号列表：**

    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴上死叉第2次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下金叉第1次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下死叉第1次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下金叉第2次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下死叉第2次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下金叉第3次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴上死叉第1次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴上金叉第1次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下死叉第3次_任意_任意_0')
    - Signal('日线_D1MACD12#26#9_金死叉V230619_0轴下金叉第4次_任意_任意_0')
    
    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param fastperiod: MACD快线周期
        - :param slowperiod: MACD慢线周期
        - :param signalperiod: MACD信号线周期

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))
    cache_key = update_macd_cache(c, **kwargs)
    s = OrderedDict()
    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    k1, k2, k3 = f"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619".split('_')
    v1 = "其他"
    if len(bars)>=100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]

        num_k = cross_zero_axis(dif, dea) # type: ignore
        dif_temp = get_sub_elements(dif, di=di, n=num_k)
        dea_temp = get_sub_elements(dea, di=di, n=num_k)

        if dif[-1] < 0 and dea[-1] < 0:
            down_num_sc = down_cross_count(dif_temp, dea_temp)
            down_num_jc = down_cross_count(dea_temp, dif_temp)
            if dif[-1] > dea[-1] and dif[-2] < dea[-2]:
                v1 = f'0轴下金叉第{down_num_jc}次'
            elif dif[-1] < dea[-1] and dif[-2] > dea[-2]:
                v1 = f'0轴下死叉第{down_num_sc}次'


        elif dif[-1] > 0 and dea[-1] > 0:
            up_num_sc = down_cross_count(dif_temp, dea_temp)
            up_num_jc = down_cross_count(dea_temp, dif_temp)
            if dif[-1] > dea[-1] and dif[-2] < dea[-2]:
                v1 = f'0轴上金叉第{up_num_jc}次'
            elif dif[-1] < dea[-1] and dif[-2] > dea[-2]:
                v1 = f'0轴上死叉第{up_num_sc}次'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    

def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': tas_cross_status_V230619, 'freq': '日线', 'di': 1, 'th': 5}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
