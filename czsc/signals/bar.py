# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/11 20:18
describe: bar 作为前缀，代表信号属于基础 K 线信号
"""
import numpy as np
from datetime import datetime
from typing import List
from loguru import logger
from deprecated import deprecated
from collections import OrderedDict
from czsc import envs, CZSC, Signal
from czsc.traders.base import CzscSignals
from czsc.objects import RawBar
from czsc.utils.sig import check_pressure_support, get_sub_elements, create_single_signal
from czsc.signals.tas import update_ma_cache


def bar_end_V221111(c: CZSC, k1='60分钟') -> OrderedDict:
    """分钟 K 线结束

    参数模板："{freq}_K线_结束"

    **信号列表：**

    - Signal('60分钟_K线_结束_否_任意_任意_0')
    - Signal('60分钟_K线_结束_是_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param k1: 分钟周期名称
    :return: s
    """
    k2, k3 = "K线", "结束"
    assert "分钟" in k1

    m = int(k1.replace("分钟", ""))
    dt: datetime = c.bars_raw[-1].dt
    v = "是" if dt.minute % m == 0 else "否"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v)


def bar_operate_span_V221111(c: CZSC, **kwargs) -> OrderedDict:
    """日内操作时间区间，c 必须是

    参数模板："{freq}_T{t1}#{t2}_时间区间"

    **信号列表：**

    - Signal('15分钟_T0935#1450_时间区间_是_任意_任意_0')
    - Signal('15分钟_T0935#1450_时间区间_否_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :return: s
    """
    t1 = kwargs.get("t1", "0935")
    t2 = kwargs.get("t2", "1450")
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_T{t1}#{t2}_时间区间".split("_")

    dt: datetime = c.bars_raw[-1].dt
    v = "是" if t1 <= dt.strftime("%H%M") <= t2 else "否"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v)


def bar_zdt_V230331(c: CZSC, **kwargs) -> OrderedDict:
    """计算倒数第di根K线的涨跌停信息

    参数模板："{freq}_D{di}_涨跌停V230331"

    **信号逻辑：**

    - close等于high大于等于前一根K线的close，近似认为是涨停；反之，跌停。

    **信号列表：**

    - Signal('15分钟_D1_涨跌停V230331_涨停_任意_任意_0')
    - Signal('15分钟_D1_涨跌停V230331_跌停_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs:
        - di: 倒数第 di 根 K 线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}_涨跌停V230331".split("_")
    v1 = "其他"
    if len(c.bars_raw) < di + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2 = c.bars_raw[-di], c.bars_raw[-di - 1]
    if b1.close == b1.high >= b2.close:
        v1 = "涨停"
    elif b1.close == b1.low <= b2.close:
        v1 = "跌停"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_vol_grow_V221112(c: CZSC, **kwargs) -> OrderedDict:
    """倒数第 i 根 K 线的成交量相比于前 N 根 K 线放量

    参数模板："{freq}_D{di}K{n}B_放量V221112"

    **信号逻辑: **

    放量的定义为，倒数第i根K线的量能 / 过去N根的平均量能，在2-4倍之间。

    **信号列表：**

    - Signal('15分钟_D1K5B_放量V221112_否_任意_任意_0')
    - Signal('15分钟_D1K5B_放量V221112_是_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - di: 倒数第i根K线
        - n: 过去N根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 2))
    n = int(kwargs.get("n", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}K{n}B_放量V221112".split("_")

    if len(c.bars_raw) < di + n + 10:
        v1 = "其他"
    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=n + 1)
        assert len(bars) == n + 1

        mean_vol = sum([x.vol for x in bars[:-1]]) / n
        v1 = "是" if mean_vol * 4 >= bars[-1].vol >= mean_vol * 2 else "否"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_fang_liang_break_V221216(c: CZSC, **kwargs) -> OrderedDict:
    """放量向上突破并回踩指定均线，贡献者：琅盎

    参数模板："{freq}_D{di}TH{th}#{ma_type}#{timeperiod}_突破V221216"
    **信号逻辑：**

    1. 放量突破
    2. 缩量回踩，最近一根K线的成交量小于前面一段时间的均量

    **信号列表：**

    - Signal('15分钟_D1TH300#SMA#233_突破V221216_放量突破_缩量回踩_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param ma_type: 指定均线的类型，默认为SMA
    :param timeperiod: 指定均线的周期，默认为233
    :param th: 当前最低价同指定均线的距离阈值，单位 BP
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    th = int(kwargs.get("th", 300))
    ma_type = kwargs.get("ma_type", "SMA").upper()
    timeperiod = int(kwargs.get("timeperiod", 233))

    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}#{ma_type}#{timeperiod}_突破V221216".split('_')

    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)

    def _vol_fang_liang_break(bars: List[RawBar]):
        if len(bars) <= 4:
            return "其他", "其他"

        # 条件1：放量突破
        ma1v = bars[-1].cache[cache_key]
        c1 = "放量突破" if bars[-1].vol >= bars[-2].vol and bars[-1].close > ma1v else "其他"

        # 条件2：缩量回踩
        vol_min = np.mean([x.vol for x in bars[:-1]])
        distance = all(abs(x.close / ma1v - 1) * 10000 <= th for x in bars[:-1])

        if bars[-1].close >= ma1v and bars[-1].vol < vol_min and distance:
            c2 = "缩量回踩"
        else:
            c2 = "其他"

        return c1, c2

    for n in (5, 6, 7, 8, 9):
        _bars = get_sub_elements(c.bars_raw[300:], di=di, n=n)
        v1, v2 = _vol_fang_liang_break(_bars)
        if v1 != "其他":
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def bar_mean_amount_V221112(c: CZSC, **kwargs) -> OrderedDict:
    """截取一段时间内的平均成交金额分类信号

    参数模板："{freq}_D{di}K{n}B均额_{th1}至{th2}千万"

    **信号逻辑: **

    倒数第i根K线向前n根K线的成交金额均值在 th1 和 th2 之间

    **信号列表：**

    - Signal('15分钟_D2K20B均额_1至4千万_否_任意_任意_0')
    - Signal('15分钟_D2K20B均额_1至4千万_是_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止的倒数第 i 根
    :param n: 向前看 n 根
    :param th1: 成交金额下限，单位：千万
    :param th2: 成交金额上限，单位：千万
    :return: s
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 10))
    th1 = int(kwargs.get("th1", 1))
    th2 = int(kwargs.get("th2", 4))

    k1, k2, k3 = str(c.freq.value), f"D{di}K{n}B均额", f"{th1}至{th2}千万"

    v1 = "其他"
    if len(c.bars_raw) > di + n + 5:
        try:
            bars = get_sub_elements(c.bars_raw, di=di, n=n)
            assert len(bars) == n
            m = sum([x.amount for x in bars]) / n
            v1 = "是" if th2 >= m / 10000000 >= th1 else "否"

        except Exception as e:
            msg = f"{c.symbol} - {c.bars_raw[-1].dt} fail: {e}"
            if envs.get_verbose():
                logger.exception(msg)
            else:
                logger.warning(msg)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_cross_ps_V221112(c: CZSC, **kwargs) -> OrderedDict:
    """倒数第 di 根 K 线穿越支撑、压力位的数量【慎用，非常耗时】

    参数模板："{freq}_D{di}K_N{num}"

    **信号逻辑：**

    1. 计算最近600根K线的支撑、压力位列表；
    2. 如果dik是阳性，切上穿 num 个以上的压力位，择时多头；反之，空头。

    **信号列表：**

    - Signal('15分钟_D2K_N3_空头_任意_任意_0')
    - Signal('15分钟_D2K_N3_多头_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算在倒数第 di 根
    :param num: 阈值
    :return: s
    """
    di = int(kwargs.get("di", 1))
    num = int(kwargs.get("num", 3))

    k1, k2, k3 = str(c.freq.value), f"D{di}K", f"N{num}"

    if len(c.bars_raw) < 300 + di:
        v1 = '其他'

    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=600)
        pres = check_pressure_support(bars, q_seq=[x / 100 for x in list(range(0, 100, 3))])
        last = bars[-1]

        cnt = 0
        for x in pres['关键位']:
            if last.close > x > last.open:
                assert cnt >= 0
                cnt += 1

            if last.close < x < last.open:
                assert cnt <= 0
                cnt -= 1

        if cnt >= num:
            v1 = "多头"
        elif cnt <= -num:
            v1 = "空头"
        else:
            v1 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def bar_section_momentum_V221112(c: CZSC, **kwargs) -> OrderedDict:
    """获取某个区间（固定K线数量）的动量强弱

    参数模板："{freq}_D{di}K{n}B_阈值{th}BP"

    **信号列表：**

    - Signal('15分钟_D2K10B_阈值100BP_下跌_强势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_弱势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_弱势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_弱势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_弱势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_强势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_强势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_强势_高波动_0')

    :param c: CZSC对象
    :param di: 区间结束K线位置，倒数
    :param n: 取近n根K线
    :param th: 动量强弱划分的阈值，单位 BP
    :return: s
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 10))
    th = int(kwargs.get("th", 100))

    k1, k2, k3 = f"{c.freq.value}_D{di}K{n}B_阈值{th}BP".split('_')

    if len(c.bars_raw) < di + n:
        v1 = v2 = v3 = "其他"
    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=n)
        bp = (bars[-1].close / bars[0].open - 1) * 10000
        wave = (max([x.high for x in bars]) / min([x.low for x in bars]) - 1) * 10000
        rate = 0 if abs(bp) == 0 else abs(wave) / abs(bp)

        v1 = "上涨" if bp >= 0 else "下跌"
        v2 = "强势" if abs(bp) >= th else "弱势"
        v3 = "高波动" if rate >= 3 else "低波动"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def bar_accelerate_V221110(c: CZSC, **kwargs) -> OrderedDict:
    """辨别加速走势

    参数模板："{freq}_D{di}W{window}_加速V221110"

    **信号逻辑：**

    - 上涨加速：窗口内最后一根K线的收盘在窗口区间的80%以上；且窗口内阳线数量占比超过80%
    - 下跌加速：窗口内最后一根K线的收盘在窗口区间的20%以下；且窗口内阴线数量占比超过80%

    **信号列表：**

    - Signal('60分钟_D1W13_加速V221110_上涨_任意_任意_0')
    - Signal('60分钟_D1W13_加速V221110_下跌_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - di: 区间结束K线位置，倒数
        - window: 取截止di的近window根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    window = int(kwargs.get("window", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{window}_加速V221110".split('_')

    v1 = "其他"
    if len(c.bars_raw) > di + window + 10:
        bars: List[RawBar] = get_sub_elements(c.bars_raw, di=di, n=window)
        hhv = max([x.high for x in bars])
        llv = min([x.low for x in bars])

        c1 = bars[-1].close > llv + (hhv - llv) * 0.8
        c2 = bars[-1].close < llv + (hhv - llv) * 0.2

        red_pct = sum([1 if x.close > x.open else 0 for x in bars]) / len(bars) >= 0.8
        green_pct = sum([1 if x.close < x.open else 0 for x in bars]) / len(bars) >= 0.8

        if c1 and red_pct:
            v1 = "上涨"

        if c2 and green_pct:
            v1 = "下跌"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_accelerate_V221118(c: CZSC, **kwargs) -> OrderedDict:
    """辨别加速走势

    参数模板："{freq}_D{di}W{window}#{ma_type}#{timeperiod}_加速V221118"

    **信号逻辑：**

    上涨加速指窗口内K线收盘价全部大于 ma1，且 close 与 ma1 的距离不断正向放大；反之为下跌加速。

    **信号列表：**

    - Signal('日线_D1W13#SMA#10_加速V221118_上涨_任意_任意_0')
    - Signal('日线_D1W13#SMA#10_加速V221118_下跌_任意_任意_0')

    :param c: CZSC对象
    :param di: 取近n根K线为截止
    :param ma_type: MA类型，支持SMA、EMA、WMA、DEMA、TEMA、TRIMA、KAMA、MAMA、T3
    :param timeperiod: MA的周期
    :param window: 识别加速走势的窗口大小
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    window = int(kwargs.get("window", 13))
    ma_type = kwargs.get("ma_type", "SMA").upper()
    timeperiod = int(kwargs.get("timeperiod", 10))

    assert window > 3, "辨别加速，至少需要3根以上K线"
    k1, k2, k3 = c.freq.value, f"D{di}W{window}#{ma_type}#{timeperiod}", f"加速V221118"

    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    bars = get_sub_elements(c.bars_raw, di=di, n=window)
    delta = [x.close - x.cache[cache_key] for x in bars]

    if all(x > 0 for x in delta) and delta[-1] > delta[-2] > delta[-3]:
        v1 = "上涨"
    elif all(x < 0 for x in delta) and delta[-1] < delta[-2] < delta[-3]:
        v1 = "下跌"
    else:
        v1 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_zdf_V221203(c: CZSC, **kwargs) -> OrderedDict:
    """单根K线的涨跌幅区间

    参数模板："{freq}_D{di}{mode}_{t1}至{t2}"

    **信号列表：**

    - Signal('日线_D1ZF_300至600_满足_任意_任意_0')
    - Signal('日线_D1DF_300至600_满足_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止倒数第i根K线
    :param mode: 模式，ZF 表示涨幅，DF 表示跌幅
    :param span: 区间大小
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    mode = kwargs.get("mode", "ZF").upper()
    span = kwargs.get("span", (300, 600))
    t1, t2 = span
    assert t2 > t1 > 0

    k1, k2, k3 = f"{c.freq.value}_D{di}{mode}_{t1}至{t2}".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    if mode == "ZF":
        edge = (bars[-1].close / bars[-2].close - 1) * 10000
    else:
        assert mode == 'DF'
        edge = (1 - bars[-1].close / bars[-2].close) * 10000

    v1 = "满足" if t2 >= edge >= t1 else "其他"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_fake_break_V230204(c: CZSC, **kwargs) -> OrderedDict:
    """假突破

    参数模板："{freq}_D{di}N{n}M{m}_假突破"

    **信号描述：**

    1. 向下假突破，最近N根K线的滑动M窗口出现过大幅下跌破K线重叠中枢，随后几根K线快速拉回，看多；
    2. 反之，向上假突破，看空。

    **信号列表：**

    - Signal('15分钟_D1N20M5_假突破_看空_任意_任意_0')
    - Signal('15分钟_D1N20M5_假突破_看多_任意_任意_0')

    :param c: CZSC 对象
    :param di: 从最新的第几个 bar 开始计算
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 20))
    m = int(kwargs.get('m', 5))
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}_假突破".split("_")

    v1 = '其他'
    last_bars: List[RawBar] = get_sub_elements(c.bars_raw, di=di, n=n)

    def __is_overlap(_bars):
        """判断是否是重叠，如果是重叠，返回True和中枢的上下轨"""
        if min([bar.high for bar in _bars]) > max([bar.low for bar in _bars]):
            return True, min([bar.low for bar in _bars]), max([bar.high for bar in _bars])
        else:
            return False, None, None

    if len(last_bars) != n or last_bars[-1].solid < last_bars[-1].upper + last_bars[-1].lower:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 找出最近N根K线的滑动M窗口出现过K线重叠中枢
    right_bars = []
    dd = 0
    gg = 0
    for i in range(m, n - m):
        _overlap, dd, gg = __is_overlap(last_bars[-i - m:-i])
        if _overlap:
            right_bars = last_bars[-i:]
            break

    if last_bars[-1].close > last_bars[-1].open:

        # 条件1：收盘价新高或者最高价新高
        c1_a = last_bars[-1].high == max([bar.high for bar in last_bars])
        c1_b = last_bars[-1].close == max([bar.close for bar in last_bars])
        c1 = c1_a or c1_b

        # 条件2：随后几根K线破中枢DD快速拉回
        c2 = 0 < min([bar.low for bar in right_bars]) < dd if right_bars else False

        if c1 and c2:
            v1 = "看多"

    if last_bars[-1].close < last_bars[-1].open:
        # 条件1：收盘价新低或者最低价新低
        c1_a = last_bars[-1].low == min([bar.low for bar in last_bars])
        c1_b = last_bars[-1].close == min([bar.close for bar in last_bars])
        c1 = c1_a or c1_b

        # 条件2：随后几根K线破中枢GG快速拉回
        c2 = max([bar.high for bar in right_bars]) > gg > 0 if right_bars else False

        if c1 and c2:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_single_V230214(c: CZSC, **kwargs) -> OrderedDict:
    """单根K线的状态

    参数模板："{freq}_D{di}T{t}_状态"

    **信号描述：**

    1. 上涨阳线，下跌阴线；
    2. 长实体，长上影，长下影，其他；

    **信号列表：**

    - Signal('日线_D2T10_状态_阴线_长实体_任意_0')
    - Signal('日线_D2T10_状态_阳线_长实体_任意_0')
    - Signal('日线_D2T10_状态_阴线_长上影_任意_0')
    - Signal('日线_D2T10_状态_阳线_长上影_任意_0')
    - Signal('日线_D2T10_状态_阴线_长下影_任意_0')
    - Signal('日线_D2T10_状态_阳线_长下影_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param kwargs:
        t: 长实体、长上影、长下影的阈值，默认为 1.0
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    t = int(kwargs.get("t", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}T{t}_状态".split("_")

    if len(c.bars_raw) < di + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    k = c.bars_raw[-di]
    v1 = "阳线" if k.close > k.open else "阴线"

    if k.solid > (k.upper + k.lower) * t / 10:
        v2 = "长实体"
    elif k.upper > (k.solid + k.lower) * t / 10:
        v2 = "长上影"
    elif k.lower > (k.solid + k.upper) * t / 10:
        v2 = "长下影"
    else:
        v2 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def bar_amount_acc_V230214(c: CZSC, **kwargs) -> OrderedDict:
    """N根K线总成交额

    参数模板："{freq}_D{di}N{n}_累计超{t}千万"

    **信号描述：**

    1. 获取截至倒数第di根K线的前n根K线，计算总成交额，如果大于 t 千万，则为是，否则为否

    **信号列表：**

    - Signal('日线_D2N1_累计超10千万_是_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: 前几根K线
    :param kwargs:
        t: 总成交额阈值
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 2))
    n = int(kwargs.get('n', 5))
    t = int(kwargs.get('t', 10))
    k1, k2, k3, v1 = f"{c.freq.value}", f"D{di}N{n}", f"累计超{t}千万", "其他"
    if len(c.bars_raw) <= di + n + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di, n)
    assert len(_bars) == n
    v1 = "是" if sum([x.amount for x in _bars]) > (t * 1e7) else "否"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_big_solid_V230215(c: CZSC, **kwargs):
    """窗口内最大实体K线的中间价区分多空

    参数模板："{freq}_D{di}N{n}_MID"

    **信号逻辑：**

    1. 找到窗口内最大实体K线, 据其中间位置区分多空

    **信号列表：**

    - Signal('日线_D1N10_MID_看空_大阳_任意_0')
    - Signal('日线_D1N10_MID_看空_大阴_任意_0')
    - Signal('日线_D1N10_MID_看多_大阴_任意_0')
    - Signal('日线_D1N10_MID_看多_大阳_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第i根K线
    :param n: 窗口大小
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 20))

    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}_MID".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)

    # 找到窗口内最大实体K线
    max_i = np.argmax([x.solid for x in _bars])
    max_solid_bar = _bars[max_i]
    max_solid_mid = min(max_solid_bar.open, max_solid_bar.close) + 0.5 * max_solid_bar.solid

    v1 = '看多' if c.bars_raw[-1].close > max_solid_mid else '看空'
    v2 = '大阳' if max_solid_bar.close > max_solid_bar.open else '大阴'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def bar_vol_bs1_V230224(c: CZSC, **kwargs):
    """量价配合的高低点判断

    参数模板："{freq}_D{di}N{n}量价_BS1辅助"

    **信号逻辑：**

    1. 高点看空：窗口内最近一根K线上影大于下影的两倍，同时最高价和成交量同时创新高
    2. 反之，低点看多

    **信号列表：**

    - Signal('15分钟_D2N34量价_BS1辅助_看多_任意_任意_0')
    - Signal('15分钟_D2N34量价_BS1辅助_看空_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第i根K线
    :param n: 窗口大小
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 20))

    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}量价_BS1辅助".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    mean_vol = np.mean([x.amount for x in _bars])

    short_c1 = _bars[-1].high == max([x.high for x in _bars]) and _bars[-1].upper > 2 * _bars[-1].lower > 0
    short_c2 = _bars[-1].amount > mean_vol * 3

    long_c1 = _bars[-1].low == min([x.low for x in _bars]) and _bars[-1].lower > 2 * _bars[-1].upper > 0
    long_c2 = _bars[-1].amount < mean_vol * 0.7

    if short_c1 and short_c2:
        v1 = '看空'
    elif long_c1 and long_c2:
        v1 = '看多'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_reversal_V230227(c: CZSC, **kwargs) -> OrderedDict:
    """判断最近一根K线是否具有反转迹象

    参数模板："{freq}_D{di}A{avg_bp}_反转V230227"

    **信号逻辑：**

    - 看多：当前K线为阴线，或阳线长上影; 且截止前一根K线，连续 3 / 5 / 8根K线累计涨幅超过 avg_bp * n，或 连续13根K线都是阳线
    - 反之，看空

    **信号列表：**

    - Signal('15分钟_D1A300_反转V230227_看多_任意_任意_0')
    - Signal('15分钟_D1A300_反转V230227_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param avg_bp: 平均单根K线的涨跌幅，用于判断是否是反转
    :return:
    """
    di = int(kwargs.get('di', 1))
    avg_bp = int(kwargs.get('avg_bp', 300))

    k1, k2, k3 = str(c.freq.value), f"D{di}A{avg_bp}", "反转V230227"
    v1 = "其他"
    _bars = get_sub_elements(c.bars_raw, di=di, n=14)

    if len(_bars) != 14:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bar = _bars[-1]
    left_bar = _bars[:-1]

    # 阳线长上影
    last_bar_up_c1 = last_bar.close > last_bar.open and last_bar.upper > 2 * max(last_bar.solid, last_bar.lower)

    # 阴线长下影
    last_bar_dn_c1 = last_bar.close < last_bar.open and last_bar.lower > 2 * max(last_bar.solid, last_bar.upper)

    if last_bar.close < last_bar.open or last_bar_up_c1:
        # 连续3 / 5 / 8根K线累计涨幅超过 avg_bp * n / 10000
        up_c1 = (left_bar[-1].close / left_bar[-3].open - 1) / 3 > avg_bp / 10000
        up_c2 = (left_bar[-1].close / left_bar[-5].open - 1) / 5 > avg_bp / 10000
        up_c3 = (left_bar[-1].close / left_bar[-8].open - 1) / 8 > avg_bp / 10000

        # 连续13根K线都是阳线
        up_c4 = all(bar.close > bar.open for bar in left_bar)

        if any([up_c1, up_c2, up_c3, up_c4]):
            v1 = "看空"

    if last_bar.close > last_bar.open or last_bar_dn_c1:
        # 连续3 / 5 / 8根K线累计跌幅超过 avg_bp * n / 10000
        dn_c1 = (left_bar[-1].close / left_bar[-3].open - 1) / 3 < -avg_bp / 10000
        dn_c2 = (left_bar[-1].close / left_bar[-5].open - 1) / 5 < -avg_bp / 10000
        dn_c3 = (left_bar[-1].close / left_bar[-8].open - 1) / 8 < -avg_bp / 10000

        # 连续13根K线都是阴线
        dn_c4 = all(bar.close < bar.open for bar in left_bar)

        if any([dn_c1, dn_c2, dn_c3, dn_c4]):
            v1 = "看多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_bpm_V230227(c: CZSC, **kwargs) -> OrderedDict:
    """以BP为单位的绝对动量

    参数模板："{freq}_D{di}N{n}T{th}_绝对动量V230227"

    **信号逻辑：**

    1. 以BP为单位的绝对动量，计算最近n根K线的涨幅，如果大于th，则为超强，否则为强势；
    2. 反之，如果小于-th，则为超弱，否则为弱势

    **信号列表：**

    - Signal('15分钟_D2N5T300_绝对动量V230227_弱势_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_强势_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_超强_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_超弱_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
        - di: 倒数第几根K线
        - n: 连续多少根K线
        - th: 超过多少bp
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 20))
    th = int(kwargs.get("th", 1000))
    freq = c.freq.value

    k1, k2, k3 = f"{freq}_D{di}N{n}T{th}_绝对动量V230227".split("_")
    if len(c.bars_raw) < di + n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    bp = (_bars[-1].close / _bars[0].open - 1) * 10000
    if bp > 0:
        v1 = "超强" if bp > th else "强势"
    else:
        v1 = "超弱" if abs(bp) > th else "弱势"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_time_V230327(c: CZSC, **kwargs):
    """K线日内时间分段信号

    参数模板："{freq}_日内时间_分段V230327"

    **信号逻辑：**

    - 60分钟或30分钟K线，按日内出现顺序分段

    **信号列表：**

    - Signal('60分钟_日内时间_分段V230327_第1段_任意_任意_0')
    - Signal('60分钟_日内时间_分段V230327_第2段_任意_任意_0')
    - Signal('60分钟_日内时间_分段V230327_第3段_任意_任意_0')
    - Signal('60分钟_日内时间_分段V230327_第4段_任意_任意_0')

    :param c: CZSC 对象
    :param kwargs:
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_日内时间_分段V230327".split("_")
    v1 = "其他"
    assert c.freq.value in ['30分钟', '60分钟'], "bar_time_V230327 仅支持30分钟和60分钟的K线"
    if len(c.bars_raw) < 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    cache_key = 'bar_time_V230327#time_spans'
    time_spans = c.cache.get(cache_key, None)
    if time_spans is None:
        bars = c.bars_raw[-100:]
        time_spans = sorted(list(set([x.dt.strftime('%H:%M') for x in bars])))
        c.cache[cache_key] = time_spans

    v1 = f"第{time_spans.index(c.bars_raw[-1].dt.strftime('%H:%M')) + 1}段"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_weekday_V230328(c: CZSC, **kwargs):
    """K线周内时间分段信号

    参数模板："{freq}_周内时间_分段V230328"

    **信号逻辑：**

    - 按周内日线出现顺序分段

    **信号列表：**

    - Signal('60分钟_周内时间_分段V230328_周一_任意_任意_0')
    - Signal('60分钟_周内时间_分段V230328_周二_任意_任意_0')
    - Signal('60分钟_周内时间_分段V230328_周三_任意_任意_0')
    - Signal('60分钟_周内时间_分段V230328_周四_任意_任意_0')
    - Signal('60分钟_周内时间_分段V230328_周五_任意_任意_0')

    :param c: CZSC 对象
    :param kwargs:
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_周内时间_分段V230328".split("_")
    v1 = "其他"

    if len(c.bars_raw) < 20:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    weekday_map = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
    v1 = weekday_map[c.bars_raw[-1].dt.weekday()]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_r_breaker_V230326(c: CZSC, **kwargs):
    """RBreaker日内回转交易

    参数模板："{freq}_RBreaker_BS辅助V230326"

    **信号逻辑：**

    参见：https://www.myquant.cn/docs/python_strategyies/425

    空仓时：突破策略
    空仓时，当盘中价格>突破买入价，则认为上涨的趋势还会继续，开仓做多；
    空仓时，当盘中价格<突破卖出价，则认为下跌的趋势还会继续，开仓做空。

    持仓时：反转策略
    持多单时：当日内最高价>观察卖出价后，盘中价格回落，跌破反转卖出价构成的支撑线时，采取反转策略，即做空；
    持空单时：当日内最低价<观察买入价后，盘中价格反弹，超过反转买入价构成的阻力线时，采取反转策略，即做多。

    **信号列表：**

    - Signal('日线_RBreaker_BS辅助V230326_做多_反转_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做空_趋势_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做多_趋势_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做空_反转_任意_0')

    :return: 信号字典
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_RBreaker_BS辅助V230326".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    # 计算六个价位
    H, C, L = c.bars_raw[-2].high, c.bars_raw[-2].close, c.bars_raw[-2].low
    P = (H + C + L) / 3
    break_buy = H + 2 * P - 2 * L
    see_sell = P + H - L
    verse_sell = 2 * P - L
    verse_buy = 2 * P - H
    see_buy = P - (H - L)
    break_sell = L - 2 * (H - P)

    # 根据价格位置判断信号
    current_bar = c.bars_raw[-1]
    if current_bar.close > break_buy:
        v1 = '做多'
        v2 = '趋势'
    elif current_bar.close < break_sell:
        v1 = '做空'
        v2 = '趋势'
    elif current_bar.high > see_sell and current_bar.close < verse_sell:
        v1 = '做空'
        v2 = '反转'
    elif current_bar.low < see_buy and current_bar.close > verse_buy:
        v1 = '做多'
        v2 = '反转'
    else:
        v1 = '其他'
        v2 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def bar_dual_thrust_V230403(c: CZSC, **kwargs):
    """Dual Thrust 通道突破

    参数模板："{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403"

    **信号逻辑：**

    参见：https://www.myquant.cn/docs/python_strategyies/424

    其核心思想是定义一个区间，区间的上界和下界分别为支撑线和阻力线。当价格超过上界时，看多，跌破下界，看空。

    **信号列表：**

    - Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看空_任意_任意_0')
    - Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - N: 前N天的数据
        - K1: 参数，根据经验优化
        - K2: 参数，根据经验优化
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    N = int(kwargs.get('N', 5))
    K1 = int(kwargs.get('K1', 20))
    K2 = int(kwargs.get('K2', 20))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di+1, n=N+1)
    HH = max([i.high for i in bars])
    HC = max([i.close for i in bars])
    LC = min([i.close for i in bars])
    LL = min([i.low for i in bars])
    Range = max(HH - LC, HC - LL)

    current_bar = c.bars_raw[-di]
    buy_line = current_bar.open + Range * K1 / 100    # 上轨
    sell_line = current_bar.open - Range * K2 / 100   # 下轨

    # 根据价格位置判断信号
    if current_bar.close > buy_line:
        v1 = '看多'
    elif current_bar.close < sell_line:
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



