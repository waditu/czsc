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
from czsc.analyze import CZSC
from czsc.objects import Signal, Direction
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


def tas_macd_power_V221108(c: CZSC, di: int = 1) -> OrderedDict:
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
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD强弱".split("_")

    v1 = "其他"
    if len(c.bars_raw) > di + 10:
        bar = c.bars_raw[-di]
        dif, dea = bar.cache['MACD']['dif'], bar.cache['MACD']['dea']

        if dif >= dea >= 0:
            v1 = "超强"
        elif dif - dea > 0:
            v1 = "强势"
        elif dif <= dea <= 0:
            v1 = "超弱"
        elif dif - dea < 0:
            v1 = "弱势"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def tas_macd_xt_V221208(c: CZSC, di: int = 1):
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
    k1, k2, k3 = f"{c.freq.value}_D{di}K_MACD形态".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=5)
    macd = [x.cache['MACD']['macd'] for x in bars]

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

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def tas_macd_bc_V221201(c: CZSC, di: int = 1, n: int = 3, m: int = 50):
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
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}_MACD背驰".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=n+m)
    assert n >= 3, "近期窗口大小至少要大于3"

    v1 = "其他"
    v2 = "任意"
    if len(bars) == n + m:
        n_bars = bars[-n:]
        m_bars = bars[:m]
        assert len(n_bars) == n and len(m_bars) == m
        n_close = [x.close for x in n_bars]
        n_macd = [x.cache['MACD']['macd'] for x in n_bars]
        m_close = [x.close for x in m_bars]
        m_macd = [x.cache['MACD']['macd'] for x in m_bars]

        if n_macd[-1] > n_macd[-2] and min(n_close) < min(m_close) and min(n_macd) > min(m_macd):
            v1 = '底部'
        elif n_macd[-1] < n_macd[-2] and max(n_close) > max(m_close) and max(n_macd) < max(m_macd):
            v1 = '顶部'

        v2 = "红柱" if n_macd[-1] > 0 else "绿柱"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
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


