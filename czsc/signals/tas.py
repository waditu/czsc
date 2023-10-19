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
    logger.warning(f"ta-lib 没有正确安装，相关信号函数无法正常执行。" f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import math
import pandas as pd
import numpy as np
from collections import OrderedDict
from deprecated import deprecated
from czsc.analyze import CZSC
from czsc.objects import Signal, Direction, BI, RawBar, FX, Mark, ZS
from czsc.traders.base import CzscSignals
from czsc.utils import get_sub_elements, fast_slow_cross, count_last_same, create_single_signal, single_linear
from czsc.utils.sig import cross_zero_axis, cal_cross_num, down_cross_count


def update_ma_cache(c: CZSC, **kwargs):
    """更新均线缓存

    :param c: CZSC对象
    :param kwargs:
        - ma_type: 均线类型，可选值：SMA, EMA, WMA, KAMA, TEMA, DEMA, MAMA, TRIMA
        - timeperiod: 计算周期
    :return: cache_key
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
    timeperiod = int(kwargs["timeperiod"])
    ma_type = kwargs.get("ma_type", 'SMA').upper()
    assert ma_type in ma_type_map.keys(), f"{ma_type} 不是支持的均线类型，可选值：{list(ma_type_map.keys())}"

    cache_key = f"{ma_type}#{timeperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        ma = ta.MA(close, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        assert len(ma) == len(close)
        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: ma[i] if ma[i] else close[i]})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10 :]])
        ma = ta.MA(close, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: ma[-i]})
            c.bars_raw[-i].cache = _c
    return cache_key


def update_macd_cache(c: CZSC, **kwargs):
    """更新MACD缓存

    :param c: CZSC对象
    :return:
    """
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = f"MACD{fastperiod}#{slowperiod}#{signalperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    min_count = signalperiod + slowperiod + 168
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 15:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        dif, dea, macd = ta.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            dif_i = dif[i] if dif[i] else close[i]
            dea_i = dea[i] if dea[i] else close[i]
            macd_i = dif_i - dea_i
            _c.update({cache_key: {'dif': dif_i, 'dea': dea_i, 'macd': macd_i}})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-min_count - 10 :]])
        dif, dea, macd = ta.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: {'dif': dif[-i], 'dea': dea[-i], 'macd': macd[-i]}})
            c.bars_raw[-i].cache = _c
    return cache_key


def update_boll_cache_V230228(c: CZSC, **kwargs):
    """更新K线的BOLL缓存，仅传入一个标准差倍数

    :param c: 交易对象
    :return:
    """
    timeperiod = int(kwargs.get('timeperiod', 20))
    nbdev = int(kwargs.get('nbdev', 20))  # 标准差倍数，计算时除以10，如20表示2.0，即2倍标准差
    cache_key = f"BOLL{timeperiod}S{nbdev}"
    nbdev = nbdev / 10

    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdev, nbdevdn=nbdev, matype=0)

        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            if not m[i]:
                _data = {"上轨": close[i], "中线": close[i], "下轨": close[i]}
            else:
                _data = {"上轨": u1[i], "中线": m[i], "下轨": l1[i]}
            _c.update({cache_key: _data})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10 :]])
        u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdev, nbdevdn=nbdev, matype=0)

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: {"上轨": u1[-i], "中线": m[-i], "下轨": l1[-i]}})
            c.bars_raw[-i].cache = _c

    return cache_key


def update_boll_cache(c: CZSC, **kwargs):
    """更新K线的BOLL缓存

    :param c: 交易对象
    :return:
    """
    timeperiod = int(kwargs.get('timeperiod', 20))
    cache_key = f"BOLL{timeperiod}"

    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    dev_seq = (1.382, 2, 2.764)
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[0], nbdevdn=dev_seq[0], matype=0)
        u2, m, l2 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[1], nbdevdn=dev_seq[1], matype=0)
        u3, m, l3 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[2], nbdevdn=dev_seq[2], matype=0)

        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            if not m[i]:
                _data = {
                    "上轨3": close[i],
                    "上轨2": close[i],
                    "上轨1": close[i],
                    "中线": close[i],
                    "下轨1": close[i],
                    "下轨2": close[i],
                    "下轨3": close[i],
                }
            else:
                _data = {"上轨3": u3[i], "上轨2": u2[i], "上轨1": u1[i], "中线": m[i], "下轨1": l1[i], "下轨2": l2[i], "下轨3": l3[i]}
            _c.update({cache_key: _data})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10 :]])
        u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[0], nbdevdn=dev_seq[0], matype=0)
        u2, m, l2 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[1], nbdevdn=dev_seq[1], matype=0)
        u3, m, l3 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[2], nbdevdn=dev_seq[2], matype=0)

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update(
                {
                    cache_key: {
                        "上轨3": u3[-i],
                        "上轨2": u2[-i],
                        "上轨1": u1[-i],
                        "中线": m[-i],
                        "下轨1": l1[-i],
                        "下轨2": l2[-i],
                        "下轨3": l3[-i],
                    }
                }
            )
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_boll_vt_V230212(c: CZSC, **kwargs) -> OrderedDict:
    """以BOLL通道为依据的多空进出场信号

    参数模板："{freq}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212"

    **信号逻辑：**

    1. 看多，当日收盘价在上轨上方，且最近max_overlap根K线中至少有一个收盘价都在上轨下方；
    2. 看空，当日收盘价在下轨下方，且最近max_overlap根K线中至少有一个收盘价都在下轨上方；

    **信号列表：**

    - Signal('15分钟_D1BOLL20S20MO5_BS辅助V230212_看空_任意_任意_0')
    - Signal('15分钟_D1BOLL20S20MO5_BS辅助V230212_看多_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 20))
    nbdev = int(kwargs.get('nbdev', 20))  # 标准差倍数，计算时除以10，如20表示2.0，即2倍标准差
    max_overlap = int(kwargs.get('max_overlap', 5))
    k1, k2, k3 = f"{c.freq.value}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212".split('_')
    v1 = "其他"

    key = update_boll_cache_V230228(c, **kwargs)
    _bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap + 1)
    if len(_bars) < max_overlap + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if _bars[-1].close > _bars[-1].cache[key]['上轨'] and any([x.close < x.cache[key]['上轨'] for x in _bars]):
        v1 = "看多"

    elif _bars[-1].close < _bars[-1].cache[key]['下轨'] and any([x.close > x.cache[key]['下轨'] for x in _bars]):
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


# MACD信号计算函数
# ======================================================================================================================
def tas_macd_base_V221028(c: CZSC, **kwargs) -> OrderedDict:
    """MACD|DIF|DEA 多空和方向信号

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}#{key}_BS辅助V221028"

    **信号逻辑：**

    1. dik 对应的MACD值大于0，多头；反之，空头
    2. dik 的MACD值大于上一个值，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9#MACD_BS辅助V221028_空头_向下_任意_0')
    - Signal('15分钟_D1MACD12#26#9#MACD_BS辅助V221028_空头_向上_任意_0')
    - Signal('15分钟_D1MACD12#26#9#MACD_BS辅助V221028_多头_向上_任意_0')
    - Signal('15分钟_D1MACD12#26#9#MACD_BS辅助V221028_多头_向下_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param key: 指定使用哪个Key来计算，可选值 [macd, dif, dea]
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'MACD').upper()
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)

    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}#{key}_BS辅助V221028".split('_')

    macd = [x.cache[cache_key][key.lower()] for x in c.bars_raw[-5 - di :]]
    v1 = "多头" if macd[-di] >= 0 else "空头"
    v2 = "向上" if macd[-di] >= macd[-di - 1] else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_direct_V221106(c: CZSC, **kwargs) -> OrderedDict:
    """MACD方向；贡献者：马鸣

    参数模板："{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106"

    **信号逻辑：** 连续三根macd柱子值依次增大，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1K#MACD12#26#9方向_BS辅助V221106_向下_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9方向_BS辅助V221106_模糊_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9方向_BS辅助V221106_向上_任意_任意_0')

    **参数列表：**

    :param c: CZSC对象
    :param di: 连续倒3根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106".split("_")
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    macd = [x.cache[cache_key]['macd'] for x in bars]

    if len(macd) != 3:
        v1 = "模糊"
    else:
        # 最近3根 MACD 方向信号
        if macd[-1] > macd[-2] > macd[-3]:
            v1 = "向上"
        elif macd[-1] < macd[-2] < macd[-3]:
            v1 = "向下"
        else:
            v1 = "模糊"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_power_V221108(c: CZSC, **kwargs) -> OrderedDict:
    """MACD强弱

    参数模板："{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108"

    **信号逻辑：**

    1. 指标超强满足条件：DIF＞DEA＞0；释义：指标超强表示市场价格处于中长期多头趋势中，可能形成凌厉的逼空行情
    2. 指标强势满足条件：DIF-DEA＞0（MACD柱线＞0）释义：指标强势表示市场价格处于中短期多头趋势中，价格涨多跌少，通常是反弹行情
    3. 指标弱势满足条件：DIF-DEA＜0（MACD柱线＜0）释义：指标弱势表示市场价格处于中短期空头趋势中，价格跌多涨少，通常是回调行情
    4. 指标超弱满足条件：DIF＜DEA＜0释义：指标超弱表示市场价格处于中长期空头趋势中，可能形成杀多行情

    **信号列表：**

    - Signal('15分钟_D1K#MACD12#26#9强弱_BS辅助V221108_弱势_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9强弱_BS辅助V221108_超弱_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9强弱_BS辅助V221108_强势_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9强弱_BS辅助V221108_超强_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号产生在倒数第di根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108".split("_")

    v1 = "其他"
    if len(c.bars_raw) > di + 10:
        bar = c.bars_raw[-di]
        dif, dea = bar.cache[cache_key]['dif'], bar.cache[cache_key]['dea']

        if dif >= dea >= 0:
            v1 = "超强"
        elif dif - dea > 0:
            v1 = "强势"
        elif dif <= dea <= 0:
            v1 = "超弱"
        elif dif - dea < 0:
            v1 = "弱势"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_first_bs_V221201(c: CZSC, **kwargs):
    """MACD金叉死叉判断第一买卖点

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201"

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221201_一买_任意_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221201_一卖_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=300)

    v1 = "其他"
    if len(bars) >= 100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]
        macd = [x.cache[cache_key]['macd'] for x in bars]

        cross = fast_slow_cross(dif, dea)
        up = [x for x in cross if x['类型'] == "金叉" and x['距离'] > 5]
        dn = [x for x in cross if x['类型'] == "死叉" and x['距离'] > 5]

        b1_con1 = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['慢线'] < 0
        b1_con2 = len(dn) > 3 and dn[-2]['慢线'] < 0 and dn[-3]['慢线'] < 0
        b1_con3 = len(macd) > 10 and macd[-1] > macd[-2]
        if b1_con1 and b1_con2 and b1_con3:
            v1 = "一买"

        s1_con1 = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['慢线'] > 0
        s1_con2 = len(up) > 3 and up[-2]['慢线'] > 0 and up[-3]['慢线'] > 0
        s1_con3 = len(macd) > 10 and macd[-1] < macd[-2]
        if s1_con1 and s1_con2 and s1_con3:
            v1 = "一卖"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_first_bs_V221216(c: CZSC, **kwargs):
    """MACD金叉死叉判断第一买卖点

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216"

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221216_一买_死叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221216_一买_金叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221216_一卖_金叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V221216_一卖_死叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    # cache_key = f"MACD"
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=300)

    v1 = "其他"
    v2 = "任意"
    if len(bars) >= 100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]
        macd = [x.cache[cache_key]['macd'] for x in bars]
        n_bars = bars[-10:]
        m_bars = bars[-100:-10]
        high_n = max([x.high for x in n_bars])
        low_n = min([x.low for x in n_bars])
        high_m = max([x.high for x in m_bars])
        low_m = min([x.low for x in m_bars])

        cross = fast_slow_cross(dif, dea)
        up = [x for x in cross if x['类型'] == "金叉" and x['距离'] > 5]
        dn = [x for x in cross if x['类型'] == "死叉" and x['距离'] > 5]

        b1_con1a = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['慢线'] < 0
        b1_con1b = len(cross) > 3 and cross[-1]['类型'] == '金叉' and dn[-1]['慢线'] < 0
        b1_con2 = len(dn) > 3 and dn[-2]['慢线'] < 0 and dn[-3]['慢线'] < 0
        b1_con3 = len(macd) > 10 and macd[-1] > macd[-2]
        if low_n < low_m and (b1_con1a or b1_con1b) and b1_con2 and b1_con3:
            v1 = "一买"

        s1_con1a = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['慢线'] > 0
        s1_con1b = len(cross) > 3 and cross[-1]['类型'] == '死叉' and up[-1]['慢线'] > 0
        s1_con2 = len(up) > 3 and up[-2]['慢线'] > 0 and up[-3]['慢线'] > 0
        s1_con3 = len(macd) > 10 and macd[-1] < macd[-2]
        if high_n > high_m and (s1_con1a or s1_con1b) and s1_con2 and s1_con3:
            v1 = "一卖"

        v2 = cross[-1]['类型']

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_second_bs_V221201(c: CZSC, **kwargs):
    """MACD金叉死叉判断第二买卖点

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201"

    **信号逻辑：**

    1. 最近一次交叉为死叉，DEA大于0，且前面两次死叉都在零轴下方，那么二买即将出现；二卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉中前两次都在零轴下方，后一次在零轴上方，那么二买即将出现；二卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9_BS2辅助V221201_二买_死叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS2辅助V221201_二买_金叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS2辅助V221201_二卖_死叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS2辅助V221201_二卖_金叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=350)[50:]

    v1 = "其他"
    v2 = "任意"
    if len(bars) >= 100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]
        macd = [x.cache[cache_key]['macd'] for x in bars]

        cross = fast_slow_cross(dif, dea)
        up = [x for x in cross if x['类型'] == "金叉" and x['距离'] > 5]
        dn = [x for x in cross if x['类型'] == "死叉" and x['距离'] > 5]

        b2_con1a = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['慢线'] > 0 and cross[-1]['距今'] > 5
        b2_con1b = len(cross) > 3 and cross[-1]['类型'] == '金叉' and dn[-1]['慢线'] > 0 and cross[-1]['距今'] < 5
        b2_con2 = len(dn) > 4 and dn[-3]['慢线'] < 0 and dn[-2]['慢线'] < 0
        b2_con3 = len(macd) > 10 and macd[-1] > macd[-2]
        if (b2_con1a or b2_con1b) and b2_con2 and b2_con3:
            v1 = "二买"

        s2_con1a = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['慢线'] < 0 and cross[-1]['距今'] > 5
        s2_con1b = len(cross) > 3 and cross[-1]['类型'] == '死叉' and up[-1]['慢线'] < 0 and cross[-1]['距今'] < 5
        s2_con2 = len(up) > 4 and up[-3]['慢线'] > 0 and up[-2]['慢线'] > 0
        s2_con3 = len(macd) > 10 and macd[-1] < macd[-2]
        if (s2_con1a or s2_con1b) and s2_con2 and s2_con3:
            v1 = "二卖"

        v2 = cross[-1]['类型']

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_xt_V221208(c: CZSC, **kwargs):
    """MACD形态信号

    参数模板："{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208"

    **信号逻辑：**

    1. MACD柱子的形态分类，具体见代码定义

    **信号列表：**

    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_绿抽脚_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_杀多棒_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_空翻多_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_红缩头_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_逼空棒_任意_任意_0')
    - Signal('15分钟_D1K#MACD12#26#9形态_BS辅助V221208_多翻空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=5)
    macd = [x.cache[cache_key]['macd'] for x in bars]

    v1 = "其他"
    if len(macd) == 5:
        if min(macd) > 0 and macd[-1] > macd[-2] < macd[-4]:
            v1 = "逼空棒"
        elif max(macd) < 0 and macd[-1] < macd[-2] > macd[-4]:
            v1 = "杀多棒"
        elif max(macd) < 0 and macd[-1] > macd[-2] < macd[-4]:
            v1 = "绿抽脚"
        elif min(macd) > 0 and macd[-1] < macd[-2] > macd[-4]:
            v1 = "红缩头"
        elif macd[-1] > 0 > macd[-3]:
            v1 = "空翻多"
        elif macd[-3] > 0 > macd[-1]:
            v1 = "多翻空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bc_V221201(c: CZSC, **kwargs):
    """MACD背驰辅助

    参数模板："{freq}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201"

    **信号逻辑：**

    1. 近n个最低价创近m个周期新低（以收盘价为准），macd柱子不创新低，这是底部背驰信号
    2. 若底背驰信号出现时 macd 为红柱，相当于进一步确认
    3. 顶部背驰反之

    **信号列表：**

    - Signal('15分钟_D1N3M50#MACD12#26#9_BCV221201_底部_绿柱_任意_0')
    - Signal('15分钟_D1N3M50#MACD12#26#9_BCV221201_底部_红柱_任意_0')
    - Signal('15分钟_D1N3M50#MACD12#26#9_BCV221201_顶部_红柱_任意_0')
    - Signal('15分钟_D1N3M50#MACD12#26#9_BCV221201_顶部_绿柱_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param n: 近期窗口大小
    :param m: 远期窗口大小
    :return: 信号识别结果
    """

    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 3))
    m = int(kwargs.get('m', 50))

    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=n + m)
    assert n >= 3, "近期窗口大小至少要大于3"

    v1 = "其他"
    v2 = "任意"
    if len(bars) == n + m:
        n_bars = bars[-n:]
        m_bars = bars[:m]
        assert len(n_bars) == n and len(m_bars) == m
        n_close = [x.close for x in n_bars]
        n_macd = [x.cache[cache_key]['macd'] for x in n_bars]
        m_close = [x.close for x in m_bars]
        m_macd = [x.cache[cache_key]['macd'] for x in m_bars]

        if n_macd[-1] > n_macd[-2] and min(n_close) < min(m_close) and min(n_macd) > min(m_macd):
            v1 = '底部'
        elif n_macd[-1] < n_macd[-2] and max(n_close) > max(m_close) and max(n_macd) < max(m_macd):
            v1 = '顶部'

        v2 = "红柱" if n_macd[-1] > 0 else "绿柱"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_change_V221105(c: CZSC, **kwargs) -> OrderedDict:
    """MACD颜色变化；贡献者：马鸣

    参数模板："{freq}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105"

    **信号逻辑：**

    从dik往前数n根k线对应的macd红绿柱子变换次数

    **信号列表：**

    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_1次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_2次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_3次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_4次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_5次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_6次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_7次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_8次_任意_任意_0')
    - Signal('15分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_9次_任意_任意_0')

    :param c: czsc对象
    :param di: 倒数第i根K线
    :param n: 从dik往前数n根k线
    :return:
    """

    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 55))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))

    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105".split('_')

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    dif = [x.cache[cache_key]['dif'] for x in bars]
    dea = [x.cache[cache_key]['dea'] for x in bars]

    cross = fast_slow_cross(dif, dea)
    # 过滤低级别信号抖动造成的金叉死叉(这个参数根据自身需要进行修改）
    re_cross = [i for i in cross if i['距离'] >= 2]

    if len(re_cross) == 0:
        num = 0
    else:
        cross_ = []
        for i in range(0, len(re_cross)):
            if len(cross_) >= 1 and re_cross[i]['类型'] == re_cross[i - 1]['类型']:
                # 不将上一个元素加入cross_
                del cross_[-1]

                # 我这里只重新计算了面积、快慢线的高低点，其他需要重新计算的参数各位可自行编写
                re_cross[i]['面积'] = re_cross[i - 1]['面积'] + re_cross[i]['面积']

                re_cross[i]['快线高点'] = max(re_cross[i - 1]['快线高点'], re_cross[i]['快线高点'])
                re_cross[i]['快线低点'] = min(re_cross[i - 1]['快线低点'], re_cross[i]['快线低点'])

                re_cross[i]['慢线高点'] = max(re_cross[i - 1]['慢线高点'], re_cross[i]['慢线高点'])
                re_cross[i]['慢线低点'] = min(re_cross[i - 1]['慢线低点'], re_cross[i]['慢线低点'])

                cross_.append(re_cross[i])
            else:
                cross_.append(re_cross[i])
        num = len(cross_)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"{num}次")


# MA信号计算函数
# ======================================================================================================================


def tas_ma_base_V221101(c: CZSC, **kwargs) -> OrderedDict:
    """MA 多空和方向信号

    参数模板："{freq}_D{di}{ma_type}#{timeperiod}_分类V221101"

    **信号逻辑：**

    1. close > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1SMA#5_分类V221101_空头_向下_任意_0')
    - Signal('15分钟_D1SMA#5_分类V221101_多头_向下_任意_0')
    - Signal('15分钟_D1SMA#5_分类V221101_多头_向上_任意_0')
    - Signal('15分钟_D1SMA#5_分类V221101_空头_向上_任意_0')

    :param c: CZSC对象
    :param kwargs:
        - di: 信号计算截止倒数第i根K线
        - ma_type: 均线类型，必须是 `ma_type_map` 中的 key
        - timeperiod: 均线计算周期
    :return:
    """
    di = int(kwargs.get('di', 1))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}{ma_type}#{timeperiod}_分类V221101".split('_')

    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "多头" if bars[-1].close >= bars[-1].cache[key] else "空头"
    v2 = "向上" if bars[-1].cache[key] >= bars[-2].cache[key] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_ma_base_V221203(c: CZSC, **kwargs) -> OrderedDict:
    """MA 多空和方向信号，加距离限制

    参数模板："{freq}_D{di}{ma_type}#{timeperiod}T{th}_分类V221203"

    **信号逻辑：**

    1. close > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下
    3. close 与 ma 的距离超过 th

    **信号列表：**

    - Signal('15分钟_D1SMA#5T100_分类V221203_空头_向下_靠近_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_多头_向下_靠近_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_多头_向上_靠近_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_空头_向上_靠近_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_空头_向下_远离_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_多头_向上_远离_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_多头_向下_远离_0')
    - Signal('15分钟_D1SMA#5T100_分类V221203_空头_向上_远离_0')

    :param c: CZSC对象
    :param kwargs:
        - di: 信号计算截止倒数第i根K线
        - ma_type: 均线类型，必须是 `ma_type_map` 中的 key
        - timeperiod: 均线计算周期
        - th: 距离阈值，单位 BP
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 5))
    th = int(kwargs.get('th', 100))
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}{ma_type}#{timeperiod}T{th}_分类V221203".split('_')

    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    c = bars[-1].close
    m = bars[-1].cache[key]
    v1 = "多头" if c >= m else "空头"
    v2 = "向上" if bars[-1].cache[key] >= bars[-2].cache[key] else "向下"
    v3 = "远离" if (abs(c - m) / m) * 10000 > th else "靠近"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def tas_ma_base_V230313(c: CZSC, **kwargs) -> OrderedDict:
    """单均线多空和方向辅助开平仓信号

    参数模板："{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313"

    **信号逻辑：**

    1. close > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下
    3. 加入 max_overlap 参数控制相同信号最大重叠次数

    **信号列表：**

    - Signal('15分钟_D1#SMA#5MO5_BS辅助V230313_看空_向下_任意_0')
    - Signal('15分钟_D1#SMA#5MO5_BS辅助V230313_看多_向下_任意_0')
    - Signal('15分钟_D1#SMA#5MO5_BS辅助V230313_看多_向上_任意_0')
    - Signal('15分钟_D1#SMA#5MO5_BS辅助V230313_看空_向上_任意_0')

    :param c: CZSC对象
    :param kwargs: 其他参数
        - ma_type: 均线类型，必须是 `ma_type_map` 中的 key
        - timeperiod: 均线计算周期
        - di: 信号计算截止倒数第i根K线
        - max_overlap: 相同信号最大重叠次数
    :return: 信号识别结果
    """
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 5))
    di = int(kwargs.get('di', 1))
    max_overlap = int(kwargs.get("max_overlap", 5))
    assert max_overlap >= 2, "max_overlap 必须大于等于2"
    freq = c.freq.value

    k1, k2, k3 = f"{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313".split('_')
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    v1 = "其他"
    bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap + 1)
    if len(bars) < max_overlap + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bars[-1].close >= bars[-1].cache[key] and not all(x.close > x.cache[key] for x in bars):
        v1 = "看多"
    elif bars[-1].close < bars[-1].cache[key] and not all(x.close < x.cache[key] for x in bars):
        v1 = "看空"
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    v2 = "向上" if bars[-1].cache[key] >= bars[-2].cache[key] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_ma_round_V221206(c: CZSC, **kwargs) -> OrderedDict:
    """笔端点在均线附近，贡献者：谌意勇

    参数模板："{freq}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206"

    **信号逻辑：**

    倒数第i笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近

    **信号列表：**

    - Signal('15分钟_D1TH10#碰SMA#60_BE辅助V221206_上碰_任意_任意_0')
    - Signal('15分钟_D1TH10#碰SMA#60_BE辅助V221206_下碰_任意_任意_0')

    :param c: CZSC对象
    :param di: 指定倒数第几笔
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param timeperiod: 均线计算周期
    :param th: 笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 10))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 5))
    k1, k2, k3 = f'{c.freq.value}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206'.split('_')
    v1 = "其他"

    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    if len(c.bi_list) > di + 3:
        last_bi = c.bi_list[-di]
        last_ma = np.mean([x.cache[key] for x in last_bi.fx_b.new_bars[1].raw_bars])
        bi_change = last_bi.power_price

        if last_bi.direction == Direction.Up and abs(last_bi.high - last_ma) / bi_change < th / 100:
            v1 = "上碰"
        elif last_bi.direction == Direction.Down and abs(last_bi.low - last_ma) / bi_change < th / 100:
            v1 = "下碰"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_double_ma_V221203(c: CZSC, **kwargs) -> OrderedDict:
    """双均线多空和强弱信号

    参数模板："{freq}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203"

    **信号逻辑：**

    1. ma1 > ma2，多头；反之，空头
    2. ma1 离开 ma2 的距离大于 th，强势；反之，弱势

    **信号列表：**

    - Signal('15分钟_D1T100#SMA#5#10_JX辅助V221203_空头_弱势_任意_0')
    - Signal('15分钟_D1T100#SMA#5#10_JX辅助V221203_多头_弱势_任意_0')
    - Signal('15分钟_D1T100#SMA#5#10_JX辅助V221203_多头_强势_任意_0')
    - Signal('15分钟_D1T100#SMA#5#10_JX辅助V221203_空头_强势_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param ma_seq: 快慢均线计算周期，快线在前
    :param th: ma1 相比 ma2 的距离阈值，单位 BP
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 100))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod1 = int(kwargs.get('timeperiod1', 5))
    timeperiod2 = int(kwargs.get('timeperiod2', 10))

    assert timeperiod1 < timeperiod2, "快线周期必须小于慢线周期"
    ma1 = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod1)
    ma2 = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod2)

    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    ma1v = bars[-1].cache[ma1]
    ma2v = bars[-1].cache[ma2]
    v1 = "多头" if ma1v >= ma2v else "空头"
    v2 = "强势" if (abs(ma1v - ma2v) / ma2v) * 10000 >= th else "弱势"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_double_ma_V230511(c: CZSC, **kwargs):
    """双均线金叉死叉后的反向信号

    参数模板："{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511"

    **信号逻辑：**

    1. t1周期均线上穿t2周期均线，且当前K线为大实体阴线，看多信号；
    2. t1周期均线下穿t2周期均线，且当前K线为大实体阳线，看空信号；

    **信号列表：**

    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看空_任意_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看多_第一个_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看多_任意_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看空_第一个_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - t1: 均线1周期
        - t2: 均线2周期
        - ma_type: 均线类型，支持：MA, EMA, WMA, DEMA, TEMA, TRIMA, KAMA, MAMA, T3
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    t1 = int(kwargs.get('t1', 5))
    t2 = int(kwargs.get('t2', 20))
    assert t1 < t2, "t1 必须小于 t2，否则无法判断金叉死叉"
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    cache_key1 = update_ma_cache(c, ma_type=ma_type, timeperiod=t1)
    cache_key2 = update_ma_cache(c, ma_type=ma_type, timeperiod=t2)

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511".split('_')
    v1, v2 = '其他', '任意'
    if len(c.bars_raw) < t2 + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=t2 + 1)
    mean_solid = np.mean([x.solid for x in bars])
    bar = c.bars_raw[-di]
    solid_th = max(bar.upper, bar.lower, mean_solid)

    if bar.solid < solid_th:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bar.cache[cache_key1] > bar.cache[cache_key2] and bar.close < bar.open:
        v1 = '看多'

        right_bars = []
        for x in bars[::-1]:
            if x.cache[cache_key1] > x.cache[cache_key2]:
                right_bars.append({'bar': x, '大实体阴线': x.solid > solid_th and x.close < x.open})
            else:
                break

        if len(right_bars) < t2 / 2 and sum([x['大实体阴线'] for x in right_bars]) == 1:
            v2 = '第一个'

    if bar.cache[cache_key1] < bar.cache[cache_key2] and bar.close > bar.open:
        v1 = '看空'

        right_bars = []
        for x in bars[::-1]:
            if x.cache[cache_key1] < x.cache[cache_key2]:
                right_bars.append({'bar': x, '大实体阳线': x.solid > solid_th and x.close > x.open})
            else:
                break

        if len(right_bars) < t2 / 2 and sum([x['大实体阳线'] for x in right_bars]) == 1:
            v2 = '第一个'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


# BOLL信号计算函数
# ======================================================================================================================


def tas_boll_power_V221112(c: CZSC, **kwargs):
    """BOLL指标强弱

    参数模板："{freq}_D{di}BOLL{timeperiod}_强弱V221112"

    **信号逻辑：**

    1. close大于中线，多头；反之，空头
    2. close超过轨3，超强，以此类推

    **信号列表：**

    - Signal('15分钟_D1BOLL20_强弱V221112_空头_强势_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_空头_弱势_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_空头_超强_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_多头_弱势_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_空头_极强_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_多头_强势_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_多头_超强_任意_0')
    - Signal('15分钟_D1BOLL20_强弱V221112_多头_极强_任意_0')

    :param c: CZSC对象
    :param kwargs: 其他参数
        - di: 信号计算截止倒数第i根K线
        - timeperiod: BOLL指标计算周期
    :return: s
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 20))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}BOLL{timeperiod}_强弱V221112".split("_")

    cache_key = update_boll_cache(c, **kwargs)
    if len(c.bars_raw) < di + 20:
        v1, v2 = '其他', '其他'

    else:
        last = c.bars_raw[-di]
        cache = last.cache[cache_key]

        latest_c = last.close
        m = cache['中线']
        u3, u2, u1 = cache['上轨3'], cache['上轨2'], cache['上轨1']
        l3, l2, l1 = cache['下轨3'], cache['下轨2'], cache['下轨1']

        v1 = "多头" if latest_c >= m else "空头"

        if latest_c >= u3 or latest_c <= l3:
            v2 = "极强"
        elif latest_c >= u2 or latest_c <= l2:
            v2 = "超强"
        elif latest_c >= u1 or latest_c <= l1:
            v2 = "强势"
        else:
            v2 = "弱势"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_boll_bc_V221118(c: CZSC, **kwargs):
    """BOLL背驰辅助

    参数模板："{freq}_D{di}N{n}M{m}L{line}#BOLL{timeperiod}_背驰V221118"

    **信号逻辑：**

    近n个最低价创近m个周期新低，近m个周期跌破下轨，近n个周期不破下轨，这是BOLL一买（底部背驰）信号，顶部背驰反之。

    **信号列表：**

    - Signal('15分钟_D1N3M10L3#BOLL20_背驰V221118_一卖_任意_任意_0')
    - Signal('15分钟_D1N3M10L3#BOLL20_背驰V221118_一买_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :param n: 近n个周期
    :param m: 近m个周期
    :param line: 选第几个上下轨
    :return:
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 3))
    m = int(kwargs.get('m', 10))
    line = int(kwargs.get('line', 3))
    timeperiod = int(kwargs.get('timeperiod', 20))
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}L{line}#BOLL{timeperiod}_背驰V221118".split('_')

    cache_key = update_boll_cache(c, **kwargs)
    bn = get_sub_elements(c.bars_raw, di=di, n=n)
    bm = get_sub_elements(c.bars_raw, di=di, n=m)

    d_c1 = min([x.low for x in bn]) <= min([x.low for x in bm])
    d_c2 = sum([x.close < x.cache[cache_key][f'下轨{line}'] for x in bm]) > 1
    d_c3 = sum([x.close < x.cache[cache_key][f'下轨{line}'] for x in bn]) == 0

    g_c1 = max([x.high for x in bn]) == max([x.high for x in bm])
    g_c2 = sum([x.close > x.cache[cache_key][f'上轨{line}'] for x in bm]) > 1
    g_c3 = sum([x.close > x.cache[cache_key][f'上轨{line}'] for x in bn]) == 0

    if d_c1 and d_c2 and d_c3:
        v1 = "一买"
    elif g_c1 and g_c2 and g_c3:
        v1 = "一卖"
    else:
        v1 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


# KDJ信号计算函数
# ======================================================================================================================
def update_kdj_cache(c: CZSC, **kwargs):
    """更新KDJ缓存

    :param c: CZSC对象
    :return:
    """
    fastk_period = int(kwargs.get('fastk_period', 9))
    slowk_period = int(kwargs.get('slowk_period', 3))
    slowd_period = int(kwargs.get('slowd_period', 3))
    cache_key = f"KDJ{fastk_period}#{slowk_period}#{slowd_period}"

    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    min_count = fastk_period + slowk_period
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 15:
        bars = c.bars_raw
        high = np.array([x.high for x in bars])
        low = np.array([x.low for x in bars])
        close = np.array([x.close for x in bars])

        k, d = ta.STOCH(
            high, low, close, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period
        )
        j = list(map(lambda x, y: 3 * x - 2 * y, k, d))

        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: {'k': k[i] if k[i] else 0, 'd': d[i] if d[i] else 0, 'j': j[i] if j[i] else 0}})
            c.bars_raw[i].cache = _c

    else:
        bars = c.bars_raw[-min_count - 10 :]
        high = np.array([x.high for x in bars])
        low = np.array([x.low for x in bars])
        close = np.array([x.close for x in bars])
        k, d = ta.STOCH(
            high, low, close, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period
        )
        j = list(map(lambda x, y: 3 * x - 2 * y, k, d))

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: {'k': k[-i], 'd': d[-i], 'j': j[-i]}})
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_kdj_base_V221101(c: CZSC, **kwargs) -> OrderedDict:
    """KDJ金叉死叉信号

    参数模板："{freq}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101"

    **信号逻辑：**

    1. J > K > D，多头；反之，空头
    2. J 值定方向

    **信号列表：**

    - Signal('15分钟_D1K#KDJ9#3#3_KDJ辅助V221101_空头_向下_任意_0')
    - Signal('15分钟_D1K#KDJ9#3#3_KDJ辅助V221101_多头_向上_任意_0')
    - Signal('15分钟_D1K#KDJ9#3#3_KDJ辅助V221101_多头_向下_任意_0')
    - Signal('15分钟_D1K#KDJ9#3#3_KDJ辅助V221101_空头_向上_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    fastk_period = int(kwargs.get('fastk_period', 9))
    slowk_period = int(kwargs.get('slowk_period', 3))
    slowd_period = int(kwargs.get('slowd_period', 3))

    cache_key = update_kdj_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    kdj = bars[-1].cache[cache_key]

    if kdj['j'] > kdj['k'] > kdj['d']:
        v1 = "多头"
    elif kdj['j'] < kdj['k'] < kdj['d']:
        v1 = "空头"
    else:
        v1 = "其他"

    v2 = "向上" if kdj['j'] >= bars[-2].cache[cache_key]['j'] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_kdj_evc_V221201(c: CZSC, **kwargs) -> OrderedDict:
    """KDJ极值计数信号, evc 是 extreme value counts 的首字母缩写

    参数模板："{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201"

    **信号逻辑：**

     1. K < th，记录一次多头信号，连续出现信号次数在 count_range 范围，则认为是有效多头信号；
     2. K > 100 - th, 记录一次空头信号，连续出现信号次数在 count_range 范围，则认为是有效空头信号

    **信号列表：**

    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_多头_C5_任意_0')
    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_多头_C6_任意_0')
    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_空头_C5_任意_0')
    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_空头_C6_任意_0')
    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_空头_C7_任意_0')
    - Signal('15分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_多头_C7_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param key: KDJ 值的名称，可以是 K， D， J
    :param th: 信号计算截止倒数第i根K线
    :param count_range: 信号计数范围
    :return:
    """
    di = int(kwargs.get('di', 1))
    key = kwargs.get('key', 'K')
    th = int(kwargs.get('th', 10))
    count_range = kwargs.get('count_range', (5, 8))

    fastk_period = int(kwargs.get('fastk_period', 9))
    slowk_period = int(kwargs.get('slowk_period', 3))
    slowd_period = int(kwargs.get('slowd_period', 3))

    key = key.upper()
    c1, c2 = count_range
    assert c2 > c1

    k1, k2, k3 = (
        f"{c.freq.value}_D{di}T{th}KDJ{fastk_period}#{slowk_period}"
        f"#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201".split('_')
    )
    bars = get_sub_elements(c.bars_raw, di=di, n=3 + c2)

    v1 = "其他"
    v2 = "任意"

    cache_key = update_kdj_cache(c, **kwargs)

    if len(bars) == 3 + c2:
        key = key.lower()
        long = [x.cache[cache_key][key] < th for x in bars]
        short = [x.cache[cache_key][key] > 100 - th for x in bars]
        lc = count_last_same(long) if long[-1] else 0
        sc = count_last_same(short) if short[-1] else 0

        if c2 > lc >= c1:
            v1 = "多头"
            v2 = f"C{lc}"

        if c2 > sc >= c1:
            assert v1 == '其他'
            v1 = "空头"
            v2 = f"C{sc}"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


# RSI信号计算函数
# ======================================================================================================================
def update_rsi_cache(c: CZSC, **kwargs):
    """更新RSI缓存

    相对强弱指数（RSI）是通过比较一段时期内的平均收盘涨数和平均收盘跌数来分析市场买沽盘的意向和实力，从而判断未来市场的走势。
    RSI在1978年6月由WellsWider创制。

    RSI = 100 × RS / (1 + RS) 或者 RSI=100－100÷(1+RS)
    RS = X天的平均上涨点数 / X天的平均下跌点数

    :param c: CZSC对象
    :return:
    """
    timeperiod = kwargs.get('timeperiod', 9)
    cache_key = f"RSI{timeperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        close = np.array([x.close for x in c.bars_raw])
        rsi = ta.RSI(close, timeperiod=timeperiod)

        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: rsi[i] if rsi[i] else 0})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10 :]])
        rsi = ta.RSI(close, timeperiod=timeperiod)

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: rsi[-i]})
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_rsi_base_V230227(c: CZSC, **kwargs) -> OrderedDict:
    """RSI超买超卖信号

    参数模板："{freq}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227"

    **信号逻辑：**

    在正常情况下，RSI指标都会在30-70的区间内波动。当6日RSI超过80时，表示市场已经处于超买区间。6日RSI达到90以上时，
    表示市场已经严重超买，股价极有可能已经达到阶段顶点。这时投资者应该果断卖出。当6日RSI下降到20时，表示市场已经处于
    超卖区间。6日RSI一旦下降到10以下，则表示市场已经严重超卖，股价极有可能会止跌回升，是很好的买入信号。

    **信号列表：**

    - Signal('15分钟_D1T20RSI6_RSI辅助V230227_超卖_向下_任意_0')
    - Signal('15分钟_D1T20RSI6_RSI辅助V230227_超卖_向上_任意_0')
    - Signal('15分钟_D1T20RSI6_RSI辅助V230227_超买_向上_任意_0')
    - Signal('15分钟_D1T20RSI6_RSI辅助V230227_超买_向下_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: RSI的计算周期
    :param th: RSI阈值
    :return: 信号识别结果
    """

    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 6))
    th = int(kwargs.get('th', 20))
    timeperiod = int(kwargs.get('timeperiod', 6))
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227".split("_")
    v1 = "其他"

    cache_key = update_rsi_cache(c, timeperiod=n)
    _bars = get_sub_elements(c.bars_raw, di=di, n=2)
    if len(_bars) != 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    rsi1 = _bars[-1].cache[cache_key]
    rsi2 = _bars[-2].cache[cache_key]

    if rsi1 <= th:
        v1 = "超卖"
    elif rsi1 >= 100 - th:
        v1 = "超买"
    else:
        v1 = "其他"

    v2 = "向上" if rsi1 >= rsi2 else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_first_bs_V230217(c: CZSC, **kwargs) -> OrderedDict:
    """均线结合K线形态的一买一卖辅助判断

    参数模板："{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS1辅助V230217"

    **信号逻辑：**

    1. 窗口N内的K线的最低点全部小于SMA5，且阴线数量占比超过60%，且最近三根K线创新低，最后一根K线收在SMA5上方，看多；
    2. 反之，看空。

    **信号列表：**

    - Signal('15分钟_D1N10#SMA#5_BS1辅助V230217_一买_任意_任意_0')
    - Signal('15分钟_D1N10#SMA#5_BS1辅助V230217_一卖_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
        - di: 倒数第几根K线，1表示最后一根K线
        - n: 窗口大小
        - ma_type: 均线类型
        - timeperiod: 均线周期
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 10))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 5))
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}#{ma_type}#{timeperiod}_BS1辅助V230217".split('_')
    v1 = '其他'
    if len(c.bars_raw) < n + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    sma = [x.cache[key] for x in _bars]
    low = [x.low for x in _bars]
    _open = [x.open for x in _bars]
    close = [x.close for x in _bars]
    high = [x.high for x in _bars]

    # 窗口N内的K线的最低点全部小于SMA5
    condition_1_down = np.all(np.array(sma) > np.array(low))
    condition_1_up = np.all(np.array(sma) < np.array(high))

    n1, m1 = 0, 0
    for i in range(len(low)):
        if close[i] < _open[i]:
            n1 += 1
        if close[i] > _open[i]:
            m1 += 1
    condition_2_down = True if (n1 / len(low)) > 0.6 else False
    condition_2_up = True if (m1 / len(low)) > 0.6 else False

    # 最近三根K线创新低
    condition_3_down = True if min(low[-3:]) < min(low[:-3]) else False
    condition_3_up = True if max(high[-3:]) > max(high[:-3]) else False

    # 最后一根K线收在MA5之上/下
    condition_4_down = True if close[-1] > sma[-1] else False
    condition_4_up = True if close[-1] < sma[-1] else False

    if condition_1_down and condition_2_down and condition_3_down and condition_4_down:
        v1 = '一买'
    elif condition_1_up and condition_2_up and condition_3_up and condition_4_up:
        v1 = '一卖'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


# 买卖点辅助判断
# ======================================================================================================================
def tas_second_bs_V230228(c: CZSC, **kwargs) -> OrderedDict:
    """均线结合K线形态的第二买卖点辅助判断

    参数模板："{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS2辅助V230228"

    **信号逻辑：**

    1. 二买辅助：1）MA20创新高且向上；2）近三根K线最低价跌破 MA20，且当前收盘价在MA20上
    2. 反之，二卖辅助。

    **信号列表：**

    - Signal('日线_D2N21#SMA#20_BS2辅助V230228_二卖_任意_任意_0')
    - Signal('日线_D2N21#SMA#20_BS2辅助V230228_二买_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线，1表示最后一根K线
    :param n: 窗口大小
    :param kwargs:
    :return: 信号识别结果
    """

    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 21))
    ma_type = kwargs.get('ma_type', 'SMA')
    timeperiod = int(kwargs.get('timeperiod', 20))
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}#{ma_type}#{timeperiod}_BS2辅助V230228".split('_')
    v1 = '其他'
    if len(c.bars_raw) < n + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    sma = [x.cache[key] for x in _bars]
    min_three = any([x.cache[key] > x.low for x in _bars[-3:]])
    max_three = any([x.high > x.cache[key] for x in _bars[-3:]])

    if max(sma) == sma[-1] > sma[-2] and _bars[-1].close > sma[-1] and min_three:
        v1 = '二买'
    elif min(sma) == sma[-1] < sma[-2] and _bars[-1].close < sma[-1] and max_three:
        v1 = '二卖'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_second_bs_V230303(c: CZSC, **kwargs):
    """利用笔和均线辅助二买信号生成

    参数模板："{freq}_D{di}{ma_type}#{timeperiod}_BS2辅助V230303"

    **信号逻辑：**

    1. 最近5笔创新低，且最近一向下笔最低点跌破中期均线，且中期均线向上，二买信号；
    2. 反之，二卖信号。

    **信号列表**

    - Signal('15分钟_D1SMA#30_BS2辅助V230303_二卖_任意_任意_0')
    - Signal('15分钟_D1SMA#30_BS2辅助V230303_二买_任意_任意_0')

    :param c: CZSC对象
    :param di: 指定倒数第几笔
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param timeperiod: 均线计算周期
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 30))

    k1, k2, k3 = f'{c.freq.value}_D{di}{ma_type}#{timeperiod}_BS2辅助V230303'.split('_')
    v1 = '其他'

    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    if len(c.bi_list) < di + 13:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bi_list = get_sub_elements(c.bi_list, di=di, n=13)
    last_bi: BI = _bi_list[-1]
    first_bar: RawBar = last_bi.raw_bars[0]
    last_bar: RawBar = last_bi.raw_bars[-1]

    if (
        last_bi.direction == Direction.Down
        and last_bar.low < last_bar.cache[key]
        and min([x.low for x in _bi_list[-5:]]) == min([x.low for x in _bi_list])
        and first_bar.cache[key] < last_bar.cache[key]
    ):
        v1 = "二买"

    if (
        last_bi.direction == Direction.Up
        and last_bar.high > last_bar.cache[key]
        and max([x.high for x in _bi_list[-5:]]) == max([x.high for x in _bi_list])
        and first_bar.cache[key] > last_bar.cache[key]
    ):
        v1 = "二卖"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_hlma_V230301(c: CZSC, **kwargs) -> OrderedDict:
    """HMA 多空信号，贡献者：琅盎

    参数模板："{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301"

    **信号逻辑：**

    1. 收盘价大于HMA and 上一根K线的收盘价小于均线
    2. 收盘价小于LMA and 上一根K线的收盘价大于均线

    **信号列表：**

    - Signal('15分钟_D1#SMA#3HLMA_BS辅助V230301_看多_任意_任意_0')
    - Signal('15分钟_D1#SMA#3HLMA_BS辅助V230301_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 其他参数
        - di: 信号计算截止倒数第i根K线
        - ma_type: 均线类型，必须是 ma_type_map 中的 key
        - timeperiod: 均线周期
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    ma_type = kwargs.get("ma_type", "SMA").upper()
    timeperiod = int(kwargs.get("timeperiod", 3))
    freq = c.freq.value

    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=timeperiod)

    hma = np.mean([x.high for x in _bars])
    lma = np.mean([x.low for x in _bars])

    if _bars[-1].close > hma and _bars[-2].close <= _bars[-2].cache[key]:
        v1 = "看多"
    elif _bars[-1].close < lma and _bars[-2].close >= _bars[-2].cache[key]:
        v1 = "看空"
    else:
        v1 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_boll_cc_V230312(c: CZSC, **kwargs) -> OrderedDict:
    """多空进出场信号，贡献者：琅盎

    参数模板："{freq}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312"

    **信号逻辑：**

    1. 收盘在布林线上轨下方，且跌破中线一定距离，看空；反之，看多。

    **信号列表：**

    - Signal('15分钟_D1BOLL20S20SP400_BS辅助V230312_看多_任意_任意_0')
    - Signal('15分钟_D1BOLL20S20SP400_BS辅助V230312_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param sp: 停盈点数，单位：BP；1BP = 0.01%
    :return:
    """

    di = int(kwargs.get('di', 1))
    sp = int(kwargs.get('sp', 400))
    timeperiod = int(kwargs.get('timeperiod', 20))
    nbdev = int(kwargs.get('nbdev', 20))  # 标准差倍数，计算时除以10，如20表示2.0，即2倍标准差
    k1, k2, k3 = f"{c.freq.value}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312".split('_')

    key = update_boll_cache_V230228(c, **kwargs)
    _bars = get_sub_elements(c.bars_raw, di=di, n=6)

    bias = (_bars[-1].close / _bars[-1].cache[key]['中线'] - 1) * 10000

    v1 = "其他"
    if _bars[-1].close < _bars[-1].cache[key]['上轨'] and bias < -sp:
        v1 = "看空"

    elif _bars[-1].close > _bars[-1].cache[key]['下轨'] and bias > sp:
        v1 = "看多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230312(c: CZSC, **kwargs):
    """MACD辅助一买一卖信号

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312"

    **信号逻辑：**

    1. 看多，最近一笔新低，且该笔的高点对应一个三卖，MACD向上；
    2. 反之，看空，最近一笔新高，且该笔的低点对应一个三买，MACD向下。

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230312_看多_任意_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230312_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i笔
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312".split('_')
    v1 = "其他"

    cache_key = update_macd_cache(c, **kwargs)
    bis = get_sub_elements(c.bi_list, di=di, n=7)
    if len(bis) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_fx: FX = bis[-1].fx_b
    bi_low = max([x.low for x in bis[:-1] if x.direction == Direction.Up])
    if (
        bis[-1].direction == Direction.Down
        and bis[-1].low == min([x.low for x in bis])
        and bis[-1].high < bi_low
        and last_fx.raw_bars[-1].cache[cache_key]['macd'] > last_fx.raw_bars[0].cache[cache_key]['macd']
    ):
        v1 = "看多"

    bi_high = min([x.high for x in bis[:-1] if x.direction == Direction.Down])
    if (
        bis[-1].direction == Direction.Up
        and bis[-1].high == max([x.high for x in bis])
        and bis[-1].low > bi_high
        and last_fx.raw_bars[-1].cache[cache_key]['macd'] < last_fx.raw_bars[0].cache[cache_key]['macd']
    ):
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230313(c: CZSC, **kwargs):
    """MACD红绿柱判断第一买卖点，贡献者：琅盎

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313"

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230313_一买_死叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230313_一买_金叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230313_一卖_金叉_任意_0')
    - Signal('15分钟_D1MACD12#26#9_BS1辅助V230313_一卖_死叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=300)

    v1 = "其他"
    v2 = "任意"
    if len(bars) <= 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    dif, dea, macd = [], [], []
    cache_key = update_macd_cache(c, **kwargs)
    for x in bars:
        dif.append(x.cache[cache_key]['dif'])
        dea.append(x.cache[cache_key]['dea'])
        macd.append(x.cache[cache_key]['macd'])

    n_bars = bars[-10:]
    m_bars = bars[-100:-10]
    high_n = max([x.high for x in n_bars])
    low_n = min([x.low for x in n_bars])
    high_m = max([x.high for x in m_bars])
    low_m = min([x.low for x in m_bars])

    cross = fast_slow_cross(dif, dea)
    up = [x for x in cross if x['类型'] == "金叉"]
    dn = [x for x in cross if x['类型'] == "死叉"]

    b1_con1a = (
        len(cross) > 3
        and cross[-1]['类型'] == '死叉'
        and cross[-1]['面积'] < cross[-2]['面积']
        or cross[-1]['面积'] < cross[-3]['面积']
    )
    b1_con1b = (
        len(cross) > 3
        and cross[-1]['类型'] == '金叉'
        and cross[-1]['面积'] > cross[-2]['面积']
        or cross[-1]['面积'] < cross[-3]['面积']
    )
    b1_con2 = len(dn) > 3 and dn[-2]['面积'] < dn[-3]['面积']  # 三次死叉面积逐渐减小
    b1_con3 = len(macd) > 10 and macd[-1] > macd[-2]  # MACD向上
    if low_n < low_m and (b1_con1a or b1_con1b) and b1_con2 and b1_con3:
        v1 = "一买"

    s1_con1a = (
        len(cross) > 3
        and cross[-1]['类型'] == '金叉'
        and cross[-1]['面积'] > cross[-2]['面积']
        or cross[-1]['面积'] > cross[-3]['面积']
    )
    s1_con1b = (
        len(cross) > 3
        and cross[-1]['类型'] == '死叉'
        and cross[-1]['面积'] < cross[-2]['面积']
        or cross[-1]['面积'] < cross[-3]['面积']
    )
    s1_con2 = len(up) > 3 and up[-2]['面积'] > up[-3]['面积']
    s1_con3 = len(macd) > 10 and macd[-1] < macd[-2]
    if high_n > high_m and (s1_con1a or s1_con1b) and s1_con2 and s1_con3:
        v1 = "一卖"

    v2 = cross[-1]['类型']
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_base_V230320(c: CZSC, **kwargs) -> OrderedDict:
    """MACD|DIF|DEA 多空和方向信号，支持 max_overlap 参数

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320"

    **信号逻辑：**

    1. dik 对应的MACD值大于0，多头；反之，空头；最大允许重叠 max_overlap 个K线
    2. dik 的MACD值大于上一个值，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_多头_向上_任意_0')
    - Signal('15分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_多头_向下_任意_0')
    - Signal('15分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_空头_向下_任意_0')
    - Signal('15分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_空头_向上_任意_0')

    :param c: CZSC对象
    :param kwargs: 其他参数
        - max_overlap: 最大允许重叠的K线数
        - di: 倒数第i根K线
        - key: 指定使用哪个Key来计算，可选值 [macd, dif, dea]
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    key = kwargs.get("key", "macd").upper()
    fastperiod = int(kwargs.get('fastperiod', 12))
    slowperiod = int(kwargs.get('slowperiod', 26))
    signalperiod = int(kwargs.get('signalperiod', 9))
    max_overlap = int(kwargs.get("max_overlap", 3))
    cache_key = update_macd_cache(c, **kwargs)
    assert key.lower() in ['macd', 'dif', 'dea']
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 5 + di + max_overlap:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap + 1)
    value = [x.cache[cache_key][key.lower()] for x in bars]
    if value[-1] > 0 and any([x < 0 for x in value[:-1]]):
        v1 = "多头"
    elif value[-1] < 0 and any([x > 0 for x in value[:-1]]):
        v1 = "空头"
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    v2 = "向上" if value[-1] >= value[-2] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def update_cci_cache(c: CZSC, **kwargs):
    """更新CCI缓存

    CCI = (TP - MA) / MD / 0.015; 其中，

    - TP=(最高价+最低价+收盘价)÷3;
    - MA=最近N日收盘价的累计之和÷N;
    - MD=最近N日（MA－收盘价）的累计之和÷N;
    - 0.015为计算系数，N为计算周期

    :param c: CZSC对象
    :return:
    """
    timeperiod = int(kwargs.get('timeperiod', 14))
    cache_key = f"CCI{timeperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        bars = c.bars_raw
    else:
        # 增量更新最近5个K线缓存
        bars = c.bars_raw[-timeperiod - 10 :]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    close = np.array([x.close for x in bars])
    cci = ta.CCI(high, low, close, timeperiod=timeperiod)

    for i in range(len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            _c.update({cache_key: cci[i] if cci[i] else 0})
            bars[i].cache = _c

    return cache_key


def tas_cci_base_V230402(c: CZSC, **kwargs) -> OrderedDict:
    """CCI基础信号

    参数模板："{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402"

    **信号逻辑：**

     1. CCI连续大于100的次数大于 min_count, 小于max_count，看空；反之，看多。

    **信号列表：**

    - Signal('60分钟_D1CCI14#3#6_BS辅助V230402_空头_任意_任意_0')
    - Signal('60分钟_D1CCI14#3#6_BS辅助V230402_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - di: int, 默认1，倒数第几根K线
        - timeperiod: int, 默认14，计算CCI的周期
        - min_count: int, 默认3，CCI连续大于100的次数
        - max_count: int, 默认min_count+3，CCI连续大于100的次数
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    min_count = int(kwargs.get('min_count', 3))
    max_count = int(kwargs.get('max_count', min_count + 3))
    assert min_count < max_count, "min_count 必须小于 max_count"
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402".split("_")
    v1 = "其他"

    cache_key = update_cci_cache(c, timeperiod=timeperiod)
    bars = get_sub_elements(c.bars_raw, di=di, n=max_count + 1)
    if len(bars) != max_count + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    cci = [x.cache[cache_key] for x in bars]

    long = [x > 100 for x in cci]
    short = [x < -100 for x in cci]
    lc = count_last_same(long) if long[-1] else 0
    sc = count_last_same(short) if short[-1] else 0

    if max_count > lc >= min_count:
        v1 = "多头"
    if max_count > sc >= min_count:
        v1 = "空头"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_kdj_evc_V230401(c: CZSC, **kwargs) -> OrderedDict:
    """KDJ极值计数信号, evc 是 extreme value counts 的首字母缩写

    参数模板："{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{min_count}#{max_count}_BS辅助V230401"

    **信号逻辑：**

     1. K < th，记录一次多头信号，连续出现信号次数在 count_range 范围，则认为是有效多头信号；
     2. K > 100 - th, 记录一次空头信号，连续出现信号次数在 count_range 范围，则认为是有效空头信号

    **信号列表：**

    - Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_空头_任意_任意_0')
    - Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - di: 信号计算截止倒数第i根K线
        - key: KDJ 值的名称，可以是 K， D， J
        - th: 信号计算截止倒数第i根K线
        - min_count: 连续出现信号次数的最小值
        - max_count: 连续出现信号次数的最大值
    :return:
    """
    di = int(kwargs.get("di", 1))
    key = kwargs.get("key", "K")
    th = int(kwargs.get("th", 10))
    min_count = int(kwargs.get("min_count", 5))
    max_count = int(kwargs.get("max_count", min_count + 3))
    freq = c.freq.value
    key = key.upper()
    assert min_count < max_count, "min_count 必须小于 max_count"
    assert key in ['K', 'D', 'J'], "key 必须是 K， D， J 中的一个"
    assert 0 < th < 100, "th 必须在 0 到 100 之间"
    cache_key = update_kdj_cache(c, **kwargs)

    k1, k2, k3 = f"{freq}_D{di}T{th}{cache_key}#{key}值突破{min_count}#{max_count}_BS辅助V230401".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + max_count + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=3 + max_count)
    key = key.lower()
    long = [x.cache[cache_key][key] < th for x in bars]
    short = [x.cache[cache_key][key] > 100 - th for x in bars]
    lc = count_last_same(long) if long[-1] else 0
    sc = count_last_same(short) if short[-1] else 0

    if max_count > lc >= min_count:
        v1 = "多头"

    if max_count > sc >= min_count:
        assert v1 == '其他'
        v1 = "空头"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def update_atr_cache(c: CZSC, **kwargs):
    """更新ATR缓存

    平均真实波幅（ATR）的计算方法：

    1、当前交易日的最高价与最低价间的波幅
    2、前一交易日收盘价与当个交易日最高价间的波幅
    3、前一交易日收盘价与当个交易日最低价间的波幅

    今日振幅、今日最高与昨收差价，今日最低与昨收差价中的最大值，为真实波幅，在有了真实波幅后，就可以利用一段时间的平均值计算ATR了。

    :param c: CZSC对象
    :return:
    """
    timeperiod = int(kwargs.get('timeperiod', 14))
    cache_key = f"ATR{timeperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        bars = c.bars_raw
    else:
        # 增量更新最近5个K线缓存
        bars = c.bars_raw[-timeperiod - 80 :]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    close = np.array([x.close for x in bars])
    atr = ta.ATR(high, low, close, timeperiod=timeperiod)

    for i in range(len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            _c.update({cache_key: atr[i] if atr[i] else 0})
            bars[i].cache = _c

    return cache_key


def tas_atr_break_V230424(c: CZSC, **kwargs):
    """ATR突破

    参数模板："{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424"

    **信号逻辑：**

    1. 以ATR为基础的通道突破；
    2. close 向上突破 LL + th * ATR, 看多；
    3. close 向下突破 HH - th * ATR，看空

    **信号列表：**

    - Signal('日线_D1ATR5T30突破_BS辅助V230424_看空_任意_任意_0')
    - Signal('日线_D1ATR5T30突破_BS辅助V230424_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - timeperiod: ATR的计算周期
        - th: ATR突破的倍数，根据经验优化
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 30))
    timeperiod = int(kwargs.get('timeperiod', 5))
    cache_key = update_atr_cache(c, timeperiod=timeperiod)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=timeperiod)
    HH = max([i.high for i in bars])
    LL = min([i.low for i in bars])
    bar = c.bars_raw[-di]
    atr = c.bars_raw[-di].cache[cache_key]

    th = th / 10
    if HH - th * atr > bar.close > LL + th * atr:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    if bar.close > LL + th * atr:
        v1 = '看多'
    elif bar.close < HH - th * atr:
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def update_sar_cache(c: CZSC, **kwargs):
    """更新SAR缓存

    SAR是止损转向操作点指标的简称，英文名称为“Stop and Reverse"，缩写为SAR，一般称为抛物线指标。
    该指标是由美国技术分析大师威尔斯·威尔德所创造出来的。

    详细介绍：

    - https://zhuanlan.zhihu.com/p/210169446
    - https://www.investopedia.com/terms/p/parabolicindicator.asp

    :param c: CZSC对象
    :return:
    """
    cache_key = "SAR"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < 50:
        # 初始化缓存
        bars = c.bars_raw
    else:
        # 增量更新最近5个K线缓存
        bars = c.bars_raw[-120:]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    sar = ta.SAR(high, low)

    for i in range(len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            _c.update({cache_key: sar[i] if sar[i] else 0})
            bars[i].cache = _c

    return cache_key


def tas_sar_base_V230425(c: CZSC, **kwargs):
    """SAR基础信号

    参数模板："{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425"

    **信号逻辑：**

    1. 收盘价升破SAR，且前面MO根K中有任意一根K线的收盘价都低于SAR，看多信号
    2. 收盘价跌破SAR，且前面MO根K中有任意一根K线的收盘价都高于SAR，看空信号

    **信号列表：**

    - Signal('日线_D1MO5SAR_BS辅助V230425_看空_任意_任意_0')
    - Signal('日线_D1MO5SAR_BS辅助V230425_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - max_overlap: 信号最大重叠K线数
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    max_overlap = int(kwargs.get('max_overlap', 5))
    cache_key = update_sar_cache(c)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap)
    bar = c.bars_raw[-di]
    sar = c.bars_raw[-di].cache[cache_key]
    if bar.close > sar and any([x.close < x.cache[cache_key] for x in bars]):
        v1 = '看多'
    elif bar.close < sar and any([x.close > x.cache[cache_key] for x in bars]):
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_ma_system_V230513(c: CZSC, **kwargs) -> OrderedDict:
    """均线系统多空排列

    参数模板："{freq}_D{di}SMA{ma_seq}_均线系统V230513"

     **信号逻辑：**

    1. 5日均线 > 10日均线 > 20日均线，多头排列，以此类推；
    2. 5日均线 < 10日均线 < 20日均线，空头排列，以此类推；

     **信号列表：**

    - Signal('60分钟_D1SMA5#10#20_均线系统V230513_多头排列_任意_任意_0')
    - Signal('60分钟_D1SMA5#10#20_均线系统V230513_空头排列_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    ma_seq = kwargs.get('ma_seq', "5#10#20")
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}SMA{ma_seq}_均线系统V230513".split('_')
    v1 = '其他'
    ma_seq = [int(x) for x in ma_seq.split('#')]
    for ma in ma_seq:
        update_ma_cache(c, ma_type="SMA", timeperiod=ma)

    if len(c.bars_raw) < max(ma_seq) + di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    ma_val = [c.bars_raw[-di].cache[f'SMA#{x}'] for x in ma_seq]
    if all([x > y for x, y in zip(ma_val[:-1], ma_val[1:])]):
        v1 = '多头排列'
    if all([x < y for x, y in zip(ma_val[:-1], ma_val[1:])]):
        v1 = '空头排列'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230411(c: CZSC, **kwargs) -> OrderedDict:
    """基于MACD DIF的笔背驰判断信号

    参数模板："{freq}_D{di}T{tha}#{thb}#{thc}_BS1辅助V230411"

    **信号逻辑：**

    tha, thb, thc 分别为阈值，取值范围为 0 ~ 10000

    取5笔，从远到近分别记为 1、2、3、4、5，如果满足以下条件，则判断为顶背驰，反之为底背弛：

    1. 5向上，1~3的累计涨幅超过阈值tha，且3顶部的dif值大于1顶部dif值；
    2. 5的顶部相比于3的顶部的涨幅超过阈值-thb，且相应dif值的变化率小于阈值-thc；

    **信号列表：**

    - Signal('15分钟_D1T100#10#30_BS1辅助V230411_底背驰_任意_任意_0')
    - Signal('15分钟_D1T100#10#30_BS1辅助V230411_顶背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - di: 信号计算截止倒数第i根K线
        - tha: 前三笔的累计涨跌超过阈值tha，单位：BP，表示万分之一
        - thb: 第3笔相比第1笔的顶的涨跌幅阈值thb，单位：BP，表示万分之一
        - thc: 第5笔相比第3笔的DIF值的变化率阈值thc，单位：BP，表示万分之一

    :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    tha = int(kwargs.get("tha", 30))
    thb = int(kwargs.get("thb", 5))
    thc = int(kwargs.get("thc", 30))
    freq = c.freq.value
    assert 0 < tha < 10000, "tha 必须在 0 到 10000 之间"
    assert 0 < thb < 10000, "thb 必须在 0 到 10000 之间"
    assert 0 < thc < 10000, "thc 必须在 0 到 10000 之间"

    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}T{tha}#{thb}#{thc}_BS1辅助V230411".split('_')
    v1 = "其他"
    if len(c.bi_list) <= di + 7 or len(c.bars_ubi) > 9:
        # 笔数不够，或者当下未完成笔已经延伸超过9根K线，不计算
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bi1, bi2, bi3, bi4, bi5 = get_sub_elements(c.bi_list, di=di, n=5)
    # 第一个bar要有macd结果
    if np.isnan(bi1.raw_bars[0].cache[cache_key]['dif']):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bi5.direction == Direction.Up:
        bi1_dif = max([x.cache[cache_key]['dif'] for x in bi1.fx_b.raw_bars])
        bi3_dif = max([x.cache[cache_key]['dif'] for x in bi3.fx_b.raw_bars])
        bi5_dif = max([x.cache[cache_key]['dif'] for x in bi5.fx_b.raw_bars])

        # 前三笔累计涨幅超过阈值tha
        cond1 = ((bi3.high - bi1.low) / bi1.low) * 10000 > tha

        # 第二个向上笔的顶所对应的DIF值，要高于第一个向上笔的顶所对应的DIF值
        cond2 = bi3_dif > bi1_dif

        # 第三个向上笔的顶相比第二个向上笔的顶的涨幅超过阈值thb
        cond3 = ((bi5.high - bi3.high) / bi3.high) * 10000 > -thb

        # 第三个向上笔的顶相比第二个向上笔的顶的DIF值的变化率小于阈值thc
        cond4 = ((bi5_dif - bi3_dif) / bi3_dif) * 10000 < -thc

        if cond1 and cond2 and cond3 and cond4:
            v1 = "顶背驰"

    elif bi5.direction == Direction.Down:
        bi1_dif = min([x.cache[cache_key]['dif'] for x in bi1.fx_b.raw_bars])
        bi3_dif = min([x.cache[cache_key]['dif'] for x in bi3.fx_b.raw_bars])
        bi5_dif = min([x.cache[cache_key]['dif'] for x in bi5.fx_b.raw_bars])

        # 前三笔累计跌幅超过阈值tha
        cond1 = ((bi3.low - bi1.high) / bi1.high) * 10000 < -tha

        # 第二个向下笔的底所对应的DIF值，要小于第一个向下笔的底所对应的DIF值
        cond2 = bi3_dif < bi1_dif

        # 第三个向下笔的底相比第二个向下笔的底的跌幅小于thb
        cond3 = ((bi5.low - bi3.low) / bi3.low) * 10000 < thb

        # 第三个向下笔的底相比第二个向下笔的底的DIF值的变化率大于thc
        cond4 = ((bi5_dif - bi3_dif) / bi3_dif) * 10000 > thc

        if cond1 and cond2 and cond3 and cond4:
            v1 = "底背驰"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230412(c: CZSC, **kwargs) -> OrderedDict:
    """基于MACD DIF的笔背驰判断信号

    参数模板："{freq}_D{di}T{tha}#{thb}_BS1辅助V230412"

    **信号逻辑：**

    取5笔，从远到近分别记为 1、2、3、4、5，如果满足以下条件，则判断为顶背驰，反之为底背弛：

    1. 5向上，1~3的累计涨幅超过阈值tha，且3顶部的dif值大于1顶部dif值；
    2. 5的顶部相比于3的顶部的涨幅超过阈值thb，且5顶部的dif值小于3顶部dif值；

    **信号列表：**

    - Signal('15分钟_D1T100#10_BS1辅助V230412_底背驰_任意_任意_0')
    - Signal('15分钟_D1T100#10_BS1辅助V230412_顶背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - di: 信号计算截止倒数第i根K线
        - tha: 前三笔的累计涨跌超过阈值tha
        - thb: 第三笔相比第二个向上笔的顶的涨幅超过阈值thb

    :return:
    """
    di = int(kwargs.get("di", 1))
    tha = int(kwargs.get("tha", 100))
    thb = int(kwargs.get("thb", 10))
    freq = c.freq.value

    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}T{tha}#{thb}_BS1辅助V230412".split('_')
    v1 = "其他"
    if len(c.bi_list) <= di + 7 or len(c.bars_ubi) > 9:
        # 笔数不够，或者当下未完成笔已经延伸超过9根K线，不计算
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bi1, bi2, bi3, bi4, bi5 = get_sub_elements(c.bi_list, di=di, n=5)
    # 第一个bar要有macd结果
    if np.isnan(bi1.raw_bars[0].cache[cache_key]['dif']):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bi5.direction == Direction.Up:
        bi1_dif = max([x.cache[cache_key]['dif'] for x in bi1.fx_b.raw_bars])
        bi3_dif = max([x.cache[cache_key]['dif'] for x in bi3.fx_b.raw_bars])
        bi5_dif = max([x.cache[cache_key]['dif'] for x in bi5.fx_b.raw_bars])

        # 前三笔累计涨幅超过阈值tha
        cond1 = ((bi3.high - bi1.low) / bi1.low) * 10000 > tha

        # 5、3、1笔的dif值，3的最大
        cond2 = bi5_dif < bi3_dif > bi1_dif

        # 第三个向上笔的顶相比第二个向上笔的顶的涨幅超过阈值thb
        cond3 = ((bi5.high - bi3.high) / bi3.high) * 10000 > -thb

        if cond1 and cond2 and cond3:
            v1 = "顶背驰"

    elif bi5.direction == Direction.Down:
        bi1_dif = min([x.cache[cache_key]['dif'] for x in bi1.fx_b.raw_bars])
        bi3_dif = min([x.cache[cache_key]['dif'] for x in bi3.fx_b.raw_bars])
        bi5_dif = min([x.cache[cache_key]['dif'] for x in bi5.fx_b.raw_bars])

        # 前三笔累计跌幅超过阈值tha
        cond1 = ((bi3.low - bi1.high) / bi1.high) * 10000 < -tha

        # 5、3、1笔的dif值，3的最小
        cond2 = bi5_dif > bi3_dif < bi1_dif

        # 第三个向下笔的底相比第二个向下笔的底的跌幅超过阈值-thb
        cond3 = ((bi5.low - bi3.low) / bi3.low) * 10000 < thb

        if cond1 and cond2 and cond3:
            v1 = "底背驰"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_accelerate_V230531(c: CZSC, **kwargs) -> OrderedDict:
    """BOLL辅助判断加速行情

    参数模板："{freq}_D{di}N{n}T{t}_BOLL加速V230531"

     **信号逻辑：**

    最近N根K线全部在中轨上方，上轨累计涨幅大于中轨2倍以上，多头加速，反之空头加速。

     **信号列表：**

    - Signal('60分钟_D1N20T20_BOLL加速V230531_空头加速_未破下轨_任意_0')
    - Signal('60分钟_D1N20T20_BOLL加速V230531_空头加速_跌破下轨_任意_0')
    - Signal('60分钟_D1N20T20_BOLL加速V230531_多头加速_升破上轨_任意_0')
    - Signal('60分钟_D1N20T20_BOLL加速V230531_多头加速_未破上轨_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - di: 倒数第几根K线
        - n: 取截止dik的前n根K线
        - t: 阈值，上下轨变化率超过中轨变化率的 t / 10 倍，默认20，即上下轨变化率超过中轨变化率的2倍

    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 20))
    t = int(kwargs.get('t', 20))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}T{t}_BOLL加速V230531".split('_')
    v1, v2 = '其他', '其他'
    cache_key = update_boll_cache_V230228(c, timeperiod=20, nbdev=20)

    if len(c.bars_raw) < 40:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    mid_zdf = bars[-1].cache[cache_key]['中线'] / bars[0].cache[cache_key]['中线'] - 1
    up_zdf = bars[-1].cache[cache_key]['上轨'] / bars[0].cache[cache_key]['上轨'] - 1
    down_zdf = bars[-1].cache[cache_key]['下轨'] / bars[0].cache[cache_key]['下轨'] - 1
    last_bar = bars[-1]

    if all([x.close > x.cache[cache_key]['中线'] for x in bars]) and up_zdf > t / 10 * mid_zdf > 0:
        v1 = '多头加速'
        v2 = '升破上轨' if last_bar.cache[cache_key]['上轨'] < last_bar.high else '未破上轨'

    if all([x.close < x.cache[cache_key]['中线'] for x in bars]) and down_zdf < t / 10 * mid_zdf < 0:
        v1 = '空头加速'
        v2 = '跌破下轨' if last_bar.cache[cache_key]['下轨'] > last_bar.low else '未破下轨'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_ma_cohere_V230512(c: CZSC, **kwargs) -> OrderedDict:
    """均线系统粘合/扩散状态

    参数模板："{freq}_D{di}SMA{ma_seq}_均线系统V230512"

     **信号逻辑：**

    1. 计算最近100根K线中，均线系统最大值与最小值的差异；取前80根K线，计算其标准差；
    1. 粘合：最近20根K线中，均线系统最大值与最小值的差异小于0.5倍标准差的数量超过16根
    2. 扩散：最近20根K线中，均线系统最大值与最小值的差异大于1.0倍标准差的数量超过16根

     **信号列表：**

    - Signal('60分钟_D1SMA5#13#21#34#55_均线系统V230512_扩散_任意_任意_0')
    - Signal('60分钟_D1SMA5#13#21#34#55_均线系统V230512_粘合_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    ma_seq = kwargs.get('ma_seq', "5#13#21#34#55")  # 均线系统参数，以#分隔
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}SMA{ma_seq}_均线系统V230512".split('_')
    v1 = '其他'
    ma_seq = [int(x) for x in ma_seq.split('#')]
    for ma in ma_seq:
        update_ma_cache(c, ma_type="SMA", timeperiod=ma)

    if len(c.bars_raw) < max(ma_seq) + di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    ret_seq = []
    for bar in get_sub_elements(c.bars_raw, di=di, n=100):
        ma_val = [bar.cache[f'SMA#{x}'] for x in ma_seq]
        ret_seq.append(max(ma_val) / min(ma_val) - 1)

    ret_std = np.std(ret_seq[:-20])
    if sum([1 if ret < 0.5 * ret_std else 0 for ret in ret_seq[-20:]]) >= 16:
        v1 = "粘合"

    if sum([1 if ret > 1.0 * ret_std else 0 for ret in ret_seq[-20:]]) >= 16:
        v1 = "扩散"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


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
    if len(bars) >= 100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]

        num_k = cross_zero_axis(dif, dea)  # type: ignore
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

    bars = get_sub_elements(c.bars_raw, di=di, n=n + 5)
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


def tas_atr_V230630(c: CZSC, **kwargs) -> OrderedDict:
    """ATR波动强弱

    参数模板："{freq}_D{di}ATR{timeperiod}_波动V230630"

    **信号逻辑：**

    ATR与收盘价的比值衡量了价格振幅比率的大小，对这个值进行分层。

    **信号列表：**

    - Signal('日线_D1ATR14_波动V230630_第7层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第6层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第8层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第9层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第10层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第5层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第4层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第3层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第2层_任意_任意_0')
    - Signal('日线_D1ATR14_波动V230630_第1层_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: ATR指标的参数

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    freq = c.freq.value
    cache_key = update_atr_cache(c, timeperiod=timeperiod)
    k1, k2, k3 = f"{freq}_D{di}ATR{timeperiod}_波动V230630".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    lev = [bar.cache[cache_key] / bar.close for bar in bars]
    lev = pd.qcut(lev, 10, labels=False, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"第{int(lev+1)}层")


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



def tas_macd_dist_V230408(c: CZSC, **kwargs) -> OrderedDict:
    """DIF/DEA/MACD 分层信号辅助判断买卖点

    参数模板："{freq}_{key}分层W{w}N{n}_BS辅助V230408"

    **信号逻辑：**

    1. 获取最近 w 根K线，计算 DIF/DEA/MACD，分成 n 层


    **信号列表：**

    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第7层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第6层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第5层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第4层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第3层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第2层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第1层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第8层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第9层_任意_任意_0')
    - Signal('15分钟_DIF分层W100N10_BS辅助V230408_第10层_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 10))
    w = int(kwargs.get("w", 100))
    key = kwargs.get("key", "dif").upper()
    assert key in ["DIF", "DEA", "MACD"]
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{key}分层W{w}N{n}_BS辅助V230408".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=w)
    factors = [x.cache[cache_key][key.lower()] for x in bars]
    q = pd.cut(factors, n, labels=list(range(1, n+1)), precision=5, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"第{q}层")


def tas_macd_dist_V230409(c: CZSC, **kwargs) -> OrderedDict:
    """DIF/DEA/MACD 远离零轴辅助判断买卖点

    参数模板："{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230409"

    **信号逻辑：**

    1. 获取最近 w 根K线，计算 DIF/DEA/MACD，计算绝对值的平均值
    2. 如果最新的值大于平均值 * t / 10，则认为远离零轴

    **信号列表：**

    - Signal('60分钟_DIF远离W100N10T20_BS辅助V230409_空头远离_任意_任意_0')
    - Signal('60分钟_DIF远离W100N10T20_BS辅助V230409_多头远离_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 10))
    w = int(kwargs.get("w", 100))
    t = int(kwargs.get("t", 20))    # 远离零轴的阈值，绝对值，越大越远离零轴，比较的基准是窗口内绝对值得平均；20表示2倍
    key = kwargs.get("key", "dif").upper()
    assert key in ["DIF", "DEA", "MACD"]
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230409".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=w)
    factors = [x.cache[cache_key][key.lower()] for x in bars]
    mean = np.mean(np.abs(factors))
    if max([abs(x) for x in factors[-n:]]) > mean * t / 10:
        v1 = f"{'多头' if factors[-1] > 0 else '空头'}远离"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_dist_V230410(c: CZSC, **kwargs) -> OrderedDict:
    """DIF/DEA/MACD 分层信号辅助判断买卖点

    参数模板："{freq}_{key}多空分层W{w}N{n}_BS辅助V230410"

    **信号逻辑：**

    1. 获取最近 w 根K线，计算 DIF/DEA/MACD
    2. 最近一根K线的值，如果大于0，则认为多头，小于0，则认为空头
    3. 多头情况下，只对 DIF/DEA/MACD 的值大于0的分层进行判断，空头情况下，只对 DIF/DEA/MACD 的值小于0的分层进行判断

    **信号列表：**

    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第1层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第2层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第5层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第4层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第3层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第2层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第1层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第3层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第4层_任意_0')
    - Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第5层_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 5))
    w = int(kwargs.get("w", 200))
    key = kwargs.get("key", "dif").upper()
    assert key in ["DIF", "DEA", "MACD"]
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{key}多空分层W{w}N{n}_BS辅助V230410".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=w)
    factors = [x.cache[cache_key][key.lower()] for x in bars]
    v1 = '多头' if factors[-1] > 0 else '空头'
    if v1 == '多头':
        factors = [x for x in factors if x > 0]
    else:
        factors = [x for x in factors if x < 0]

    q = pd.cut(factors, n, labels=list(range(1, n+1)), precision=5, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{q}层")


def cat_macd_V230518(cat: CzscSignals, **kwargs) -> OrderedDict:
    """freq1 与 freq2 联立信号，freq1 > freq2

    参数模板："{freq1}#{freq2}_MACD交叉_联立V230518"

     **信号逻辑：**

    1. 看多：freq1 MACD金叉后，freq2 MACD首次金叉
    2. 看空：freq1 MACD死叉后，freq2 MACD首次死叉

     **信号列表：**

    - Signal('日线#60分钟_MACD交叉_联立V230518_看空_任意_任意_0')
    - Signal('日线#60分钟_MACD交叉_联立V230518_看多_任意_任意_0')

    :param cat: CzscSignals对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    freq1 = kwargs.get('freq1', '5分钟')
    freq2 = kwargs.get('freq2', '1分钟')
    c1: CZSC = cat.kas[freq1]
    c2: CZSC = cat.kas[freq2]
    _ = update_macd_cache(c1, fastperiod=12, slowperiod=26, signalperiod=9)
    cache_key = update_macd_cache(c2, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq1}#{freq2}_MACD交叉_联立V230518".split('_')
    if len(c1.bars_raw) < 50 or len(c2.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    c1_bars = get_sub_elements(c1.bars_raw, di=1, n=8)
    c1_macd = [x.cache[cache_key]['macd'] for x in c1_bars]
    c2_bars = get_sub_elements(c2.bars_raw, di=1, n=50)

    if c1_macd[-1] > 0 and sum([1 if x > 0 else 0 for x in c1_macd]) != len(c1_macd):
        # 找出 c1 的最近一次金叉
        macd_gold_bars = []
        for bar1, bar2 in zip(c1_bars, c1_bars[1:]):
            if bar1.cache[cache_key]['macd'] < 0 and bar2.cache[cache_key]['macd'] > 0:
                macd_gold_bars.append(bar2)
        assert macd_gold_bars, "没有找到金叉"
        macd_gold_bar = macd_gold_bars[-1]

        # 找出 c2 的最近一次金叉
        c2_bars = [x for x in c2_bars if x.dt > macd_gold_bar.dt]
        if len(c2_bars) > 3:
            c2_gold_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] < 0 and bar2.cache[cache_key]['macd'] > 0:
                    c2_gold_bars.append(bar2)

            if len(c2_gold_bars) == 1:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='看多')

    if c1_macd[-1] < 0 and sum([1 if x < 0 else 0 for x in c1_macd]) != len(c1_macd):
        # 找出 c1 的最近一次死叉
        macd_dead_bars = []
        for bar1, bar2 in zip(c1_bars, c1_bars[1:]):
            if bar1.cache[cache_key]['macd'] > 0 and bar2.cache[cache_key]['macd'] < 0:
                macd_dead_bars.append(bar2)
        assert macd_dead_bars, "没有找到死叉"
        macd_dead_bar = macd_dead_bars[-1]

        # 找出 c2 的最近一次死叉
        c2_bars = [x for x in c2_bars if x.dt > macd_dead_bar.dt]
        if len(c2_bars) > 3:
            c2_dead_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] > 0 and bar2.cache[cache_key]['macd'] < 0:
                    c2_dead_bars.append(bar2)

            if len(c2_dead_bars) == 1:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='看空')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')


