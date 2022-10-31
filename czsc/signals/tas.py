# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/27 23:17
describe: 使用 ta-lib 构建的信号函数

tas = ta-lib signals 的缩写
"""
from loguru import logger
try:
    import talib as ta
except:
    logger.warning(f"ta-lib 没有正确安装，相关信号函数无法正常执行。"
                   f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import numpy as np
from deprecated import deprecated
from collections import OrderedDict
from typing import List, Union, Tuple, Dict
from czsc import CZSC, Freq, Signal, CzscAdvancedTrader, RawBar, NewBar
from czsc.utils import same_dir_counts, fast_slow_cross, get_sub_elements


def update_macd_cache(c: CZSC, **kwargs):
    """更新MACD缓存"""
    fastperiod = kwargs.get('fastperiod', 12)
    slowperiod = kwargs.get('slowperiod', 26)
    signalperiod = kwargs.get('signalperiod', 9)

    min_count = fastperiod + slowperiod
    cache_key = f"MACD"
    if not hasattr(c.bars_raw[-1].cache, cache_key) or len(c.bars_raw) < min_count:
        close = np.array([x.close for x in c.bars_raw])
        min_count = 0
    else:
        close = np.array([x.close for x in c.bars_raw[-min_count-20:]])

    dif, dea, macd = ta.MACD(close, fastperiod=fastperiod,
                             slowperiod=slowperiod, signalperiod=signalperiod)

    for i in range(1, len(close)-min_count-10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: {'dif': dif[-i], 'dea': dea[-i], 'macd': macd[-i]}})
        c.bars_raw[-i].cache = _c


def tas_macd_power_V221028(c: CZSC, di: int = 1) -> OrderedDict:
    """MACD多空/方向

    信号逻辑：
    1. dik 对应的MACD值大于0，多头；反之，空头
    2. dik 的MACD值大于上一个值，向上；反之，向下

    信号列表：
    - Signal('30分钟_D1K_MACD_多头_向下_任意_0')
    - Signal('30分钟_D1K_MACD_空头_向下_任意_0')
    - Signal('30分钟_D1K_MACD_多头_向上_任意_0')
    - Signal('30分钟_D1K_MACD_空头_向上_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return:
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD".split('_')
    macd = [x.cache['MACD']['macd'] for x in c.bars_raw[-5-di:]]
    v1 = "多头" if macd[-di] >= 0 else "空头"
    v2 = "向上" if macd[-di] >= macd[-di-1] else "向下"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s



