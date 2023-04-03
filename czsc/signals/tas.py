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
from czsc.analyze import CZSC
from czsc.objects import Signal, Direction, BI, RawBar, FX
from czsc.utils import get_sub_elements, fast_slow_cross, count_last_same, create_single_signal
from collections import OrderedDict


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
    timeperiod = int(kwargs.get("timeperiod"))
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
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10:]])
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

    min_count = signalperiod + slowperiod
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
        close = np.array([x.close for x in c.bars_raw[-min_count - 10:]])
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
    timeperiod = kwargs.get('timeperiod', 20)
    nbdev = int(kwargs.get('nbdev', 20))   # 标准差倍数，计算时除以10，如20表示2.0，即2倍标准差
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
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10:]])
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
                _data = {"上轨3": close[i], "上轨2": close[i], "上轨1": close[i],
                         "中线": close[i],
                         "下轨1": close[i], "下轨2": close[i], "下轨3": close[i]}
            else:
                _data = {"上轨3": u3[i], "上轨2": u2[i], "上轨1": u1[i],
                         "中线": m[i],
                         "下轨1": l1[i], "下轨2": l2[i], "下轨3": l3[i]}
            _c.update({cache_key: _data})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近5个K线缓存
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10:]])
        u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[0], nbdevdn=dev_seq[0], matype=0)
        u2, m, l2 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[1], nbdevdn=dev_seq[1], matype=0)
        u3, m, l3 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[2], nbdevdn=dev_seq[2], matype=0)

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: {"上轨3": u3[-i], "上轨2": u2[-i], "上轨1": u1[-i],
                                   "中线": m[-i],
                                   "下轨1": l1[-i], "下轨2": l2[-i], "下轨3": l3[-i]}})
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_boll_vt_V230212(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """以BOLL通道为依据的多空进出场信号

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
    key = update_boll_cache_V230228(c, **kwargs)
    max_overlap = kwargs.get('max_overlap', 5)
    k1, k2, k3 = f"{c.freq.value}_D{di}{key}MO{max_overlap}_BS辅助V230212".split('_')
    v1 = "其他"
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
def tas_macd_base_V221028(c: CZSC, di: int = 1, key="macd", **kwargs) -> OrderedDict:
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
    cache_key = update_macd_cache(c, **kwargs)
    assert key.lower() in ['macd', 'dif', 'dea']
    k1, k2, k3 = f"{c.freq.value}_D{di}K_{key.upper()}".split('_')

    macd = [x.cache[cache_key][key.lower()] for x in c.bars_raw[-5 - di:]]
    v1 = "多头" if macd[-di] >= 0 else "空头"
    v2 = "向上" if macd[-di] >= macd[-di - 1] else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def tas_macd_direct_V221106(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """MACD方向；贡献者：马鸣

    **信号逻辑：** 连续三根macd柱子值依次增大，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1K_MACD方向_向下_任意_任意_0')
    - Signal('15分钟_D1K_MACD方向_模糊_任意_任意_0')
    - Signal('15分钟_D1K_MACD方向_向上_任意_任意_0')

    :param c: CZSC对象
    :param di: 连续倒3根K线
    :return:
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD方向".split("_")
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


def tas_macd_power_V221108(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """MACD强弱

    **信号逻辑：**

    1. 指标超强满足条件：DIF＞DEA＞0；释义：指标超强表示市场价格处于中长期多头趋势中，可能形成凌厉的逼空行情
    2. 指标强势满足条件：DIF-DEA＞0（MACD柱线＞0）释义：指标强势表示市场价格处于中短期多头趋势中，价格涨多跌少，通常是反弹行情
    3. 指标弱势满足条件：DIF-DEA＜0（MACD柱线＜0）释义：指标弱势表示市场价格处于中短期空头趋势中，价格跌多涨少，通常是回调行情
    4. 指标超弱满足条件：DIF＜DEA＜0释义：指标超弱表示市场价格处于中长期空头趋势中，可能形成杀多行情

    **信号列表：**

    - Signal('60分钟_D1K_MACD强弱_超强_任意_任意_0')
    - Signal('60分钟_D1K_MACD强弱_弱势_任意_任意_0')
    - Signal('60分钟_D1K_MACD强弱_超弱_任意_任意_0')
    - Signal('60分钟_D1K_MACD强弱_强势_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号产生在倒数第di根K线
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD强弱".split("_")

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


def tas_macd_first_bs_V221201(c: CZSC, di: int = 1, **kwargs):
    """MACD金叉死叉判断第一买卖点

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD_BS1_一卖_任意_任意_0')
    - Signal('15分钟_D1MACD_BS1_一买_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD_BS1".split('_')
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


def tas_macd_first_bs_V221216(c: CZSC, di: int = 1, **kwargs):
    """MACD金叉死叉判断第一买卖点

    **信号逻辑：**

    1. 最近一次交叉为死叉，且前面两次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉都在零轴下方，价格创新低，那么一买即将出现；一卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD_BS1A_一卖_金叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一卖_死叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一买_死叉_任意_0')
    - Signal('15分钟_D1MACD_BS1A_一买_金叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD_BS1A".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=300)

    v1 = "其他"
    v2 = "任意"
    if len(bars) >= 100:
        dif = [x.cache[cache_key]['dif'] for x in bars]
        dea = [x.cache[cache_key]['dea'] for x in bars]
        macd = [x.cache[cache_key]['macd'] for x in bars]
        n_bars = bars[-10:]
        m_bars = bars[-100: -10]
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


def tas_macd_second_bs_V221201(c: CZSC, di: int = 1, **kwargs):
    """MACD金叉死叉判断第二买卖点

    **信号逻辑：**

    1. 最近一次交叉为死叉，DEA大于0，且前面两次死叉都在零轴下方，那么二买即将出现；二卖反之。
    2. 或 最近一次交叉为金叉，且前面三次死叉中前两次都在零轴下方，后一次在零轴上方，那么二买即将出现；二卖反之。

    **信号列表：**

    - Signal('15分钟_D1MACD_BS2_二卖_金叉_任意_0')
    - Signal('15分钟_D1MACD_BS2_二卖_死叉_任意_0')
    - Signal('15分钟_D1MACD_BS2_二买_金叉_任意_0')
    - Signal('15分钟_D1MACD_BS2_二买_死叉_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}MACD_BS2".split('_')
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


def tas_macd_xt_V221208(c: CZSC, di: int = 1, **kwargs):
    """MACD形态信号

    **信号逻辑：**

    1. MACD柱子的形态分类，具体见代码定义

    **信号列表：**

    - Signal('15分钟_D3K_MACD形态_多翻空_任意_任意_0')
    - Signal('15分钟_D3K_MACD形态_绿抽脚_任意_任意_0')
    - Signal('15分钟_D3K_MACD形态_空翻多_任意_任意_0')
    - Signal('15分钟_D3K_MACD形态_杀多棒_任意_任意_0')
    - Signal('15分钟_D3K_MACD形态_红缩头_任意_任意_0')
    - Signal('15分钟_D3K_MACD形态_逼空棒_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :return:
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD形态".split('_')
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


def tas_macd_bc_V221201(c: CZSC, di: int = 1, n: int = 3, m: int = 50, **kwargs):
    """MACD背驰辅助

    **信号逻辑：**

    1. 近n个最低价创近m个周期新低（以收盘价为准），macd柱子不创新低，这是底部背驰信号
    2. 若底背驰信号出现时 macd 为红柱，相当于进一步确认
    3. 顶部背驰反之

    **信号列表：**

    - Signal('15分钟_D1N3M50_MACD背驰_顶部_绿柱_任意_0')
    - Signal('15分钟_D1N3M50_MACD背驰_顶部_红柱_任意_0')
    - Signal('15分钟_D1N3M50_MACD背驰_底部_绿柱_任意_0')
    - Signal('15分钟_D1N3M50_MACD背驰_底部_红柱_任意_0')

    :param c: CZSC对象
    :param di: 倒数第i根K线
    :param n: 近期窗口大小
    :param m: 远期窗口大小
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}_MACD背驰".split('_')
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


def tas_macd_change_V221105(c: CZSC, di: int = 1, n: int = 55, **kwargs) -> OrderedDict:
    """MACD颜色变化；贡献者：马鸣

    **信号逻辑：**

    从dik往前数n根k线对应的macd红绿柱子变换次数

    **信号列表：**

    - Signal('15分钟_D1K55_MACD变色次数_1次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_2次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_3次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_4次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_5次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_6次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_7次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_8次_任意_任意_0')
    - Signal('15分钟_D1K55_MACD变色次数_9次_任意_任意_0')

    :param c: czsc对象
    :param di: 倒数第i根K线
    :param n: 从dik往前数n根k线
    :return:
    """
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K{n}_MACD变色次数".split('_')

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
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}{key}_分类V221101".split('_')

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
    k1, k2, k3 = f"{freq}_D{di}{key}T{th}_分类V221203".split('_')

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


def tas_ma_round_V221206(c: CZSC, di: int = 1, ma_type='SMA', timeperiod=60, th: int = 10) -> OrderedDict:
    """笔端点在均线附近，贡献者：谌意勇

    **信号逻辑：**

    倒数第i笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近

    **信号列表：**

    - Signal('15分钟_D3TH10_碰SMA233_上碰_任意_任意_0')
    - Signal('15分钟_D3TH10_碰SMA233_下碰_任意_任意_0')

    :param c: CZSC对象
    :param di: 指定倒数第几笔
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param timeperiod: 均线计算周期
    :param th: 笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近
    :return: 信号识别结果
    """
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f'{c.freq.value}_D{di}TH{th}_碰{key}'.split('_')

    v1 = "其他"
    if len(c.bi_list) > di + 3:
        last_bi = c.bi_list[-di]
        last_ma = np.mean([x.cache[key] for x in last_bi.fx_b.new_bars[1].raw_bars])
        bi_change = last_bi.power_price

        if last_bi.direction == Direction.Up and abs(last_bi.high - last_ma) / bi_change < th / 100:
            v1 = "上碰"
        elif last_bi.direction == Direction.Down and abs(last_bi.low - last_ma) / bi_change < th / 100:
            v1 = "下碰"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_double_ma_V221203(c: CZSC, di: int = 1, ma_type='SMA', ma_seq=(5, 10), th: int = 100) -> OrderedDict:
    """双均线多空和强弱信号

    **信号逻辑：**

    1. ma1 > ma2，多头；反之，空头
    2. ma1 离开 ma2 的距离大于 th，强势；反之，弱势

    **信号列表：**

    - Signal('日线_D2T100_SMA5SMA10_多头_强势_任意_0')
    - Signal('日线_D2T100_SMA5SMA10_多头_弱势_任意_0')
    - Signal('日线_D2T100_SMA5SMA10_空头_强势_任意_0')
    - Signal('日线_D2T100_SMA5SMA10_空头_弱势_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param ma_seq: 快慢均线计算周期，快线在前
    :param th: ma1 相比 ma2 的距离阈值，单位 BP
    :return: 信号识别结果
    """
    assert len(ma_seq) == 2 and ma_seq[1] > ma_seq[0]
    ma1 = update_ma_cache(c, ma_type=ma_type, timeperiod=ma_seq[0])
    ma2 = update_ma_cache(c, ma_type=ma_type, timeperiod=ma_seq[1])

    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}_{ma1}{ma2}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    ma1v = bars[-1].cache[ma1]
    ma2v = bars[-1].cache[ma2]
    v1 = "多头" if ma1v >= ma2v else "空头"
    v2 = "强势" if (abs(ma1v - ma2v) / ma2v) * 10000 >= th else "弱势"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


# BOLL信号计算函数
# ======================================================================================================================


def tas_boll_power_V221112(c: CZSC, **kwargs):
    """BOLL指标强弱

    参数模板："{freq}_D{di}K_BOLL强弱"

    **信号逻辑：**

    1. close大于中线，多头；反之，空头
    2. close超过轨3，超强，以此类推

    **信号列表：**

    - Signal('15分钟_D1K_BOLL强弱_空头_强势_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_空头_弱势_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_多头_强势_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_多头_弱势_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_空头_超强_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_空头_极强_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_多头_超强_任意_0')
    - Signal('15分钟_D1K_BOLL强弱_多头_极强_任意_0')

    :param c: CZSC对象
    :param kwargs: 其他参数
        - di: 信号计算截止倒数第i根K线
        - timeperiod: BOLL指标计算周期
    :return: s
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}K_BOLL强弱".split("_")

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


def tas_boll_bc_V221118(c: CZSC, di=1, n=3, m=10, line=3, **kwargs):
    """BOLL背驰辅助

    **信号逻辑：**

    近n个最低价创近m个周期新低，近m个周期跌破下轨，近n个周期不破下轨，这是BOLL一买（底部背驰）信号，顶部背驰反之。

    **信号列表：**

    - Signal('60分钟_D1N3M10L2_BOLL背驰_一卖_任意_任意_0')
    - Signal('60分钟_D1N3M10L2_BOLL背驰_一买_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :param n: 近n个周期
    :param m: 近m个周期
    :param line: 选第几个上下轨
    :return:
    """
    cache_key = update_boll_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}L{line}_BOLL背驰".split('_')

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

        k, d = ta.STOCH(high, low, close, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)
        j = list(map(lambda x, y: 3 * x - 2 * y, k, d))

        for i in range(len(close)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: {'k': k[i] if k[i] else 0, 'd': d[i] if d[i] else 0, 'j': j[i] if j[i] else 0}})
            c.bars_raw[i].cache = _c

    else:
        bars = c.bars_raw[-min_count - 10:]
        high = np.array([x.high for x in bars])
        low = np.array([x.low for x in bars])
        close = np.array([x.close for x in bars])
        k, d = ta.STOCH(high, low, close, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)
        j = list(map(lambda x, y: 3 * x - 2 * y, k, d))

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: {'k': k[-i], 'd': d[-i], 'j': j[-i]}})
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_kdj_base_V221101(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """KDJ金叉死叉信号

    **信号逻辑：**

    1. J > K > D，多头；反之，空头
    2. J 值定方向

    **信号列表：**

    - Signal('日线_D2K_KDJ_空头_向下_任意_0')
    - Signal('日线_D2K_KDJ_空头_向上_任意_0')
    - Signal('日线_D2K_KDJ_多头_向上_任意_0')
    - Signal('日线_D2K_KDJ_多头_向下_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :return:
    """
    cache_key = update_kdj_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}K_{cache_key}".split('_')
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


def tas_kdj_evc_V221201(c: CZSC, di: int = 1, key='K', th=10, count_range=(5, 8), **kwargs) -> OrderedDict:
    """KDJ极值计数信号, evc 是 extreme value counts 的首字母缩写

    **信号逻辑：**

     1. K < th，记录一次多头信号，连续出现信号次数在 count_range 范围，则认为是有效多头信号；
     2. K > 100 - th, 记录一次空头信号，连续出现信号次数在 count_range 范围，则认为是有效空头信号

    **信号列表：**

    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C5_任意_0')
    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C5_任意_0')
    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C6_任意_0')
    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_多头_C7_任意_0')
    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C6_任意_0')
    - Signal('日线_D1T10KDJ36#3#3_K值突破5#8_空头_C7_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param key: KDJ 值的名称，可以是 K， D， J
    :param th: 信号计算截止倒数第i根K线
    :param count_range: 信号计数范围
    :return:
    """
    cache_key = update_kdj_cache(c, **kwargs)
    c1, c2 = count_range
    assert c2 > c1
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}{cache_key}_{key.upper()}值突破{c1}#{c2}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3+c2)

    v1 = "其他"
    v2 = "任意"
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
        close = np.array([x.close for x in c.bars_raw[-timeperiod - 10:]])
        rsi = ta.RSI(close, timeperiod=timeperiod)

        for i in range(1, 6):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: rsi[-i]})
            c.bars_raw[-i].cache = _c

    return cache_key


def tas_rsi_base_V230227(c: CZSC, di=1, n: int = 6, th: int = 20, **kwargs) -> OrderedDict:
    """RSI超买超卖信号

    **信号逻辑：**

    在正常情况下，RSI指标都会在30-70的区间内波动。当6日RSI超过80时，表示市场已经处于超买区间。6日RSI达到90以上时，
    表示市场已经严重超买，股价极有可能已经达到阶段顶点。这时投资者应该果断卖出。当6日RSI下降到20时，表示市场已经处于
    超卖区间。6日RSI一旦下降到10以下，则表示市场已经严重超卖，股价极有可能会止跌回升，是很好的买入信号。

    **信号列表：**

    - Signal('日线_D2T20_RSI6V230227_超卖_向下_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超买_向上_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超买_向下_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超卖_向上_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: RSI的计算周期
    :param th: RSI阈值
    :return: 信号识别结果
    """
    cache_key = update_rsi_cache(c, timeperiod=n)
    k1, k2, k3, v1 = str(c.freq.value), f"D{di}T{th}", f"{cache_key}V230227", "其他"
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


def tas_double_rsi_V221203(c: CZSC, di: int = 1, rsi_seq=(5, 10), **kwargs) -> OrderedDict:
    """两个周期的RSI多空信号

    **信号逻辑：**

    1. rsi1 > rsi2，多头；反之，空头

    **信号列表：**

    - Signal('15分钟_D1K_RSI5#10_空头_任意_任意_0')
    - Signal('15分钟_D1K_RSI5#10_多头_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param di: 信号计算截止倒数第i根K线
    :param rsi_seq: 指定短期RSI, 长期RSI 参数
    :return: 信号识别结果
    """
    assert len(rsi_seq) == 2 and rsi_seq[1] > rsi_seq[0]
    rsi1 = update_rsi_cache(c, timeperiod=rsi_seq[0])
    rsi2 = update_rsi_cache(c, timeperiod=rsi_seq[1])

    k1, k2, k3 = f"{c.freq.value}_D{di}K_RSI{rsi_seq[0]}#{rsi_seq[1]}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    rsi1v = bars[-1].cache[rsi1]
    rsi2v = bars[-1].cache[rsi2]
    v1 = "多头" if rsi1v >= rsi2v else "空头"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_first_bs_V230217(c: CZSC, **kwargs) -> OrderedDict:
    """均线结合K线形态的一买一卖辅助判断

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
def tas_second_bs_V230228(c: CZSC, di: int = 1, n: int = 21, **kwargs) -> OrderedDict:
    """均线结合K线形态的第二买卖点辅助判断

    **信号逻辑：**

    1. 二买辅助：1）MA20创新高且向上；2）近三根K线最低价跌破 MA20，且当前收盘价在MA20上
    2. 反之，二卖辅助。

    **信号列表：**

    - Signal('日线_D2N21SMA20_BS2辅助V230228_二卖_任意_任意_0')
    - Signal('日线_D2N21SMA20_BS2辅助V230228_二买_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线，1表示最后一根K线
    :param n: 窗口大小
    :param kwargs:
    :return: 信号识别结果
    """
    ma_type = kwargs.get('ma_type', 'SMA')
    timeperiod = int(kwargs.get('timeperiod', 20))
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}{ma_type}{timeperiod}_BS2辅助V230228".split('_')
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


def tas_second_bs_V230303(c: CZSC, di: int = 1, **kwargs):
    """利用笔和均线辅助二买信号生成

    **信号逻辑：**

    1. 最近5笔创新低，且最近一向下笔最低点跌破中期均线，且中期均线向上，二买信号；
    2. 反之，二卖信号。

    **信号列表**

    - Signal('15分钟_D1SMA34_BS2辅助V230303_二买_任意_任意_0')
    - Signal('15分钟_D1SMA34_BS2辅助V230303_二卖_任意_任意_0')

    :param c: CZSC对象
    :param di: 指定倒数第几笔
    :param ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    :param timeperiod: 均线计算周期
    :return: 信号识别结果
    """
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    timeperiod = int(kwargs.get('timeperiod', 30))
    key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f'{c.freq.value}_D{di}{key}_BS2辅助V230303'.split('_')
    v1 = '其他'

    if len(c.bi_list) < di + 13:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bi_list = get_sub_elements(c.bi_list, di=di, n=13)
    last_bi: BI = _bi_list[-1]
    first_bar: RawBar = last_bi.raw_bars[0]
    last_bar: RawBar = last_bi.raw_bars[-1]

    if last_bi.direction == Direction.Down and last_bar.low < last_bar.cache[key] \
            and min([x.low for x in _bi_list[-5:]]) == min([x.low for x in _bi_list]) \
            and first_bar.cache[key] < last_bar.cache[key]:
        v1 = "二买"

    if last_bi.direction == Direction.Up and last_bar.high > last_bar.cache[key] \
            and max([x.high for x in _bi_list[-5:]]) == max([x.high for x in _bi_list]) \
            and first_bar.cache[key] > last_bar.cache[key]:
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


@deprecated(version='1.0.0', reason="表现不如 tas_hlma_V230301，已废弃")
def tas_hlma_V230304(c: CZSC, di: int = 1, n=3) -> OrderedDict:
    """HMA多空信号；贡献者：琅盎

    **信号逻辑：**

    1. 收盘价大于HMA and 上一根K线的收盘价小于昨日HMA开多
    2. 收盘价小于LMA and 上一根K线的收盘价大于昨日LMA开多

    **信号列表：**

    - Signal('30分钟_D2N34HLMA_V230304_看空_任意_任意_0')
    - Signal('30分钟_D2N34HLMA_V230304_看多_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param n: high均线计算周期
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}HLMA_V230304".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)

    hma = np.mean([x.high for x in _bars])
    lma = np.mean([x.low for x in _bars])

    # 使用缓存来更新信号的数据
    cache_key = 'tas_hlma_V230304'
    hlma = c.cache.get(cache_key, None)
    _today = _bars[-1].dt.strftime('%Y-%m-%d')

    if not hlma:
        hlma = {'yesterday': _today, 'yesterday_hma': hma, 'yesterday_lma': lma,
                'today': _today, 'today_hma': hma, 'today_lma': lma}

    if _today != hlma['yesterday']:
        hlma['yesterday_hma'] = hlma['today_hma']
        hlma['yesterday_lma'] = hlma['today_lma']
        hlma['yesterday'] = hlma['today']

    hlma['today'] = _today
    hlma['today_hma'] = hma
    hlma['today_lma'] = lma

    c.cache[cache_key] = hlma

    # 生成信号
    if _bars[-1].close > hma and _bars[-2].close <= hlma['yesterday_hma']:
        v1 = "看多"
    elif _bars[-1].close < lma and _bars[-2].close >= hlma['yesterday_lma']:
        v1 = "看空"
    else:
        v1 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_boll_cc_V230312(c: CZSC, di: int = 1, sp=400, **kwargs) -> OrderedDict:
    """多空进出场信号，贡献者：琅盎

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
    key = update_boll_cache_V230228(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}{key}SP{sp}_BS辅助V230312".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=6)

    bias = (_bars[-1].close / _bars[-1].cache[key]['中线'] - 1) * 10000

    v1 = "其他"
    if _bars[-1].close < _bars[-1].cache[key]['上轨'] and bias < -sp:
        v1 = "看空"

    elif _bars[-1].close > _bars[-1].cache[key]['下轨'] and bias > sp:
        v1 = "看多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230312(c: CZSC, di: int = 1, **kwargs):
    """MACD辅助一买一卖信号

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
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}{cache_key}_BS1辅助V230312".split('_')
    v1 = "其他"

    bis = get_sub_elements(c.bi_list, di=di, n=7)
    if len(bis) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_fx: FX = bis[-1].fx_b
    bi_low = max([x.low for x in bis[:-1] if x.direction == Direction.Up])
    if bis[-1].direction == Direction.Down and bis[-1].low == min([x.low for x in bis]) and bis[-1].high < bi_low \
            and last_fx.raw_bars[-1].cache[cache_key]['macd'] > last_fx.raw_bars[0].cache[cache_key]['macd']:
        v1 = "看多"

    bi_high = min([x.high for x in bis[:-1] if x.direction == Direction.Down])
    if bis[-1].direction == Direction.Up and bis[-1].high == max([x.high for x in bis]) and bis[-1].low > bi_high \
            and last_fx.raw_bars[-1].cache[cache_key]['macd'] < last_fx.raw_bars[0].cache[cache_key]['macd']:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def tas_macd_bs1_V230313(c: CZSC, di: int = 1, **kwargs):
    """MACD红绿柱判断第一买卖点，贡献者：琅盎

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
    cache_key = update_macd_cache(c, **kwargs)
    k1, k2, k3 = f"{c.freq.value}_D{di}{cache_key}_BS1辅助V230313".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=300)

    v1 = "其他"
    v2 = "任意"
    if len(bars) <= 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    dif, dea, macd = [], [], []
    for x in bars:
        dif.append(x.cache[cache_key]['dif'])
        dea.append(x.cache[cache_key]['dea'])
        macd.append(x.cache[cache_key]['macd'])

    n_bars = bars[-10:]
    m_bars = bars[-100: -10]
    high_n = max([x.high for x in n_bars])
    low_n = min([x.low for x in n_bars])
    high_m = max([x.high for x in m_bars])
    low_m = min([x.low for x in m_bars])

    cross = fast_slow_cross(dif, dea)
    up = [x for x in cross if x['类型'] == "金叉"]
    dn = [x for x in cross if x['类型'] == "死叉"]

    b1_con1a = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['面积'] < cross[-2]['面积'] or cross[-1]['面积'] < cross[-3]['面积']
    b1_con1b = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['面积'] > cross[-2]['面积'] or cross[-1]['面积'] < cross[-3]['面积']
    b1_con2 = len(dn) > 3 and dn[-2]['面积'] < dn[-3]['面积']   # 三次死叉面积逐渐减小
    b1_con3 = len(macd) > 10 and macd[-1] > macd[-2]          # MACD向上
    if low_n < low_m and (b1_con1a or b1_con1b) and b1_con2 and b1_con3:
        v1 = "一买"

    s1_con1a = len(cross) > 3 and cross[-1]['类型'] == '金叉' and cross[-1]['面积'] > cross[-2]['面积'] or cross[-1]['面积'] > cross[-3]['面积']
    s1_con1b = len(cross) > 3 and cross[-1]['类型'] == '死叉' and cross[-1]['面积'] < cross[-2]['面积'] or cross[-1]['面积'] < cross[-3]['面积']
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
    max_overlap = int(kwargs.get("max_overlap", 3))
    cache_key = update_macd_cache(c, **kwargs)
    assert key.lower() in ['macd', 'dif', 'dea']
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}{cache_key}MO{max_overlap}#{key}_BS辅助V230320".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 5 + di + max_overlap:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap+1)
    value = [x.cache[cache_key][key.lower()] for x in bars]
    if value[-1] > 0 and any([x < 0 for x in value[:-1]]):
        v1 = "多头"
    elif value[-1] < 0 and any([x > 0 for x in value[:-1]]):
        v1 = "空头"
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    v2 = "向上" if value[-1] >= value[-2] else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