def cat_macd_V230520(cat: CzscSignals, **kwargs) -> OrderedDict:
    """freq1 与 freq2 联立信号，freq1 > freq2

    参数模板："{freq1}#{freq2}_MACD交叉_联立V230520"

    **信号逻辑：**

    1. 看多：freq1 MACD多头缩柱后，freq2 MACD首次金叉
    2. 看空：freq1 MACD空头缩柱后，freq2 MACD首次死叉

    **信号列表：**

    - Signal('日线#60分钟_MACD交叉_联立V230520_看空_零轴下方_任意_0')
    - Signal('日线#60分钟_MACD交叉_联立V230520_看多_零轴上方_任意_0')
    - Signal('日线#60分钟_MACD交叉_联立V230520_看空_零轴上方_任意_0')
    - Signal('日线#60分钟_MACD交叉_联立V230520_看多_零轴下方_任意_0')

    :param cat: CzscSignals对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    freq1 = kwargs.get('freq1', '5分钟')
    freq2 = kwargs.get('freq2', '1分钟')
    c1: CZSC = cat.kas[freq1]
    c2: CZSC = cat.kas[freq2]
    _ = update_macd_cache(c1, fastperiod=12, slowperiod=26, signalperiod=9)
    cache_key = update_macd_cache(c2, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq1}#{freq2}_MACD交叉_联立V230520".split('_')
    if len(c1.bars_raw) < 50 or len(c2.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    c1_bars = get_sub_elements(c1.bars_raw, di=1, n=8)
    c1_macd = [x.cache[cache_key]['macd'] for x in c1_bars]
    c2_bars = get_sub_elements(c2.bars_raw, di=1, n=50)

    # Check for three consecutive increases in MACD values for bull shrinkage
    min_bar = min(c1_bars, key=lambda x: x.low)
    if all(x < y for x, y in zip(c1_macd[-3:], c1_macd[-2:])) and min(c1_macd) < 0:

        c2_bars = [x for x in c2_bars if x.dt > min_bar.dt]
        if len(c2_bars) > 3:
            last_bar = c2_bars[-1]

            min_macd = min([x.cache[cache_key]['macd'] for x in c2_bars])
            max_macd = max([x.cache[cache_key]['macd'] for x in c2_bars])

            c2_gold_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] < 0 and bar2.cache[cache_key]['macd'] > 0:
                    c2_gold_bars.append(bar2)

            c2_dead_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] > 0 and bar2.cache[cache_key]['macd'] < 0:
                    c2_dead_bars.append(bar2)

            if len(c2_gold_bars) == 1 and len(c2_dead_bars) == 1 and c2_gold_bars[-1].id - c2_dead_bars[-1].id >= 5 \
                    and last_bar.dt == c2_gold_bars[0].dt > c2_dead_bars[0].dt and abs(min_macd) > abs(max_macd) * 0.3:
                v2 = '零轴上方' if c2_gold_bars[0].cache[cache_key]['dea'] > 0 else '零轴下方'
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='看多', v2=v2)

    # Check for three consecutive decreases in MACD values for bear shrinkage
    max_bar = max(c1_bars, key=lambda x: x.high)
    if all(x > y for x, y in zip(c1_macd[-3:], c1_macd[-2:])) and max(c1_macd) > 0:

        c2_bars = [x for x in c2_bars if x.dt > max_bar.dt]
        if len(c2_bars) > 3:
            last_bar = c2_bars[-1]
            min_macd = min([x.cache[cache_key]['macd'] for x in c2_bars])
            max_macd = max([x.cache[cache_key]['macd'] for x in c2_bars])

            c2_gold_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] < 0 and bar2.cache[cache_key]['macd'] > 0:
                    c2_gold_bars.append(bar2)

            c2_dead_bars = []
            for bar1, bar2 in zip(c2_bars, c2_bars[1:]):
                if bar1.cache[cache_key]['macd'] > 0 and bar2.cache[cache_key]['macd'] < 0:
                    c2_dead_bars.append(bar2)

            if len(c2_dead_bars) == 1 and len(c2_gold_bars) == 1 and c2_dead_bars[-1].id - c2_gold_bars[-1].id >= 5\
                    and last_bar.dt == c2_dead_bars[0].dt > c2_gold_bars[0].dt and abs(max_macd) > abs(min_macd) * 0.3:
                v2 = '零轴上方' if c2_dead_bars[0].cache[cache_key]['dea'] > 0 else '零轴下方'
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='看空', v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')


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


def tas_macd_bc_V230803(c: CZSC, **kwargs) -> OrderedDict:
    """MACD辅助背驰判断

    参数模板："{freq}_MACD双分型背驰_BS辅助V230803"

    **信号逻辑：**

    以向上笔为例，当出现两个顶分型时，当后一个顶分型中间K线的MACD柱子与前一个相比更低，认为是顶背驰。

    **信号列表：**

    - Signal('60分钟_MACD双分型背驰_BS辅助V230803_多头_任意_任意_0')
    - Signal('60分钟_MACD双分型背驰_BS辅助V230803_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_MACD双分型背驰_BS辅助V230803".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    if len(c.bi_list) < 3 or len(c.bars_ubi) >= 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1 = c.bi_list[-1]
    if b1.direction == Direction.Up:
        fx1, fx2 = [fx for fx in c.fx_list[-10:] if fx.mark == Mark.G][-2:]
        macd1 = fx1.raw_bars[1].cache[cache_key]['macd']
        macd2 = fx2.raw_bars[1].cache[cache_key]['macd']
        if macd1 > macd2 > 0:
            v1 = '空头'
    else:
        fx1, fx2 = [fx for fx in c.fx_list[-10:] if fx.mark == Mark.D][-2:]
        macd1 = fx1.raw_bars[1].cache[cache_key]['macd']
        macd2 = fx2.raw_bars[1].cache[cache_key]['macd']
        if macd1 < macd2 < 0:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bc_V230804(c: CZSC, **kwargs) -> OrderedDict:
    """MACD黄白线辅助背驰判断

    参数模板："{freq}_D{di}MACD背驰_BS辅助V230804"

    **信号逻辑：**

    以向上笔为例，当前笔在中枢中轴上方，且MACD黄白线不是最高，认为是背驰，做空；反之，做多。

    **信号列表：**

    - Signal('60分钟_D1MACD背驰_BS辅助V230804_空头_任意_任意_0')
    - Signal('60分钟_D1MACD背驰_BS辅助V230804_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MACD背驰_BS辅助V230804".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    if len(c.bi_list) < 7 or len(c.bars_ubi) >= 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=7)
    zs = ZS(bis=bis[-5:])
    if not zs.is_valid:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    dd = min([bi.low for bi in bis])
    gg = max([bi.high for bi in bis])
    b1, b2, b3, b4, b5 = bis[-5:]
    if b5.direction == Direction.Up and b5.high > (gg - (gg - dd) / 4):
        b5_dif = max([x.cache[cache_key]['dif'] for x in b5.fx_b.raw_bars])
        od_dif = max([x.cache[cache_key]['dif'] for x in b1.fx_b.raw_bars + b3.fx_b.raw_bars])
        if 0 < b5_dif < od_dif:
            v1 = '空头'

    if b5.direction == Direction.Down and b5.low < (dd + (gg - dd) / 4):
        b5_dif = min([x.cache[cache_key]['dif'] for x in b5.fx_b.raw_bars])
        od_dif = min([x.cache[cache_key]['dif'] for x in b1.fx_b.raw_bars + b3.fx_b.raw_bars])
        if 0 > b5_dif > od_dif:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bc_ubi_V230804(c: CZSC, **kwargs) -> OrderedDict:
    """未完成笔MACD黄白线辅助背驰判断

    参数模板："{freq}_MACD背驰_UBI观察V230804"

    **信号逻辑：**

    以向上未完成笔为例，当前笔在中枢中轴上方，且MACD黄白线不是最高，认为是背驰，做空；反之，做多。

    **信号列表：**

    - Signal('60分钟_MACD背驰_UBI观察V230804_多头_任意_任意_0')
    - Signal('60分钟_MACD背驰_UBI观察V230804_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_MACD背驰_UBI观察V230804".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    ubi = c.ubi
    if len(c.bi_list) < 7 or not ubi or len(ubi['raw_bars']) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=1, n=6)
    zs = ZS(bis=bis[-5:])
    if not zs.is_valid:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    dd = min([bi.low for bi in bis])
    gg = max([bi.high for bi in bis])
    b1, b2, b3, b4, b5 = bis[-5:]
    if ubi['direction'] == Direction.Up and ubi['high'] > (gg - (gg - dd) / 4):
        b5_dif = max([x.cache[cache_key]['dif'] for x in ubi['raw_bars'][-5:]])
        od_dif = max([x.cache[cache_key]['dif'] for x in b2.fx_b.raw_bars + b4.fx_b.raw_bars])
        if 0 < b5_dif < od_dif:
            v1 = '空头'

    if ubi['direction'] == Direction.Down and ubi['low'] < (dd + (gg - dd) / 4):
        b5_dif = min([x.cache[cache_key]['dif'] for x in ubi['raw_bars'][-5:]])
        od_dif = min([x.cache[cache_key]['dif'] for x in b2.fx_b.raw_bars + b4.fx_b.raw_bars])
        if 0 > b5_dif > od_dif:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_slope_V231019(c: CZSC, **kwargs) -> OrderedDict:
    """DIF趋势线斜率判断多空

    参数模板："{freq}_D{di}DIF{n}斜率T{th}_BS辅助V231019"

    **信号逻辑：**

    取最近 N 根K线的DIF值计算斜率，然后取 N * 10 根K线的斜率值，计算斜率值的分位数，
    如果分位数大于th，则看多，小于1-th，则看空。

    **信号列表：**

    - Signal('60分钟_D1DIF10斜率T80_BS辅助V231019_看多_任意_任意_0')
    - Signal('60分钟_D1DIF10斜率T80_BS辅助V231019_看空_任意_任意_0')

    :param cat: CzscSignals对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 10))
    th = int(kwargs.get('th', 80))
    assert th > 50 and th < 100, 'th 参数取值范围为 50 ~ 100'

    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}DIF{n}斜率T{th}_BS辅助V231019".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    cache_slope_key = f"tas_slope_V231019_{di}_{n}"
    for i, bar in enumerate(c.bars_raw):
        if i < n:
            continue

        if cache_slope_key not in bar.cache:
            dif = [x.cache[cache_key]['dif'] for x in c.bars_raw[i - n: i]]
            bar.cache[cache_slope_key] = single_linear(dif)['slope']

    bars = get_sub_elements(c.bars_raw, di=di, n=n * 10)
    dif_slope = [x.cache.get(cache_slope_key, 0) for x in bars]
    q = (dif_slope[-1] - min(dif_slope)) / (max(dif_slope) - min(dif_slope))
    if q > th / 100:
        v1 = '看多'
    elif q < 1 - th / 100:
        v1 = '看空'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
