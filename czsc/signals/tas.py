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
from czsc import CZSC, Signal
from czsc.utils import get_sub_elements, fast_slow_cross
from collections import OrderedDict


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
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 5:
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
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 30:
        close = np.array([x.close for x in c.bars_raw])
        min_count = 0
    else:
        close = np.array([x.close for x in c.bars_raw[-min_count-30:]])

    dif, dea, macd = ta.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)

    for i in range(1, len(close) - min_count - 10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: {'dif': dif[-i], 'dea': dea[-i], 'macd': macd[-i]}})
        c.bars_raw[-i].cache = _c


def update_boll_cache(c: CZSC, **kwargs) -> None:
    """更新K线的BOLL缓存

    :param c: 交易对象
    :return:
    """
    cache_key = "boll"
    timeperiod = kwargs.get('timeperiod', 20)
    dev_seq = kwargs.get('dev_seq', (1.382, 2, 2.764))

    min_count = timeperiod
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 30:
        close = np.array([x.close for x in c.bars_raw])
        min_count = 0
    else:
        close = np.array([x.close for x in c.bars_raw[-min_count-30:]])

    u1, m, l1 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[0], nbdevdn=dev_seq[0], matype=ta.MA_Type.SMA)
    u2, m, l2 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[1], nbdevdn=dev_seq[1], matype=ta.MA_Type.SMA)
    u3, m, l3 = ta.BBANDS(close, timeperiod=timeperiod, nbdevup=dev_seq[2], nbdevdn=dev_seq[2], matype=ta.MA_Type.SMA)

    for i in range(1, len(close) - min_count - 10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: {"上轨3": u3[-i], "上轨2": u2[-i], "上轨1": u1[-i],
                               "中线": m[-i],
                               "下轨1": l1[-i], "下轨2": l2[-i], "下轨3": l3[-i]}})
        c.bars_raw[-i].cache = _c


# MACD信号计算函数
# ======================================================================================================================

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


def tas_macd_direct_V221106(c: CZSC, di: int = 1) -> OrderedDict:
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
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD方向".split("_")
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    macd = [x.cache['MACD']['macd'] for x in bars]

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

    s = OrderedDict()
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s


def tas_macd_change_V221105(c: CZSC, di: int = 1, n: int = 55) -> OrderedDict:
    """MACD颜色变化；贡献者：马鸣

    **信号逻辑：** 从dik往前数n根k线对应的macd红绿柱子变换次数

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
    k1, k2, k3 = f"{c.freq.value}_D{di}K{n}_MACD变色次数".split('_')

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    dif = [x.cache['MACD']['dif'] for x in bars]
    dea = [x.cache['MACD']['dea'] for x in bars]

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

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=f"{num}次")
    s[signal.key] = signal.value
    return s


# MA信号计算函数
# ======================================================================================================================

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
    :param di: 信号计算截止倒数第i根K线
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


# BOLL信号计算函数
# ======================================================================================================================


def tas_boll_power_V221112(c: CZSC, di: int = 1):
    """BOLL指标强弱

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
    :param di: 信号计算截止倒数第i根K线
    :return: s
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_BOLL强弱".split("_")

    if len(c.bars_raw) < di + 20:
        v1, v2 = '其他', '其他'

    else:
        last = c.bars_raw[-di]
        cache = last.cache['boll']

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

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s




