# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/11 20:18
describe: bar 作为前缀，代表信号属于基础 K 线信号
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List
from loguru import logger
from deprecated import deprecated
from collections import OrderedDict
from czsc import envs, CZSC, Signal
from czsc.traders.base import CzscSignals
from czsc.objects import RawBar
from czsc.utils.sig import check_pressure_support
from czsc.signals.tas import update_ma_cache, update_macd_cache
from czsc.utils.bar_generator import freq_end_time
from czsc.utils import single_linear, freq_end_time, get_sub_elements, create_single_signal


def bar_single_V230506(c: CZSC, **kwargs) -> OrderedDict:
    """单K趋势因子辅助判断买卖点

    参数模板："{freq}_D{di}单K趋势N{n}_BS辅助V230506"

     **信号逻辑：**

    1. 定义趋势因子：(收盘价 / 开盘价 -1) / 成交量
    2. 选取最近100根K线，计算趋势因子，分成n层

     **信号列表：**

    - Signal('15分钟_D1单K趋势N5_BS辅助V230506_第3层_任意_任意_0')
    - Signal('15分钟_D1单K趋势N5_BS辅助V230506_第4层_任意_任意_0')
    - Signal('15分钟_D1单K趋势N5_BS辅助V230506_第2层_任意_任意_0')
    - Signal('15分钟_D1单K趋势N5_BS辅助V230506_第1层_任意_任意_0')
    - Signal('15分钟_D1单K趋势N5_BS辅助V230506_第5层_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 5))
    assert n <= 20, "n 的取值范围为 1~20，分层数量不宜太多"
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}单K趋势N{n}_BS辅助V230506".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 100 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    factors = [(x.close / x.open - 1) / x.vol for x in bars]
    q = pd.cut(factors, n, labels=list(range(1, n+1)), precision=5, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"第{q}层")


def bar_triple_V230506(c: CZSC, **kwargs) -> OrderedDict:
    """三K加速形态配合成交量变化

    参数模板："{freq}_D{di}三K加速_裸K形态V230506"

     **信号逻辑：**

    1. 连续三根阳线，【三连涨】，如果高低点不断创新高，【新高涨】
    2. 连续三根阴线，【三连跌】，如果高低点不断创新低，【新低跌】
    3. 加入成交量变化的判断，成交量逐渐放大 或 成交量逐渐缩小

     **信号列表：**

    - Signal('15分钟_D1三K加速_裸K形态V230506_三连涨_量柱无序_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_三连跌_量柱无序_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新高涨_依次放量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新低跌_依次缩量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新低跌_量柱无序_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_三连涨_依次放量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_三连跌_依次放量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新低跌_依次放量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_三连跌_依次缩量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新高涨_依次缩量_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_新高涨_量柱无序_任意_0')
    - Signal('15分钟_D1三K加速_裸K形态V230506_三连涨_依次缩量_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}三K加速_裸K形态V230506".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b3, b2, b1 = get_sub_elements(c.bars_raw, di=di, n=3)

    if b1.close > b1.open and b2.close > b2.open and b3.close > b3.open:
        v1 = '三连涨'
        if b1.high > b2.high > b3.high and b1.low > b2.low > b3.low:
            v1 = "新高涨"

    if b1.close < b1.open and b2.close < b2.open and b3.close < b3.open:
        v1 = '三连跌'
        if b1.high < b2.high < b3.high and b1.low < b2.low < b3.low:
            v1 = "新低跌"

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if b1.vol > b2.vol > b3.vol:
        v2 = '依次放量'
    elif b1.vol < b2.vol < b3.vol:
        v2 = '依次缩量'
    else:
        v2 = '量柱无序'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def bar_end_V221211(c: CZSC, freq1='60分钟', **kwargs) -> OrderedDict:
    """判断分钟 K 线是否结束

    参数模板："{freq}_{freq1}结束_BS辅助221211"

    **信号逻辑：**

    以 freq 为基础周期，freq1 为大周期，判断 freq1 K线是否结束。
    如果结束，返回信号值为 "闭合"，否则返回 "未闭x"，x 为未闭合的次数。

    **信号列表：**

    - Signal('15分钟_60分钟结束_BS辅助221211_未闭1_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_未闭2_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_未闭3_任意_任意_0')
    - Signal('15分钟_60分钟结束_BS辅助221211_闭合_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param freq1: 分钟周期名称
    :return: s
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{freq1}结束_BS辅助221211".split('_')
    assert "分钟" in freq1

    c1_dt = freq_end_time(c.bars_raw[-1].dt, freq1)
    i = 0
    for bar in c.bars_raw[::-1]:
        _edt = freq_end_time(bar.dt, freq1)
        if _edt != c1_dt:
            break
        i += 1

    if c1_dt == c.bars_raw[-1].dt:
        v = "闭合"
    else:
        v = "未闭{}".format(i)
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v)


def bar_operate_span_V221111(c: CZSC, **kwargs) -> OrderedDict:
    """日内操作时间区间，c 必须是基础周期的 CZSC 对象

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


@deprecated(version='1.0.0', reason="计算耗时，逻辑不严谨")
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


def bar_zt_count_V230504(c: CZSC, **kwargs) -> OrderedDict:
    """窗口内涨停计数

    参数模板："{freq}_D{di}W{window}涨停计数_裸K形态V230504"

     **信号逻辑：**

    1. 连续三根阳线，且高低点不断创新高，看多
    2. 连续三根阴线，且高低点不断创新低，看空

     **信号列表：**

    - Signal('日线_D1W5涨停计数_裸K形态V230504_1次_连续0次_任意_0')
    - Signal('日线_D1W5涨停计数_裸K形态V230504_2次_连续1次_任意_0')
    - Signal('日线_D1W5涨停计数_裸K形态V230504_3次_连续2次_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    di = int(kwargs.get("di", 1))
    window = int(kwargs.get("window", 5))
    freq = c.freq.value
    assert freq in ['日线']
    k1, k2, k3 = f"{freq}_D{di}W{window}涨停计数_裸K形态V230504".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 7 + di + window:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=window)
    c1 = []
    cc = 0
    for b1, b2 in zip(bars[:-1], bars[1:]):
        if b2.close > b1.close * 1.07 and b2.close == b2.high:
            c1.append(1)
        else:
            c1.append(0)

        if len(c1) >= 2 and c1[-1] == 1 and c1[-2] == 1:
            cc += 1

    if sum(c1) == 0:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"{sum(c1)}次", v2=f"连续{cc}次")


def bar_channel_V230508(c: CZSC, **kwargs) -> OrderedDict:
    """N日内小阴小阳通道内运行

    参数模板："{freq}_D{di}M{m}_通道V230507"

    **信号逻辑：**

    1. 取N日内最高价和最低价，计算通道上下轨斜率；
    2. 看多：上轨斜率大于0，下轨斜率大于0，且内部K线的涨跌幅在M以内
    3. 看空：上轨斜率小于0，下轨斜率小于0，且内部K线的涨跌幅在M以内

    **信号列表：**

    - Signal('日线_D2M600_通道V230507_看空_任意_任意_0')
    - Signal('日线_D2M600_通道V230507_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 20))
    m = int(kwargs.get("m", 600))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}M{m}_通道V230507".split('_')
    v1 = "其他"

    if len(c.bars_raw) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)

    if any(abs(x.close / x.open - 1) * 10000 > m for x in bars):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    res_high = single_linear([x.high for x in bars])
    res_low = single_linear([x.low for x in bars])
    high_right = max(x.high for x in bars[-3:])
    low_right = min(x.low for x in bars[-3:])
    max_high = max(x.high for x in bars)
    min_low = min(x.low for x in bars)

    if not (res_high['r2'] > 0.8 and res_low['r2'] > 0.8):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if res_high['slope'] > 0 and res_low['slope'] > 0 and high_right == max_high:
        v1 = "看多"

    if res_high['slope'] < 0 and res_low['slope'] < 0 and low_right == min_low:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_tnr_V230630(c: CZSC, **kwargs) -> OrderedDict:
    """趋势噪音指标（TNR，Trend to Noise Rate）

    参数模板："{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630"

    **信号逻辑：**

    TNR计算公式：取N根K线，首尾两个close的绝对差值 除以 相邻两个close的绝对差值累计。

    噪音变化判断，如果 t 时刻的 TNR > 过去k个TNR的均值，则说明噪音在减少，此时趋势较强；反之，噪音在增加，此时趋势较弱。

    **信号列表：**

    - Signal('15分钟_D1TNR14K3_趋势V230630_噪音减少_任意_任意_0')
    - Signal('15分钟_D1TNR14K3_趋势V230630_噪音增加_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: TNR指标的参数
        - k: 过去k个TNR的均值

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    k = int(kwargs.get('k', 3))
    freq = c.freq.value

    # 更新缓存
    cache_key = f"TNR{timeperiod}"
    for i, bar in enumerate(c.bars_raw, 0):
        if cache_key in bar.cache:
            continue
        if i < timeperiod:
            bar.cache[cache_key] = 0
        else:
            _bars = c.bars_raw[max(0, i - timeperiod):i + 1]
            sum_abs = sum([abs(_bars[j].close - _bars[j - 1].close) for j in range(1, len(_bars))])
            bar.cache[cache_key] = 0 if sum_abs == 0 else abs(_bars[-1].close - _bars[0].close) / sum_abs

    k1, k2, k3 = f"{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=k)
    delta_tnr = bars[-1].cache[cache_key] - np.mean([bar.cache[cache_key] for bar in bars])
    v1 = "噪音减少" if delta_tnr > 0 else "噪音增加"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_tnr_V230629(c: CZSC, **kwargs) -> OrderedDict:
    """趋势噪音指标（TNR，Trend to Noise Rate）分层

    参数模板："{freq}_D{di}TNR{timeperiod}_趋势V230629"

    **信号逻辑：**

    TNR计算公式：取N根K线，首尾两个close的绝对差值 除以 相邻两个close的绝对差值累计。

    取最近100个bar的TNR进行分层。

    **信号列表：**

    - Signal('15分钟_D1TNR14_趋势V230629_第7层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第6层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第8层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第9层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第10层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第5层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第2层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第1层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第3层_任意_任意_0')
    - Signal('15分钟_D1TNR14_趋势V230629_第4层_任意_任意_0')

    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: TNR指标的参数

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    freq = c.freq.value

    # 更新缓存
    cache_key = f"TNR{timeperiod}"
    for i, bar in enumerate(c.bars_raw, 0):
        if cache_key in bar.cache:
            continue
        if i < timeperiod:
            bar.cache[cache_key] = 0
        else:
            _bars = c.bars_raw[max(0, i - timeperiod):i + 1]
            sum_abs = sum([abs(_bars[j].close - _bars[j - 1].close) for j in range(1, len(_bars))])
            bar.cache[cache_key] = 0 if sum_abs == 0 else abs(_bars[-1].close - _bars[0].close) / sum_abs

    k1, k2, k3 = f"{freq}_D{di}TNR{timeperiod}_趋势V230629".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    tnr = [bar.cache[cache_key] for bar in bars]
    lev = pd.qcut(tnr, 10, labels=False, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=f"第{int(lev+1)}层")


