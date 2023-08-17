from loguru import logger

try:
    import talib as ta
except:
    logger.warning(
        f"ta-lib 没有正确安装，相关信号函数无法正常执行。" f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
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
from typing import Union, List


def tas_angle_V230802(c: CZSC, **kwargs) -> OrderedDict:
    """笔的角度比较 贡献者：谌意勇

    参数模板："{freq}_D{di}N{n}T{th}_笔角度V230802"

    **信号逻辑：**

    笔的角度，走过的笔的空间最高价和最低价的空间与走过的时间（原始K的数量）形成比值。
    如果当前笔的角度小于前面9笔的平均角度的50%，当前笔向上认为是空头笔，否则是多头笔。

    **信号列表：**

    - Signal('60分钟_D1N9T50_笔角度V230802_空头_任意_任意_0')
    - Signal('60分钟_D1N9T50_笔角度V230802_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        -n：统计笔的数量
        -di：取第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 9))
    th = int(kwargs.get('th', 50))
    assert 300 > th > 30, "th 取值范围为 30 ~ 300"
    
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}T{th}_笔角度V230802".split('_')
    v1 = '其他'
    if len(c.bi_list) < di + 2 * n + 2 or len(c.bars_ubi) >= 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=n*2+1)
    b1 = bis[-1]
    b1_angle = b1.power_price / b1.length
    same_dir_ang = [bi.power_price / bi.length for bi in bis[:-1] if bi.direction == b1.direction][-n:]

    if b1_angle < np.mean(same_dir_ang) * th / 100:
        v1 = '空头' if b1.direction == Direction.Up else '多头'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_angle_V230802, 'freq': "60分钟", 'di': 1,'n': 9}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0)  # type: ignore


if __name__ == '__main__':
    check()
