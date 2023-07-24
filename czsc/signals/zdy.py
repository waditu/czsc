# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/13 22:45
describe: ZDY 信号函数集合
"""
import numpy as np
from loguru import logger
from collections import OrderedDict
from czsc.traders.base import CZSC, CzscTrader
from czsc.signals.tas import update_macd_cache
from czsc.utils import get_sub_elements, create_single_signal, sorted_freqs
from czsc.objects import Direction, Mark, Operate, ZS


def zdy_bi_end_V230406(c: CZSC, **kwargs) -> OrderedDict:
    """分型停顿判断K线结束

    参数模板："{freq}_D0停顿分型_BE辅助V230406"

    **信号逻辑：**

    1. 当分型形成后，等待后续出现某一根 K 线的收盘价站住第三根 K 线（此处的第三根 K 线是指形成分型的第三根 K 线）
    的极值，即可认为满足了停顿法的要求。
    2. 如果是两次停顿确认笔结束，要求内部至少还有一个相应的分型停顿。

    **信号列表：**

    - Signal('15分钟_D0停顿分型_BE辅助V230406_看空_任意_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看多_任意_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看多_内部底停顿_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看空_内部顶停顿_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看空_任意_顶分区间_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看多_任意_底分区间_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看空_内部顶停顿_顶分区间_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230406_看多_内部底停顿_底分区间_0')

    **相关信号：**

    - :func:`czsc.signals.byi_bi_end_V230106`

    :param c: CZSC对象
    :return:
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D0停顿分型_BE辅助V230406".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3 or len(c.bars_ubi) > 6 or len(c.bars_ubi) < 4:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    last_high = max([x.high for x in last_bi.fx_b.elements[-1].raw_bars])
    last_low = min([x.low for x in last_bi.fx_b.elements[-1].raw_bars])
    last_bar = c.bars_raw[-1]

    if last_bi.fx_b.elements[-1].dt >= last_bar.dt or last_bi.length < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bars = [y for x in c.bars_ubi[3:] for y in x.raw_bars]
    max_close = max([x.close for x in last_bars])
    min_close = min([x.close for x in last_bars])

    if last_bi.direction == Direction.Down and max_close > last_high:
        v1 = '看多'
    elif last_bi.direction == Direction.Up and min_close < last_low:
        v1 = '看空'

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 笔内部再次查找停顿分型
    v2 = "任意"
    if v1 == '看多' and len(last_bi.fxs) >= 4:
        for fx1, fx2 in zip(last_bi.fxs[:-1], last_bi.fxs[1:]):
            if (
                fx1.mark == Mark.D
                and fx2.mark == Mark.G
                and max([x.close for x in fx2.raw_bars]) > fx1.elements[-1].high
            ):
                v2 = '内部底停顿'

    if v1 == "看空" and len(last_bi.fxs) >= 4:
        for fx1, fx2 in zip(last_bi.fxs[:-1], last_bi.fxs[1:]):
            if (
                fx1.mark == Mark.G
                and fx2.mark == Mark.D
                and min([x.close for x in fx2.raw_bars]) < fx1.elements[-1].low
            ):
                v2 = '内部顶停顿'

    # 价格回到笔结束分型内部
    v3 = "任意"
    if v1 == '看多':
        assert last_bi.fx_b.mark == Mark.D
        if last_bar.close < last_bi.fx_b.high:
            v3 = '底分区间'
    if v1 == '看空':
        assert last_bi.fx_b.mark == Mark.G
        if last_bar.close > last_bi.fx_b.low:
            v3 = '顶分区间'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def zdy_bi_end_V230407(c: CZSC, **kwargs) -> OrderedDict:
    """分型停顿判断K线结束

    参数模板："{freq}_D0停顿分型_BE辅助V230407"

    **信号逻辑：**

    1. 当分型形成后，等待后续出现某一根 K 线的收盘价站住第三根 K 线（此处的第三根 K 线是指形成分型的第三根 K 线）
       的极值，且后续的所有K线收盘价都满足，即可认为满足了停顿法的要求。
    2. 如果是两次停顿确认笔结束，要求内部至少还有一个相应的分型停顿。

    **信号列表：**

    - Signal('15分钟_D0停顿分型_BE辅助V230407_看空_任意_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230407_看多_任意_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230407_看多_内部底停顿_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230407_看空_内部顶停顿_任意_0')

    :param c: CZSC对象
    :return:
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D0停顿分型_BE辅助V230407".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3 or len(c.bars_ubi) > 6 or len(c.bars_ubi) < 4:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    last_high = max([x.high for x in last_bi.fx_b.elements[-1].raw_bars])
    last_low = min([x.low for x in last_bi.fx_b.elements[-1].raw_bars])
    last_bar = c.bars_raw[-1]

    if last_bi.fx_b.elements[-1].dt >= last_bar.dt or last_bi.length < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bars = [y for x in c.bars_ubi for y in x.raw_bars]
    last_bars = [x for x in last_bars if x.dt >= last_bi.fx_b.elements[-1].dt]

    if last_bi.direction == Direction.Down and last_bars[-1].close > last_high:
        _temp = [i for i, x in enumerate(last_bars) if x.close > last_high]
        if len(_temp) == 1 or (len(_temp) > 1 and _temp[-1] - _temp[0] == len(_temp) - 1):
            v1 = '看多'

    elif last_bi.direction == Direction.Up and last_bars[-1].close < last_low:
        _temp = [i for i, x in enumerate(last_bars) if x.close < last_low]
        if len(_temp) == 1 or (len(_temp) > 1 and _temp[-1] - _temp[0] == len(_temp) - 1):
            v1 = '看空'

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 笔内部再次查找停顿分型
    v2 = "任意"
    if v1 == '看多' and len(last_bi.fxs) >= 4:
        for fx1, fx2 in zip(last_bi.fxs[:-1], last_bi.fxs[1:]):
            if (
                fx1.mark == Mark.D
                and fx2.mark == Mark.G
                and max([x.close for x in fx2.raw_bars]) > fx1.elements[-1].high
            ):
                v2 = '内部底停顿'

    if v1 == "看空" and len(last_bi.fxs) >= 4:
        for fx1, fx2 in zip(last_bi.fxs[:-1], last_bi.fxs[1:]):
            if (
                fx1.mark == Mark.G
                and fx2.mark == Mark.D
                and min([x.close for x in fx2.raw_bars]) < fx1.elements[-1].low
            ):
                v2 = '内部顶停顿'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_vibrate_V230406(cat: CzscTrader, freq1, freq2, **kwargs) -> OrderedDict:
    """中枢震荡短差操作

    参数模板："中枢震荡_{freq1}#{freq2}_BS辅助V230406"

    **信号逻辑：**

    1、中枢笔数必须大于等于3笔。（排除掉盘背构成的中枢）
    2、中枢上沿做空，中枢下沿做多（不区分中枢方向）

    以开空仓为例（中枢上沿），当向上一笔出现次级别分型停顿后，定义次级别收盘价为 P，次级别顶分型高点为 H ，则需满足：

    1. H>=本级别中枢上沿价格
    2.（H-本级别中枢上沿价格）< 本级别中枢高度
    3.（H-P）*3  < 中枢高度
    4. 本级别MACD黄白线死叉确立（已经走出并列向下走势）

    稍微解释一下几个条件的内在逻辑：

    1. H>=本级别中枢上沿价格 ： 确保是在中枢的上沿
    2.（H-本级别中枢上沿价格）< 本级别中枢高度 ： 确保中枢上沿不要太远的距离，太远了可能下跌就形成三买上去了。这种点不要。
    3. （H-P）*3  < 中枢高度 ： H-P，其实就是一个次级别分型停顿的高度了，这里就是为了排除掉奔走型中枢，区间特别小的中枢，没必要做。

    **信号列表：**

    - Signal('中枢震荡_5分钟#60分钟_BS辅助V230406_看多_任意_任意_0')
    - Signal('中枢震荡_5分钟#60分钟_BS辅助V230406_看空_任意_任意_0')

    :param cat: 交易员对象
    :param freq1: 次级别
    :param freq2: 本级别
    :param kwargs:
    :return:
    """
    k1, k2, k3 = f"中枢震荡_{freq1}#{freq2}_BS辅助V230406".split("_")
    v1 = '其他'
    assert sorted_freqs.index(freq1) < sorted_freqs.index(freq2), "freq1 必须小于 freq2"
    c1: CZSC = cat.kas[freq1]
    c2: CZSC = cat.kas[freq2]
    cache_key = update_macd_cache(c2, fastperiod=12, slowperiod=26, signalperiod=9)

    if len(c2.bi_list) < 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3, b4 = c2.bi_list[-4:]
    zg = min(b1.high, b2.high, b3.high)
    zd = max(b1.low, b2.low, b3.low)

    if zd > zg:  # 本级别中枢不成立，不做
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 判断次级别分型是否停顿
    c1_lbi = c1.bi_list[-1]
    c1_bar = c1.bars_raw[-1]

    if c1_bar.dt == c1_lbi.fx_b.raw_bars[-1].dt or len(c1.bars_ubi) > 6:
        # 次级别不具备分型停顿的条件，不做
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if (
        c1_lbi.direction == Direction.Down
        and c1_bar.close > c1_bar.open
        and c1_bar.close > c1_lbi.fx_b.raw_bars[-1].high
    ):
        temp = '底分停顿'

    elif (
        c1_lbi.direction == Direction.Up and c1_bar.close < c1_bar.open and c1_bar.close < c1_lbi.fx_b.raw_bars[-1].low
    ):
        temp = '顶分停顿'

    else:
        # 次级别分型没有停顿，不做
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 判断中枢震荡买卖点
    c2_bar = c2.bars_raw[-1]
    if temp == '顶分停顿' and c2_bar.cache[cache_key]['macd'] < 0:
        P = c1_bar.close
        H = c1_lbi.high
        if H >= zg and (H - zg) < (zg - zd) and (H - P) * 3 < (zg - zd):
            v1 = '看空'

    if temp == '底分停顿' and c2_bar.cache[cache_key]['macd'] > 0:
        P = c1_bar.close
        L = c1_lbi.low
        if L <= zd and (zd - L) < (zg - zd) and (P - L) * 3 < (zg - zd):
            v1 = '看多'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_stop_loss_V230406(cat: CzscTrader, **kwargs) -> OrderedDict:
    """笔操作止损逻辑

    参数模板："{freq1}_{pos_name}F{first_stop}_止损V230406"

    **信号逻辑：**

    多头止损逻辑如下，反之为空头止损逻辑：

    1. 进场后设定止损为固定BP止损。
    2. 跌破开仓前最后一个分型的低点，止损。
    3. 任何一笔在持仓状态下的上升笔结束后，若没有判断止盈走人，则将止损设定在该笔起始点的位置（或适当放低一些固定BP）

    **信号列表：**

    - Signal('日线_5日线多头F300_止损V230406_多头止损_任意_任意_0')
    - Signal('日线_5日线多头F300_止损V230406_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]  # 笔的观察周期
    first_stop = int(kwargs.get("first_stop", 300))  # 进场点止损设置
    k1, k2, k3 = f"{freq1}_{pos_name}F{first_stop}_止损V230406".split("_")
    v1, v2 = '其他', '其他'
    if hasattr(cat, 'positions') is False:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]['op'] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    d3bi = c.bi_list[-3]
    bis = [x for x in c.bi_list if x.fx_b.dt >= op['dt']]
    last_bar = c.bars_raw[-1]

    # 多头止损逻辑
    if op['op'] == Operate.LO:
        open_base_fx = [x for x in c.fx_list if x.mark == Mark.D and x.dt < op['dt']][-1]
        assert open_base_fx.mark == Mark.D, "开仓前最后一个分型必须是底分型"
        if last_bar.close < open_base_fx.low:
            v1 = '多头止损'
            v2 = '跌破分型低点'

        if (last_bar.close / op['price'] - 1) * 10000 <= -first_stop:
            v1 = '多头止损'
            v2 = '进场点止损'

        if (
            len(bis) > 0
            and bis[-1].direction == Direction.Up
            and bis[-1].high > d3bi.high
            and last_bar.close < op['price']
        ):
            assert bis[-1].direction == Direction.Up
            v1 = '多头止损'
            v2 = '跌破成本价'

        if len(bis) > 1 and bis[-1].direction == Direction.Up and last_bar.close < bis[-2].fx_b.low:
            v1 = '多头止损'
            v2 = '跌破上个向下笔底'

    # 空头止损逻辑
    if op['op'] == Operate.SO:
        open_base_fx = [x for x in c.fx_list if x.mark == Mark.G and x.dt < op['dt']][-1]
        assert open_base_fx.mark == Mark.G, "开仓前最后一个分型必须是底分型"
        if last_bar.close > open_base_fx.high:
            v1 = '空头止损'
            v2 = '升破分型高点'

        if (1 - last_bar.close / op['price']) * 10000 <= -first_stop:
            v1 = '空头止损'
            v2 = '进场点止损'

        if (
            len(bis) > 0
            and bis[-1].direction == Direction.Down
            and bis[-1].low < d3bi.low
            and last_bar.close > op['price']
        ):
            assert d3bi.direction == Direction.Down
            v1 = '空头止损'
            v2 = '升破成本价'

        if len(bis) > 1 and bis[-1].direction == Direction.Down and last_bar.close > bis[-2].fx_b.high:
            v1 = '空头止损'
            v2 = '升破上个向上笔顶'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_take_profit_V230406(cat: CzscTrader, **kwargs) -> OrderedDict:
    """笔操作止盈逻辑

    参数模板："{freq1}_{pos_name}_止盈V230406"

    **信号逻辑：**

    多头止盈逻辑如下，反之为空头止盈逻辑：
    
    1. 任何一笔在持仓状态下的上升笔结束，若升破前一下跌笔高点，继续持仓，如没有升破前一下跌笔高点，止盈走人。需要用两次停顿分型判断。

    **信号列表：**

    - Signal('日线_5日线多头_止盈V230406_多头止盈_任意_任意_0')
    - Signal('日线_5日线多头_止盈V230406_空头止盈_任意_任意_0')

    :param cat: CzscTrader对象
    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]  # 笔的观察周期
    k1, k2, k3 = f"{freq1}_{pos_name}_止盈V230406".split("_")
    v1, v2 = '其他', '其他'
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]['op'] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos.operates[-1]
    c = cat.kas[freq1]
    bis = [x for x in c.bi_list if x.fx_b.dt >= op['dt']]

    # 多头止盈逻辑
    if op['op'] == Operate.LO:
        if len(bis) > 1 and bis[-1].direction == Direction.Up and bis[-1].high < bis[-2].high:
            v1 = '多头止盈'
            v2 = '向上笔不创新高'

    # 空头止盈逻辑
    if op['op'] == Operate.SO:
        if len(bis) > 1 and bis[-1].direction == Direction.Down and bis[-1].low > bis[-2].low:
            v1 = '空头止盈'
            v2 = '向下笔不创新低'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_take_profit_V230407(cat: CzscTrader, **kwargs) -> OrderedDict:
    """笔操作止盈逻辑

    参数模板："{freq1}_{pos_name}_止盈V230407"

    **信号逻辑：**

    多头止盈逻辑如下，反之为空头止盈逻辑：
    1. 根据K线个数判断力度，提前止盈。（三买之后的上升笔中，如果笔数已经大于前一下跌笔的K线个数的1.5倍，并且还没有新高，直接止盈走人。

    **信号列表：**

    - Signal('日线_5日线多头_止盈V230407_多头止盈_任意_任意_0')
    - Signal('日线_5日线多头_止盈V230407_空头止盈_任意_任意_0')

    :param cat: CzscTrader对象
    :return: 信号字典
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]  # 笔的观察周期
    k1, k2, k3 = f"{freq1}_{pos_name}_止盈V230407".split("_")
    v1, v2 = '其他', '其他'
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]['op'] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos.operates[-1]
    c = cat.kas[freq1]
    bis = [x for x in c.bi_list if x.fx_b.dt >= op['dt']]
    d2bi = c.bi_list[-2]

    if len(bis) <= 0 or bis[-1].length < 1.5 * d2bi.length:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 多头止盈逻辑
    if op['op'] == Operate.LO and bis[-1].direction == Direction.Up and bis[-1].high < d2bi.high:
        assert d2bi.direction == Direction.Down
        v1 = '多头止盈'
        v2 = '向上笔不创新高'

    # 空头止盈逻辑
    if op['op'] == Operate.SO and bis[-1].direction == Direction.Down and bis[-1].low > d2bi.low:
        assert d2bi.direction == Direction.Up
        v1 = '空头止盈'
        v2 = '向下笔不创新低'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_zs_V230423(c: CZSC, **kwargs):
    """约束中枢的形态和高度

    参数模板："{freq}_D{di}中枢形态_BS辅助V230423"

    **信号逻辑：**

    以上涨中枢为例，反之为下跌中枢：

    1. 进入笔和离开笔分别是高低点，笔的数量大于等于5
    2. 中枢高度 >= 进入中枢那一笔高度 / 3

    **信号列表：**

    - Signal('15分钟_D1中枢形态_BS辅助V230423_上涨_5笔_任意_0')
    - Signal('15分钟_D1中枢形态_BS辅助V230423_上涨_7笔_任意_0')
    - Signal('15分钟_D1中枢形态_BS辅助V230423_下跌_5笔_任意_0')
    - Signal('15分钟_D1中枢形态_BS辅助V230423_下跌_7笔_任意_0')
    - Signal('15分钟_D1中枢形态_BS辅助V230423_下跌_9笔_任意_0')
    - Signal('15分钟_D1中枢形态_BS辅助V230423_上涨_9笔_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数

        - di: 倒数第 di 根 K 线
        
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}中枢形态_BS辅助V230423".split('_')
    v1 = '其他'
    if len(c.bi_list) < 7 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    for n in (9, 7, 5):
        bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(bis) != n:
            continue

        bi1 = bis[0]
        # 假定离开中枢的都是一笔
        zs = ZS(bis[1:-1])
        if not (zs.is_valid and zs.zg - zs.zd > (bi1.high - bi1.low) / 3):
            continue

        min_low = min(x.low for x in bis)
        max_high = max(x.high for x in bis)
        if bi1.direction == Direction.Up and bi1.low == min_low and bis[-1].high == max_high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="上涨", v2=f"{n}笔")

        if bi1.direction == Direction.Down and bi1.high == max_high and bis[-1].low == min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="下跌", v2=f"{n}笔")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_macd_bc_V230422(c: CZSC, **kwargs):
    """MACD面积背驰

    参数模板："{freq}_D{di}T{th}MACD面积背驰_BS辅助V230422"

    **信号逻辑：**

    以上涨背驰为例，反之为下跌背驰：

    1. 背驰段的相应macd面积之和 <= 进入中枢段的相应面积之和 * th / 100
    2. 中枢把黄白线拉到0轴附近，
    3. 离开中枢的一笔，黄白线大于0且不新高

    **信号列表：**

    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_上涨_9笔_任意_0')
    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_上涨_7笔_任意_0')
    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_下跌_5笔_任意_0')
    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_上涨_5笔_任意_0')
    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_下跌_7笔_任意_0')
    - Signal('15分钟_D1T50MACD面积背驰_BS辅助V230422_下跌_9笔_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数

        - di: 倒数第 di 根 K 线
        - th: 背驰段的相应macd面积之和 <= 进入中枢段的相应面积之和 * th / 100

    :return: 信号字典
    """
    cache_key = update_macd_cache(c, fastperiod=26, slowperiod=12, signalperiod=9)
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 50))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}T{th}MACD面积背驰_BS辅助V230422".split('_')
    v1 = '其他'
    if len(c.bi_list) < 7 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    for n in (9, 7, 5):
        bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(bis) != n:
            continue

        # 假定离开中枢的都是一笔
        zs = ZS(bis[1:-1])
        if not zs.is_valid:  # 如果中枢不成立，往下进行
            continue

        bi1, bi2 = bis[0], bis[-1]
        bi1_macd = [x.cache[cache_key]['macd'] for x in bi1.raw_bars[1:-1]]
        bi2_macd = [x.cache[cache_key]['macd'] for x in bi2.raw_bars[1:-1]]
        bi1_dif = bi1.raw_bars[-2].cache[cache_key]['dif']
        bi2_dif = bi2.raw_bars[-2].cache[cache_key]['dif']

        zs_fxb_raw = [y for x in zs.bis for y in x.fx_b.raw_bars]

        if bi1.direction == Direction.Up:
            bi1_area = sum([x for x in bi1_macd if x > 0])
            bi2_area = sum([x for x in bi2_macd if x > 0])
            dif_zero = min([x.cache[cache_key]['dif'] for x in zs_fxb_raw])
        else:
            bi1_area = sum([x for x in bi1_macd if x < 0])
            bi2_area = sum([x for x in bi2_macd if x < 0])
            dif_zero = max([x.cache[cache_key]['dif'] for x in zs_fxb_raw])

        if bi2_area > bi1_area * th / 100:  # 如果面积背驰不成立，往下进行
            continue

        min_low = min(x.low for x in bis)
        max_high = max(x.high for x in bis)
        if (
            bi1.direction == Direction.Up
            and bi1.low == min_low
            and bi2.high == max_high
            and dif_zero < 0
            and bi1_dif > bi2_dif > 0
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="上涨", v2=f"{n}笔")

        if (
            bi1.direction == Direction.Down
            and bi1.high == max_high
            and bi2.low == min_low
            and dif_zero > 0
            and bi1_dif < bi2_dif < 0
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="下跌", v2=f"{n}笔")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_macd_bs1_V230422(c: CZSC, **kwargs):
    """MACD辅助判断第一类买卖点

    参数模板："{freq}_D{di}T{th}MACD_BS1辅助V230422"

    **信号逻辑：**

    以上涨背驰为例，反之为下跌背驰：

    1. 背驰段的相应macd面积之和 <= 进入中枢段的相应面积之和 * th / 100
    2. 离开中枢的一笔，起点的黄白线在零轴附近，终点的黄白线在中枢黄白线的上方

    **信号列表：**

    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看空_上涨5笔_任意_0')
    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看多_下跌7笔_任意_0')
    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看多_下跌5笔_任意_0')
    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看空_上涨9笔_任意_0')
    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看空_上涨7笔_任意_0')
    - Signal('5分钟_D1T50MACD_BS1辅助V230422_看多_下跌9笔_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数

        - di: 倒数第 di 根 K 线
        - th: 背驰段的相应macd面积之和 <= 进入中枢段的相应面积之和 * th / 100

    :return: 信号字典
    """
    cache_key = update_macd_cache(c, fastperiod=26, slowperiod=12, signalperiod=9)
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 50))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}T{th}MACD_BS1辅助V230422".split('_')
    v1 = '其他'
    if len(c.bi_list) < 7 or len(c.bars_ubi) > 9:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    for n in (13, 11, 9, 7, 5):
        bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(bis) != n:
            continue

        # 假定离开中枢的都是一笔
        zs = ZS(bis[1:-1])
        if not zs.is_valid:  # 如果中枢不成立，往下进行
            continue

        bi1, bi2 = bis[0], bis[-1]
        bi1_area = sum([abs(x.cache[cache_key]['macd']) for x in bi1.raw_bars[1:-1]])
        bi2_area = sum([abs(x.cache[cache_key]['macd']) for x in bi2.raw_bars[1:-1]])
        bi1_dif = bi1.raw_bars[-2].cache[cache_key]['dif']
        bi2_dif = bi2.raw_bars[-2].cache[cache_key]['dif']
        bi2_start_dif = bi2.raw_bars[1].cache[cache_key]['dif']

        if bi1.direction == Direction.Up:
            # 计算 zs 中向上笔的 dif 最大值
            up_bis = [x for x in zs.bis if x.direction == Direction.Up]
            zs_dif = max([y.cache[cache_key]['dif'] for x in up_bis for y in x.fx_b.raw_bars])
        else:
            # 计算 zs 中向下笔的 dif 最小值
            down_bis = [x for x in zs.bis if x.direction == Direction.Down]
            zs_dif = min([y.cache[cache_key]['dif'] for x in down_bis for y in x.fx_b.raw_bars])

        if bi2_area > bi1_area * th / 100:  # 如果面积背驰不成立，往下进行
            continue

        min_low = min(x.low for x in bis)
        max_high = max(x.high for x in bis)
        if (
            bi1.direction == Direction.Up
            and bi1.low == min_low
            and bi2.high == max_high
            and bi2_start_dif < abs(zs_dif) * 0.5
            and bi1_dif > bi2_dif > zs_dif > 0
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="看空", v2=f"上涨{n}笔")

        if (
            bi1.direction == Direction.Down
            and bi1.high == max_high
            and bi2.low == min_low
            and bi2_start_dif > abs(zs_dif) * 0.5
            and 0 > zs_dif > bi2_dif > bi1_dif
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="看多", v2=f"下跌{n}笔")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_zs_space_V230421(c: CZSC, **kwargs):
    """中枢空间形态约束

    参数模板："{freq}_D{di}中枢空间_BS辅助V230421"

    **信号逻辑：**

    以顶背驰为例：要求【离开笔】距离中枢上沿的高度，大于等于【进入笔】距离中枢下沿的高度

    **信号列表：**

    - Signal('15分钟_D1中枢空间_BS辅助V230421_上涨_5笔_任意_0')
    - Signal('15分钟_D1中枢空间_BS辅助V230421_下跌_5笔_任意_0')
    - Signal('15分钟_D1中枢空间_BS辅助V230421_上涨_9笔_任意_0')
    - Signal('15分钟_D1中枢空间_BS辅助V230421_上涨_7笔_任意_0')
    - Signal('15分钟_D1中枢空间_BS辅助V230421_下跌_7笔_任意_0')
    - Signal('15分钟_D1中枢空间_BS辅助V230421_下跌_9笔_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}中枢空间_BS辅助V230421".split('_')
    v1 = '其他'
    if len(c.bi_list) < 7 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    for n in (9, 7, 5):
        bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(bis) != n:
            continue

        # 假定离开中枢的都是一笔
        zs = ZS(bis[1:-1])
        if not zs.is_valid:
            continue

        bi1, bi2 = bis[0], bis[-1]
        min_low = min(x.low for x in bis)
        max_high = max(x.high for x in bis)
        if (
            bi1.direction == Direction.Up
            and bi1.low == min_low
            and bi2.high == max_high
            and bi2.high - zs.zg >= zs.zd - bi1.low
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="上涨", v2=f"{n}笔")

        if (
            bi1.direction == Direction.Down
            and bi1.high == max_high
            and bi2.low == min_low
            and zs.zd - bi2.low >= bi1.high - zs.zg
        ):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="下跌", v2=f"{n}笔")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_macd_dif_V230516(c: CZSC, **kwargs) -> OrderedDict:
    """MACD柱子与DIF的关系

    参数模板："{freq}_D{di}DIF走平_BS辅助V230516"

    **信号逻辑：**

    * DIF走平看多：1） DIF小于MACD柱子；2）DIF相比前一周期下跌小于阈值
    * DIF走平看空：1） DIF大于MACD柱子；2）DIF相比前一周期上涨小于阈值

    **信号列表：**

    - Signal('60分钟_D1DIF走平_BS辅助V230516_看空_红柱远离_任意_0')
    - Signal('60分钟_D1DIF走平_BS辅助V230516_看空_柱子否定_任意_0')
    - Signal('60分钟_D1DIF走平_BS辅助V230516_看多_绿柱远离_任意_0')
    - Signal('60分钟_D1DIF走平_BS辅助V230516_看多_柱子否定_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}DIF走平_BS辅助V230516".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bars_raw) < 12 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=10)
    # macd = bars[-1].cache[cache_key]['macd'] * 2
    dif = [x.cache[cache_key]['dif'] for x in bars]

    dif_th = sum([abs(x - y) for x, y in zip(dif, dif[1:])]) / len(dif) * 0.2
    if dif[-1] - dif[-2] > -dif_th:
        v1 = '看多'
        min_macd = min([x.cache[cache_key]['macd'] for x in bars])
        v2 = "绿柱远离" if dif[-1] < min_macd * 2.5 else "柱子否定"

    if dif[-1] - dif[-2] < dif_th:
        v1 = '看空'
        max_macd = max([x.cache[cache_key]['macd'] for x in bars])
        v2 = "红柱远离" if dif[-1] > max_macd * 2.5 else "柱子否定"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_macd_dif_V230517(c: CZSC, **kwargs) -> OrderedDict:
    """MACD三次开仓条件

    参数模板："{freq}_D{di}MACD开仓_BS辅助V230517"

    **信号逻辑：**

    以多头开仓为例：

    1. DIF 在零轴下方运行很长时间后首次升破零轴
    2. DIF 在零轴上方首次出现与 DEA 的飞吻
    3. DIF 在零轴上方首次出现与 MACD 金叉

    **信号列表：**

    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看空_DIF破零轴_任意_0')
    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看空_MACD飞吻_任意_0')
    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看空_MACD死叉_任意_0')
    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看多_DIF破零轴_任意_0')
    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看多_MACD飞吻_任意_0')
    - Signal('60分钟_D1MACD开仓_BS辅助V230517_看多_MACD金叉_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}MACD开仓_BS辅助V230517".split('_')
    if len(c.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=20)
    macd = [x.cache[cache_key]['macd'] for x in bars]
    dif = [x.cache[cache_key]['dif'] for x in bars]

    if dif[-1] > 0:
        v1 = '看多'
        v2 = None
        if all([x < 0 for x in dif[:-1]]):
            v2 = 'DIF破零轴'

        if macd[-1] > 0 and macd[-2] < 0:
            v2 = 'MACD金叉'

        if macd[-5] > macd[-4] > macd[-3] > macd[-2] < macd[-1] and macd[-2] > 0:
            v2 = 'MACD飞吻'

        if v2:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    if dif[-1] < 0:
        v1 = '看空'
        v2 = None
        if all([x > 0 for x in dif[:-1]]):
            v2 = 'DIF破零轴'

        if macd[-1] < 0 and macd[-2] > 0:
            v2 = 'MACD死叉'

        if macd[-5] < macd[-4] < macd[-3] < macd[-2] > macd[-1] and macd[-2] < 0:
            v2 = 'MACD飞吻'

        if v2:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')


def zdy_macd_V230518(c: CZSC, **kwargs) -> OrderedDict:
    """MACD交叉次数

    参数模板："{freq}_D{di}MACD交叉N{n}_BS辅助V230518"

     **信号逻辑：**

    1. MACD 大于0，金叉；MACD 小于0，死叉
    2. 计算 MACD 连续大于0或者小于0的次数

     **信号列表：**

    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第1次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第2次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第3次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第4次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第5次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第6次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第7次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第8次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_第9次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第1次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第2次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第3次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第4次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第5次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第6次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第7次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第8次_任意_0')
    - Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第9次_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
     :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 9))
    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}MACD交叉N{n}_BS辅助V230518".split('_')
    if len(c.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=n + 1)
    macd = [x.cache[cache_key]['macd'] for x in bars]
    v1 = '金叉' if macd[-1] > 0 else '死叉'

    count = 0
    for m in macd[::-1]:
        if (m > 0 and macd[-1] > 0) or (m < 0 and macd[-1] < 0):
            count += 1
        else:
            break

    if count == n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2="超计数范围")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{count}次")


def zdy_macd_V230519(c: CZSC, **kwargs) -> OrderedDict:
    """MACD连续缩柱

    参数模板："{freq}_D{di}N{n}MACD缩柱_BS辅助V230519"

    **信号逻辑：**

    1. 取 N 跟 K 线，如果 N 跟 K 线的 MACD 都在零轴上方，且 N 跟 K 线的 MACD 都比 N-1 跟 K-1 线的 MACD 小，则认为是多头连续缩柱
    2. 反之为空头连续缩柱

    **信号列表：**

    - Signal('60分钟_D1N3MACD缩柱_BS辅助V230519_多头连续缩柱_任意_任意_0')
    - Signal('60分钟_D1N3MACD缩柱_BS辅助V230519_空头连续缩柱_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 3))
    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}N{n}MACD缩柱_BS辅助V230519".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    macd = [x.cache[cache_key]['macd'] for x in bars]

    if all([x > 0 for x in macd]) and all([macd[i] < macd[i - 1] for i in range(1, n)]):
        v1 = '多头连续缩柱'

    if all([x < 0 for x in macd]) and all([macd[i] > macd[i - 1] for i in range(1, n)]):
        v1 = '空头连续缩柱'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_macd_dif_iqr_V230521(c: CZSC, **kwargs) -> OrderedDict:
    """MACD柱子与DIF的关系

    参数模板："{freq}_D{di}DIF走平IQR_BS辅助V230521"

    **信号逻辑：**

    * DIF走平看多：1） DIF小于MACD柱子；2）最近3个周期DIF相比前一周期变化在四分位距内
    * DIF走平看空：1） DIF大于MACD柱子；2）最近3个周期DIF相比前一周期变化在四分位距内

    **信号列表：**

    - Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看空_红柱远离_任意_0')
    - Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看空_柱子否定_任意_0')
    - Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看多_绿柱远离_任意_0')
    - Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看多_柱子否定_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    k1, k2, k3 = f"{freq}_D{di}DIF走平IQR_BS辅助V230521".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bars_raw) < 50:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=100)
    macd = bars[-1].cache[cache_key]['macd'] * 2
    dif = [x.cache[cache_key]['dif'] for x in bars]

    # 计算四分位距
    Q3, Q1 = np.percentile(dif, [75, 25])
    IQR = Q3 - Q1

    if max(dif[-3:]) - min(dif[-3:]) < IQR and macd < 0:
        v1 = '看多'
        v2 = "绿柱远离" if dif[-1] < macd else "柱子否定"

    if max(dif[-3:]) - min(dif[-3:]) < IQR and macd > 0:
        v1 = '看空'
        v2 = "红柱远离" if dif[-1] > macd else "柱子否定"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def zdy_macd_V230527(c: CZSC, **kwargs) -> OrderedDict:
    """DIF/DEA/MACD 远离零轴辅助判断买卖点

    参数模板："{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230527"

    **信号逻辑：**

    1. 获取最近 w 根K线，计算 DIF/DEA/MACD，计算绝对值的中位数和标准差
    2. 如果最新的 n 个值的最大绝对值大于中位数 + t / 10 * 标准差，则认为远离零轴

    **信号列表：**

    - Signal('60分钟_DIF远离W100N10T10_BS辅助V230527_多头远离_任意_任意_0')
    - Signal('60分钟_DIF远离W100N10T10_BS辅助V230527_空头远离_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 10))
    w = int(kwargs.get("w", 100))
    t = int(kwargs.get("t", 20))  # 远离零轴的阈值，越大越远离零轴，比较的基准是窗口内的中位数和标准差；20表示2倍
    key = kwargs.get("key", "dif").upper()
    assert key in ["DIF", "DEA", "MACD"]
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230527".split("_")
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=w)
    factors = [x.cache[cache_key][key.lower()] for x in bars]
    median = np.median(np.abs(factors))
    std = np.std(np.abs(factors))

    last_n_factors = factors[-n:]
    max_abs_factor = max(last_n_factors, key=abs)
    if abs(max_abs_factor) > median + t / 10 * std:
        v1 = f"{'多头' if max_abs_factor > 0 else '空头'}远离"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_dif_V230527(c: CZSC, **kwargs) -> OrderedDict:
    """DIF远离零轴辅助判断买卖点

    参数模板："{freq}_N{n}T{t}_DIF远离V230527"

    **信号逻辑：**

    以多头远离为例：回溯N根K线，找到DIF最大值，然后绿柱回溯10跟找到MACD最大值，然后看最大值之间的距离判断原理。

    **信号列表：**

    - Signal('5分钟_N10T30_DIF远离V230527_空头远离_任意_任意_0')
    - Signal('5分钟_N10T30_DIF远离V230527_多头远离_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 10))
    t = int(kwargs.get("t", 30))  # 远离零轴的阈值，越大越远离零轴；30表示3倍
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}T{t}_DIF远离V230527".split("_")
    v1 = '其他'
    if len(c.bars_raw) < 30 + n * 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=1, n=n * 8)
    max_abs_dif_bar = max(bars[-n:], key=lambda x: abs(x.cache[cache_key]['dif']))
    max_abs_dif = max_abs_dif_bar.cache[cache_key]['dif']

    if max_abs_dif > 0:
        macd_seq = [x.cache[cache_key]['macd'] for x in bars if x.cache[cache_key]['macd'] > 0]
        if len(macd_seq) > n and abs(max_abs_dif) > max(macd_seq) * t / 10:
            v1 = '多头远离'
    elif max_abs_dif < 0:
        macd_seq = [abs(x.cache[cache_key]['macd']) for x in bars if x.cache[cache_key]['macd'] < 0]
        if len(macd_seq) > n and abs(max_abs_dif) > max(macd_seq) * t / 10:
            v1 = '空头远离'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def zdy_dif_V230528(c: CZSC, **kwargs) -> OrderedDict:
    """DIF远离零轴辅助判断买卖点

    参数模板："{freq}_N{n}T{t}_DIF远离V230528"

    **信号逻辑：**

    以多头远离为例：回溯1000根K线，找到DIF的所有峰谷值，如最近一个是峰值，且大于所有峰值的 T% 分位数。

    **信号列表：**

    - Signal('5分钟_N20T70_DIF远离V230528_空头远离_任意_任意_0')
    - Signal('5分钟_N20T70_DIF远离V230528_多头远离_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    cache_key = update_macd_cache(c, fastperiod=12, slowperiod=26, signalperiod=9)
    n = int(kwargs.get("n", 20))  # 峰谷值的数量最小值
    t = int(kwargs.get("t", 80))  # 峰谷排序的分位数
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}T{t}_DIF远离V230528".split("_")
    v1 = '其他'

    def _find_peaks_valleys(data):
        """在给定的一维数据中找到所有的峰值和谷值。

        :param data: 输入的一维数据，应为一个列表或者类似列表的数据结构
        :return: 峰值和谷值的索引和对应的值
        """
        peaks = {}
        valleys = {}

        # 检查数据是否至少有5个元素
        if len(data) < 5:
            return {"peaks": peaks, "valleys": valleys}

        # 遍历数据，找到所有的峰值和谷值
        for i in range(2, len(data) - 2):
            # 如果当前元素比它的左右两侧的元素都大，则它是一个峰值
            if data[i - 2] < data[i - 1] < data[i] > data[i + 1] > data[i + 2]:
                peaks[i] = data[i]

            # 如果当前元素比它的左右两侧的元素都小，则它是一个谷值
            if data[i - 2] > data[i - 1] > data[i] < data[i + 1] < data[i + 2]:
                valleys[i] = data[i]

        return peaks, valleys

    dif_values = [x.cache[cache_key]['dif'] for x in c.bars_raw[-1000:]]
    peaks, valleys = _find_peaks_valleys(dif_values)

    if len(peaks) < n or len(valleys) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    peaks_n = np.percentile(list(peaks.values()), t)
    valleys_n = np.percentile(list(valleys.values()), 100 - t)

    if max(peaks.keys()) > max(valleys.keys()) and peaks[max(peaks.keys())] > peaks_n and dif_values[-1] > 0:
        v1 = '多头远离'

    if max(valleys.keys()) > max(peaks.keys()) and valleys[max(valleys.keys())] < valleys_n and dif_values[-1] < 0:
        v1 = '空头远离'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