def bar_shuang_fei_V230507(c: CZSC, **kwargs) -> OrderedDict:
    """双飞涨停，贡献者：琅盎

    参数模板："{freq}_D{di}双飞_短线V230507"

    **信号逻辑：**

    1. 今天涨停;
    2. 昨天收阴，且跌幅大于5%
    3. 前天涨停

    **信号列表：**

    - Signal('日线_D1双飞_短线V230507_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - di: 信号计算截止倒数第i根K线

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}双飞_短线V230507".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b4, b3, b2, b1 = get_sub_elements(c.bars_raw, di=di, n=4)
    first_zt = b3.close == b3.high and b3.close / b4.close - 1 > 0.07
    last_zt = b1.close / b2.close - 1 > 0.07 and b1.upper < max(b1.lower, b1.solid) / 2
    bar2_down = b2.close < b2.open and b2.close / b3.close - 1 < -0.05

    if first_zt and last_zt and b1.close > b2.high and bar2_down:
        v1 = "看多"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_limit_down_V230525(c: CZSC, **kwargs) -> OrderedDict:
    """跌停后出现无下影线长实体阳线做多

    参数模板："{freq}_跌停后无下影线长实体阳线_短线V230525"

     **信号逻辑：**

    1. 跌停后出现无下影线长实体阳线做多

     **信号列表：**

    - Signal('日线_跌停后无下影线长实体阳线_短线V230525_满足_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    freq = c.freq.value
    assert freq == '日线', "该信号只能用于日线级别，仅适用于A股"

    k1, k2, k3 = f"{freq}_跌停后无下影线长实体阳线_短线V230525".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3 = c.bars_raw[-3:]
    b2_condition = b2.low == b2.close < b1.close and b2.close / b1.close < 0.95
    b3_condition = b3.low == b3.open and b3.close > b3.open and b3.solid > b3.upper * 2 and b3.close / b3.open > 1.07
    if b2_condition and b3_condition and b3.low < b2.low:
        v1 = '满足'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_eight_V230702(c: CZSC, **kwargs) -> OrderedDict:
    """8K走势分类

    参数模板："{freq}_D{di}#8K_走势分类V230702"

    **信号逻辑：**

    参见博客：https://blog.sina.com.cn/s/blog_486e105c010009uy.html
    这篇博客给出了8K走势分类的逻辑。

    **信号列表：**

    - Signal('30分钟_D1#8K_走势分类V230702_弱平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_双中枢下跌_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_转折平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_强平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_双中枢上涨_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_无中枢上涨_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_无中枢下跌_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}#8K_走势分类V230702".split("_")
    v1 = "其他"
    if len(c.bars_raw) < di + 12:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=8)
    zs_list = []
    for b1, b2, b3 in zip(bars[:-2], bars[1:-1], bars[2:]):
        if min(b1.high, b2.high, b3.high) >= max(b1.low, b2.low, b3.low):
            zs_list.append([b1, b2, b3])

    _dir = "上涨" if bars[-1].close > bars[0].open else "下跌"

    if not zs_list:
        v1 = f"无中枢{_dir}"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 双中枢的情况，有一根K线的 high low 与前后两个中枢没有重叠
    if len(zs_list) >= 2:
        zs1, zs2 = zs_list[0], zs_list[-1]
        zs1_high, zs1_low = max([x.high for x in zs1]), min([x.low for x in zs1])
        zs2_high, zs2_low = max([x.high for x in zs2]), min([x.low for x in zs2])
        if _dir == "上涨" and zs1_high < zs2_low:
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        if _dir == "下跌" and zs1_low > zs2_high:
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 单中枢的情况，前三根K线出现高点：弱平衡市，前三根K线出现低点：强平衡市，否则：转折平衡市
    high_first = max(bars[0].high, bars[1].high, bars[2].high) == max([x.high for x in bars])
    low_first = min(bars[0].low, bars[1].low, bars[2].low) == min([x.low for x in bars])
    if high_first and not low_first:
        v1 = "弱平衡市"
    elif low_first and not high_first:
        v1 = "强平衡市"
    else:
        v1 = "转折平衡市"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def bar_window_std_V230731(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内波动率的特征

    参数模板："{freq}_D{di}W{window}M{m}N{n}_窗口波动V230731"

    **信号逻辑：**

    滚动计算最近m根K线的波动率，分成n层，最大值为n，最小值为1；
    最近window根K线的最大值为max_layer，最小值为min_layer。
    以这两个值作为窗口内的波动率特征。

    **信号列表：**

    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N6_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N9_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N8_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N8_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N7_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N7_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N5_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N6_低波N5_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N5_低波N4_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N5_低波N3_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N4_低波N3_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param w: 观察的窗口大小。
        - :param m: 计算分位数所需取K线的数量。
        - :param n: 分层的数量。

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 5))
    m = int(kwargs.get("m", 100))
    n = int(kwargs.get("n", 10))

    # 更新STD20波动率缓存
    cache_key = "STD20"
    for i, bar in enumerate(c.bars_raw):
        if cache_key in bar.cache:
            continue
        bar.cache[cache_key] = 0 if i < 5 else np.std([x.close for x in c.bars_raw[max(i-20, 0):i]])

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}M{m}N{n}_窗口波动V230731".split('_')
    v1 = "其他"

    if len(c.bars_raw) < di + m + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    stds = [x.cache[cache_key] for x in get_sub_elements(c.bars_raw, di=di, n=m)]
    layer = pd.qcut(stds, n, labels=False, duplicates='drop')
    max_layer = max(layer[-w:]) + 1
    min_layer = min(layer[-w:]) + 1

    v1, v2 = f"高波N{max_layer}", f"低波N{min_layer}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)



def bar_window_ps_V230731(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内支撑压力位分位数计算，贡献者：chenlei

    参数模板："{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731"

    **信号逻辑：**

    1. 计算最近 N 笔的最高价 NH 和最低价 NL，这个可以近似理解成价格的支撑和压力位
    2. 计算并缓存最新K线的收盘价格 C 处于 NH、NL 之间的位置，计算方法为 P = （C - NL）/ (NH - NL)
    3. 取最近 M 个 P 值序列，按分位数分层，分层数量为 L，分层的最大值为最近的压力，最小值为最近的支撑，当前值为最近的价格位置

    **信号列表：**

    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N5_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N4_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N4_当前N4_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N3_当前N5_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N2_当前N2_0')
    - Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N1_当前N2_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param w: 评价分位数分布用的窗口大小
        - :param m: 计算分位数所需取K线的数量。
        - :param n: 最近N笔
        - :param l: 分层的数量。

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 5))
    m = int(kwargs.get("m", 40))
    n = int(kwargs.get("n", 8))
    l = int(kwargs.get("l", 5))

    assert m > l * 2 > 2, "参数 m 必须大于 l * 2，且 l 必须大于 2"
    assert w < m, "参数 w 必须小于 m"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731".split('_')
    if len(c.bi_list) < n + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    # 更新支撑压力位位置
    cache_key_pct = "pct"
    H_line, L_line = max([x.high for x in c.bi_list[-n:]]), min([x.low for x in c.bi_list[-n:]])
    for i, bar in enumerate(c.bars_raw):
        if cache_key_pct in bar.cache:
            continue
        bar.cache[cache_key_pct] = (bar.close - L_line) / (H_line - L_line)

    fenweis = [x.cache[cache_key_pct] for x in get_sub_elements(c.bars_raw, n=m)]
    layer = pd.qcut(fenweis, l, labels=False, duplicates='drop')
    max_layer = max(layer[-w:]) + 1
    min_layer = min(layer[-w:]) + 1

    v1, v2, v3 = f"压力N{max_layer}", f"支撑N{min_layer}", f"当前N{layer[-1]+1}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def bar_window_ps_V230801(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内支撑压力位分位数计算

    参数模板："{freq}_N{n}W{w}_支撑压力位V230801"

    **信号逻辑：**

    1. 计算最近 N 笔的最高价 NH 和最低价 NL，这个可以近似理解成价格的支撑和压力位
    2. 计算并缓存最新K线的收盘价格 C 处于 NH、NL 之间的位置，计算方法为 P = （C - NL）/ (NH - NL)
    3. 取最近 M 个 P 值序列，四舍五入精确到小数点后1位，作为当前K线的分位数

    **信号列表：**

    - Signal('60分钟_N8W5_支撑压力位V230801_最大N7_最小N4_当前N5_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N8_最小N4_当前N4_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N6_最小N2_当前N6_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N6_最小N2_当前N5_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N6_最小N2_当前N3_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N4_最小N0_当前N3_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N4_最小N0_当前N2_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N4_最小N0_当前N1_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N7_最小N3_当前N6_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N9_最小N4_当前N9_0')
    - Signal('60分钟_N8W5_支撑压力位V230801_最大N4_最小N0_当前N4_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param w: 评价分位数分布用的窗口大小
        - :param n: 最近N笔

    :return: 信号识别结果
    """
    w = int(kwargs.get("w", 5))
    n = int(kwargs.get("n", 8))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}W{w}_支撑压力位V230801".split('_')
    ubi = c.ubi
    if len(c.bi_list) < n + 2 or not ubi:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    H_line = max([x.high for x in c.bi_list[-n:]] + [ubi['high']])
    L_line = min([x.low for x in c.bi_list[-n:]] + [ubi['low']])

    pcts = [int(max((x.close - L_line) / (H_line - L_line), 0) * 10) for x in c.bars_raw[-w:]]
    v1, v2, v3 = f"最大N{max(pcts)}", f"最小N{min(pcts)}", f"当前N{pcts[-1]}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def bar_trend_V240209(c: CZSC, **kwargs) -> OrderedDict:
    """趋势跟踪信号

    参数模板："{freq}_D{di}N{N}趋势跟踪_BS辅助V240209"

    **信号逻辑：**

    以多头为例：
    1. 低点出现在高点之后，且低点右侧的高点到当前K线之间的K线数量在5-30之间；
    2. 低点右侧的K线的DIF值小于前N根K线的DIF值的标准差的一半；
    3. 低点右侧的K线的最低价大于低点的最低价；
    4. 低点右侧的K线的MACD值小于前N根K线的MACD值的标准差的一半。

    **信号列表：**

    - Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_多头_任意_任意_0')
    - Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数设置

        - di: int, default 1, 倒数第几根K线
        - N: int, default 20, 窗口大小

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    N = int(kwargs.get('N', 60))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{N}趋势跟踪_BS辅助V240209".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    bars = get_sub_elements(c.bars_raw, di=di, n=N)
    max_bar = max(bars, key=lambda x: x.high)
    min_bar = min(bars, key=lambda x: x.low)
    dif_std = np.std([x.cache[cache_key]['dif'] for x in bars])
    macd_std = np.std([x.cache[cache_key]['macd'] for x in bars])

    if min_bar.dt < max_bar.dt:
        right_bars = [x for x in c.bars_raw if x.dt >= max_bar.dt]
        right_min_bar = min(right_bars, key=lambda x: x.low)
        c1 = 30 > right_min_bar.id - max_bar.id > 5
        c2 = abs(right_bars[-1].cache[cache_key]['dif']) < dif_std        # type: ignore
        c3 = right_min_bar.low > min_bar.low
        c4 = abs(right_bars[-1].cache[cache_key]['macd']) < macd_std     # type: ignore

        if c1 and c2 and c3 and c4:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="多头")

    if min_bar.dt > max_bar.dt:
        right_bars = [x for x in c.bars_raw if x.dt >= min_bar.dt]
        right_max_bar = max(right_bars, key=lambda x: x.high)
        c1 = 30 > right_max_bar.id - min_bar.id > 5
        c2 = abs(right_bars[-1].cache[cache_key]['dif']) < dif_std        # type: ignore
        c3 = right_max_bar.high < max_bar.high
        c4 = abs(right_bars[-1].cache[cache_key]['macd']) < macd_std      # type: ignore

        if c1 and c2 and c3 and c4:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="空头")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
