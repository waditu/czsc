from loguru import logger

try:
    import talib as ta
except:
    logger.warning(f"ta-lib 没有正确安装，相关信号函数无法正常执行。" f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import math
import pandas as pd
import numpy as np
from collections import OrderedDict
from deprecated import deprecated
from czsc.analyze import CZSC
from czsc.objects import Signal, Direction, BI, RawBar, FX
from czsc.signals.tas import update_ma_cache
from czsc.utils import get_sub_elements, fast_slow_cross, count_last_same, create_single_signal
from czsc.utils.sig import cross_zero_axis, cal_cross_num, down_cross_count
from typing import Union,List



def tas_rumi_V230704(c: CZSC, **kwargs) -> OrderedDict:
    """对均线偏离度平滑处理,通过平滑处理的方式降低DIFF的敏感度来解决均线缠绕的问题 贡献者：谌意勇

    参数模板："{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704"

    **信号逻辑：**

    RUMI 计算参考：
    1. https://zhuanlan.zhihu.com/p/610377004
    2. https://zhuanlan.zhihu.com/p/618394552

    多空规则：
    1. RUMI上穿0轴，买入做多
    2. RUMI下穿0轴，卖出做空。

    **信号列表：**

    - Signal('60分钟_D1F3S50R30_BS辅助V230704_空头_任意_任意_0')
    - Signal('60分钟_D1F3S50R30_BS辅助V230704_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 信号计算截止倒数第i根K线
        - timeperiod1: 均线1的周期
        - timeperiod2: 均线2的周期
        - rumi_window: rumi的周期

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    rumi_window = int(kwargs.get('rumi_window', 30))
    timeperiod1 = int(kwargs.get('timeperiod1', 3))
    timeperiod2 = int(kwargs.get('timeperiod2', 50))
    
    assert rumi_window < timeperiod2, "rumi_window 必须小于 timeperiod2"
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704".split('_')
    v1 = '其他'
    
    if len(c.bars_raw) < di + timeperiod2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
     
    key1 = update_ma_cache(c, ma_type='SMA', timeperiod=timeperiod1)
    key2 = update_ma_cache(c, ma_type='WMA', timeperiod=timeperiod2)
    bars = get_sub_elements(c.bars_raw, di=di, n=timeperiod2)
    fast_array = np.array([x.cache[key1] for x in bars])
    slow_array = np.array([x.cache[key2] for x in bars])
    diff_array = fast_array - slow_array
    rumi_array = ta.MA(diff_array, timeperiod=rumi_window, matype=ta.MA_Type.SMA)

    if rumi_array[-1] > 0 and rumi_array[-2] < 0:
        v1='多头'
    elif rumi_array[-1] < 0 and rumi_array[-2] > 0:
        v1='空头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_rumi_V230704, 'freq': "60分钟", 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0) # type: ignore


if __name__ == '__main__':
    check()