def tas_ma_base_V221203(c: CZSC, di: int = 1, key="SMA5", th=100) -> OrderedDict:
    """MA 多空和方向信号，加距离限制

    **信号逻辑：**

    1. close > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下
    3. close 与 ma 的距离超过 th

    **信号列表：**

    - Signal('日线_D1T100_SMA5_多头_向上_远离_0')
    - Signal('日线_D1T100_SMA5_多头_向上_靠近_0')
    - Signal('日线_D1T100_SMA5_空头_向上_远离_0')
    - Signal('日线_D1T100_SMA5_空头_向下_远离_0')
    - Signal('日线_D1T100_SMA5_空头_向下_靠近_0')
    - Signal('日线_D1T100_SMA5_多头_向下_靠近_0')
    - Signal('日线_D1T100_SMA5_空头_向上_靠近_0')
    - Signal('日线_D1T100_SMA5_多头_向下_远离_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param key: 指定使用哪个Key来计算，必须是 `update_ma_cache` 中已经缓存的 key
    :param th: 距离阈值，单位 BP
    :return:
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}_{key.upper()}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    c = bars[-1].close
    m = bars[-1].cache[key]
    v1 = "多头" if c >= m else "空头"
    v2 = "向上" if bars[-1].cache[key] >= bars[-2].cache[key] else "向下"
    v3 = "远离" if (abs(c - m) / m) * 10000 > th else "靠近"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)
    s[signal.key] = signal.value
    return s


def tas_ma_round_V221206(c: CZSC, di: int = 1, key: str = "SMA60", th: int = 10) -> OrderedDict:
    """笔端点在均线附近

    **信号逻辑：**

    倒数第i笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近

    **信号列表：**

    - Signal('15分钟_D3TH10_碰SMA233_上碰_任意_任意_0')
    - Signal('15分钟_D3TH10_碰SMA233_下碰_任意_任意_0')

    :param c: CZSC对象
    :param di: 指定倒数第几笔
    :param key: 指定均线名称
    :param th: 笔的端点到均线的绝对价差 / 笔的价差 < th / 100 表示笔端点在均线附近
    :return: 信号识别结果
    """
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

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def tas_double_ma_V221203(c: CZSC, di: int = 1, ma1="SMA5", ma2='SMA10', th: int = 100) -> OrderedDict:
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
    :param ma1: 指定短期均线，必须是 `update_ma_cache` 中已经缓存的 key
    :param ma2: 指定长期均线，必须是 `update_ma_cache` 中已经缓存的 key
    :param th: ma1 相比 ma2 的距离阈值，单位 BP
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}_{ma1.upper()}{ma2.upper()}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    ma1v = bars[-1].cache[ma1]
    ma2v = bars[-1].cache[ma2]
    v1 = "多头" if ma1v >= ma2v else "空头"
    v2 = "强势" if (abs(ma1v - ma2v) / ma2v) * 10000 >= th else "弱势"

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


def tas_boll_bc_V221118(c: CZSC, di=1, n=3, m=10, line=3):
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
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}L{line}_BOLL背驰".split('_')

    bn = get_sub_elements(c.bars_raw, di=di, n=n)
    bm = get_sub_elements(c.bars_raw, di=di, n=m)

    d_c1 = min([x.low for x in bn]) <= min([x.low for x in bm])
    d_c2 = sum([x.close < x.cache['boll'][f'下轨{line}'] for x in bm]) > 1
    d_c3 = sum([x.close < x.cache['boll'][f'下轨{line}'] for x in bn]) == 0

    g_c1 = max([x.high for x in bn]) == max([x.high for x in bm])
    g_c2 = sum([x.close > x.cache['boll'][f'上轨{line}'] for x in bm]) > 1
    g_c3 = sum([x.close > x.cache['boll'][f'上轨{line}'] for x in bn]) == 0

    if d_c1 and d_c2 and d_c3:
        v1 = "一买"
    elif g_c1 and g_c2 and g_c3:
        v1 = "一卖"
    else:
        v1 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


# KDJ信号计算函数
# ======================================================================================================================
def update_kdj_cache(c: CZSC, **kwargs) -> None:
    """更新KDJ缓存

    :param c: CZSC对象
    :return:
    """
    fastk_period = kwargs.get('fastk_period', 9)
    slowk_period = kwargs.get('slowk_period', 3)
    slowd_period = kwargs.get('slowd_period', 3)

    min_count = fastk_period + slowk_period
    cache_key = f"KDJ({fastk_period},{slowk_period},{slowd_period})"
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 30:
        bars = c.bars_raw
        min_count = 0
    else:
        bars = c.bars_raw[-min_count-30:]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    close = np.array([x.close for x in bars])

    k, d = ta.STOCH(high, low, close, fastk_period=fastk_period, slowk_period=slowk_period, slowd_period=slowd_period)
    j = list(map(lambda x, y: 3*x - 2*y, k, d))

    for i in range(1, len(close) - min_count - 10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: {'k': k[-i], 'd': d[-i], 'j': j[-i]}})
        c.bars_raw[-i].cache = _c


def tas_kdj_base_V221101(c: CZSC, di: int = 1, key="KDJ(9,3,3)") -> OrderedDict:
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
    :param key: 指定使用哪个Key来计算，必须是 `update_kdj_cache` 中已经缓存的 key
    :return:
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_KDJ".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    kdj = bars[-1].cache[key]

    if kdj['j'] > kdj['k'] > kdj['d']:
        v1 = "多头"
    elif kdj['j'] < kdj['k'] < kdj['d']:
        v1 = "空头"
    else:
        v1 = "其他"

    v2 = "向上" if kdj['j'] >= bars[-2].cache[key]['j'] else "向下"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


# RSI信号计算函数
# ======================================================================================================================
def update_rsi_cache(c: CZSC, **kwargs) -> None:
    """更新RSI缓存

    相对强弱指数（RSI）是通过比较一段时期内的平均收盘涨数和平均收盘跌数来分析市场买沽盘的意向和实力，从而作出未来市场的走势。
    RSI在1978年6月由WellsWider创制。

    RSI = 100 × RS / (1 + RS) 或者 RSI=100－100÷(1+RS)
    RS = X天的平均上涨点数 / X天的平均下跌点数

    :param c: CZSC对象
    :return:
    """
    timeperiod = kwargs.get('timeperiod', 9)

    min_count = timeperiod + 5
    cache_key = f"RSI{timeperiod}"
    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < min_count + 30:
        bars = c.bars_raw
        min_count = 0
    else:
        bars = c.bars_raw[-min_count-30:]
    close = np.array([x.close for x in bars])

    rsi = ta.RSI(close, timeperiod=timeperiod)

    for i in range(1, len(close) - min_count - 10):
        _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
        _c.update({cache_key: rsi[-i]})
        c.bars_raw[-i].cache = _c


def tas_double_rsi_V221203(c: CZSC, di: int = 1, rsi1="RSI5", rsi2='RSI10') -> OrderedDict:
    """两个周期的RSI多空信号

    **信号逻辑：**

    1. rsi1 > rsi2，多头；反之，空头

    **信号列表：**

    - Signal('日线_D2K_RSI6RSI12_多头_任意_任意_0')
    - Signal('日线_D2K_RSI6RSI12_空头_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param rsi1: 指定短期RSI，必须是 `update_rsi_cache` 中已经缓存的 key
    :param rsi2: 指定长期RSI，必须是 `update_rsi_cache` 中已经缓存的 key
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_{rsi1.upper()}{rsi2.upper()}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    rsi1v = bars[-1].cache[rsi1]
    rsi2v = bars[-1].cache[rsi2]
    v1 = "多头" if rsi1v >= rsi2v else "空头"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s



