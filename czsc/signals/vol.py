# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/25 17:43
describe: 成交量相关信号
"""
from loguru import logger
try:
    import talib as ta
except:
    logger.warning(f"ta-lib 没有正确安装，相关信号函数无法正常执行。"
                   f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Freq, Signal
from czsc.utils.sig import get_sub_elements, create_single_signal


def update_vol_ma_cache(c: CZSC, ma_type: str, timeperiod: int, **kwargs):
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
        'TRIMA': ta.MA_Type.TRIMA,
    }

    ma_type = ma_type.upper()
    assert ma_type in ma_type_map.keys(), f"{ma_type} 不是支持的均线类型，可选值：{list(ma_type_map.keys())}"
    cache_key = f"VOL#{ma_type.upper()}{timeperiod}"

    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        data = np.array([x.vol for x in c.bars_raw], dtype=np.float64)
        ma = ta.MA(data, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        assert len(ma) == len(data)
        for i in range(len(data)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: ma[i] if ma[i] else data[i]})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近3个K线缓存
        data = np.array([x.vol for x in c.bars_raw[-timeperiod - 10:]], dtype=np.float64)
        ma = ta.MA(data, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        for i in range(1, 4):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: ma[-i]})
            c.bars_raw[-i].cache = _c
    return cache_key


def vol_single_ma_V230214(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """成交量单均线信号

    **信号逻辑：**

    1. vol > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下

    **信号列表：**

    - Signal('日线_D2_VOL#SMA5_多头_向上_任意_0')
    - Signal('日线_D2_VOL#SMA5_空头_向上_任意_0')
    - Signal('日线_D2_VOL#SMA5_空头_向下_任意_0')
    - Signal('日线_D2_VOL#SMA5_多头_向下_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param timeperiod: 均线计算周期
    :return: 信号识别结果
    """
    ma_type = kwargs.get("ma_type", "SMA")
    timeperiod = kwargs.get("timeperiod", 5)
    cache_key = update_vol_ma_cache(c, ma_type, timeperiod)

    k1, k2, k3 = f"{c.freq.value}_D{di}_{cache_key}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "多头" if bars[-1].vol >= bars[-1].cache[cache_key] else "空头"
    v2 = "向上" if bars[-1].cache[cache_key] >= bars[-2].cache[cache_key] else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def vol_double_ma_V230214(c: CZSC, di: int = 1, t1: int = 5, t2: int = 20, **kwargs) -> OrderedDict:
    """成交量双均线信号

    **信号逻辑：**

    1. 短均线在长均线上方，看多；反之，看空

    **信号列表：**

    - Signal('日线_D2VOL#SMA5_VOL#SMA20_看空_任意_任意_0')
    - Signal('日线_D2VOL#SMA5_VOL#SMA20_看多_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param t1: 短线均线
    :param t2: 长线均线
    :param kwargs:
    :return: 信号识别结果
    """
    assert t2 > t1, "t2必须是长线均线，t1为短线均线"
    ma_type = kwargs.get("ma_type", "SMA")
    cache_key1 = update_vol_ma_cache(c, ma_type, t1)
    cache_key2 = update_vol_ma_cache(c, ma_type, t2)

    k1, k2, k3 = f"{c.freq.value}_D{di}{cache_key1}_{cache_key2}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "看多" if bars[-1].cache[cache_key1] >= bars[-1].cache[cache_key2] else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


