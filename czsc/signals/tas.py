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
from collections import OrderedDict
from typing import List, Union, Tuple, Dict
from czsc import CZSC, Signal
from czsc.utils import get_sub_elements


def update_ma_cache(c: CZSC, ma_type: str, timeperiod: int, **kwargs) -> None:
    """更新均线缓存

    :param c: CZSC对象
    :param ma_type: 均线类型
    :param timeperiod: 计算周期
    :return:
    """

    ma_type_map = {
        'SMA': ta.MA_Type.SMA,
        'EMA': ta.MA_Type.EMA,
        'WMA': ta.MA_Type.WMA,
        'KAMA': ta.MA_Type.KAMA,
        'TEMA': ta.MA_Type.TEMA,
        'DEMA': ta.MA_Type.DEMA,
        'MAMA': ta.MA_Type.MAMA,
        'T3': ta.MA_Type.T3,
        'TRIMA': ta.MA_Type.TRIMA,
    }

    min_count = timeperiod
    cache_key = f"{ma_type.upper()}{timeperiod}"
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        min_count = 0
    else:
        # 增量更新缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10:]])

    ma = ta.MA(close, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])

    for i in range(1, len(close) - min_count - 5):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: ma[-i]})
        c.bars_raw[-i].cache = _c


def update_macd_cache(c: CZSC, **kwargs) -> None:
    """更新MACD缓存

    :param c: CZSC对象
    :return:
    """
    fastperiod = kwargs.get('fastperiod', 12)
    slowperiod = kwargs.get('slowperiod', 26)
    signalperiod = kwargs.get('signalperiod', 9)

    min_count = fastperiod + slowperiod
    cache_key = f"MACD"
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count:
        close = np.array([x.close for x in c.bars_raw])
        min_count = 0
    else:
        close = np.array([x.close for x in c.bars_raw[-min_count - 20:]])

    dif, dea, macd = ta.MACD(close, fastperiod=fastperiod,
                             slowperiod=slowperiod, signalperiod=signalperiod)

    for i in range(1, len(close) - min_count - 10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: {'dif': dif[-i], 'dea': dea[-i], 'macd': macd[-i]}})
        c.bars_raw[-i].cache = _c


def tas_macd_base_V221028(c: CZSC, di: int = 1, key="macd") -> OrderedDict:
    """MACD|DIF|DEA 多空和方向信号

    **信号逻辑：**

    1. dik 对应的MACD值大于0，多头；反之，空头
    2. dik 的MACD值大于上一个值，向上；反之，向下

    **信号列表：**

    - Signal('30分钟_D1K_MACD_多头_向下_任意_0')
    - Signal('30分钟_D1K_MACD_空头_向下_任意_0')
    - Signal('30分钟_D1K_MACD_多头_向上_任意_0')
    - Signal('30分钟_D1K_MACD_空头_向上_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 [macd, dif, dea]
    :return:
    """
    assert key.lower() in ['macd', 'dif', 'dea']
    k1, k2, k3 = f"{c.freq.value}_D{di}K_{key.upper()}".split('_')
    macd = [x.cache['MACD'][key.lower()] for x in c.bars_raw[-5 - di:]]
    v1 = "多头" if macd[-di] >= 0 else "空头"
    v2 = "向上" if macd[-di] >= macd[-di - 1] else "向下"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def tas_ma_base_V221101(c: CZSC, di: int = 1, key="SMA5") -> OrderedDict:
    """MA 多空和方向信号

    **信号逻辑：**

    1. close > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1K_SMA5_空头_向下_任意_0')
    - Signal('15分钟_D1K_SMA5_多头_向下_任意_0')
    - Signal('15分钟_D1K_SMA5_多头_向上_任意_0')
    - Signal('15分钟_D1K_SMA5_空头_向上_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，必须是 `update_ma_cache` 中已经缓存的 key
    :return:
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_{key.upper()}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "多头" if bars[-1].close >= bars[-1].cache[key] else "空头"
    v2 = "向上" if bars[-1].cache[key] >= bars[-2].cache[key] else "向下"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s
