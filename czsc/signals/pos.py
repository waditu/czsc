# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/14 19:27
describe:
"""
from czsc.analyze import CZSC
from collections import OrderedDict
from czsc.traders.base import CzscTrader
from czsc.utils import create_single_signal, get_sub_elements
from czsc.objects import Operate, Direction, Mark
from czsc.signals.tas import update_ma_cache


def pos_ma_V230414(cat: CzscTrader, **kwargs) -> OrderedDict:
    """判断开仓后是否升破MA均线或跌破MA均线

    参数模板："{pos_name}_{freq1}#{ma_type}#{timeperiod}_持有状态V230414"

    **信号逻辑：**

    多头持有状态如下，反之为空头持有状态：

    1. 如果持有多头，且开仓后有价格升破MA均线，则为多头升破均线；
    2. 如果持有空头，且开仓后有价格跌破MA均线，则为空头跌破均线。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟#SMA#5_持有状态V230414_多头_升破均线_任意_0')
    - Signal('日线三买多头N1_60分钟#SMA#5_持有状态V230414_空头_跌破均线_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，向前找的分型个数，默认为 3
    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    ma_type = kwargs.get("ma_type", "SMA").upper()
    timeperiod = int(kwargs.get("timeperiod", 5))
    k1, k2, k3 = f"{pos_name}_{freq1}#{ma_type}#{timeperiod}_持有状态V230414".split("_")
    v1, v2 = "其他", "其他"
    key = update_ma_cache(cat.kas[freq1], ma_type=ma_type, timeperiod=timeperiod)
    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    if op["op"] == Operate.LO:
        bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
        for x in bars:
            if x.close > x.cache[key]:
                v1, v2 = "多头", "升破均线"
                break

    if op["op"] == Operate.SO:
        bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
        for x in bars:
            if x.close < x.cache[key]:
                v1, v2 = "空头", "跌破均线"
                break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def pos_fx_stop_V230414(cat: CzscTrader, **kwargs) -> OrderedDict:
    """按照开仓点附近的分型止损

    参数模板："{freq1}_{pos_name}N{n}_止损V230414"

    **信号逻辑：**

    多头止损逻辑如下，反之为空头止损逻辑：

    1. 从多头开仓点开始，在给定对的K线周期 freq1 上向前找 N 个底分型，记为 F1
    2. 将这 N 个底分型的最低点，记为 L1，如果最新价低于 L1，则止损

    **信号列表：**

    - Signal('日线_日线三买多头N1_止损V230414_多头止损_任意_任意_0')
    - Signal('日线_日线三买多头N1_止损V230414_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，向前找的分型个数，默认为 3
    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 3))
    k1, k2, k3 = f"{freq1}_{pos_name}N{n}_止损V230414".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    # 多头止损逻辑
    if op["op"] == Operate.LO:
        fxs = [x for x in c.fx_list if x.mark == Mark.D and x.dt < op["dt"]][-n:]
        if cat.latest_price < min([x.low for x in fxs]):
            v1 = "多头止损"

    # 空头止损逻辑
    if op["op"] == Operate.SO:
        fxs = [x for x in c.fx_list if x.mark == Mark.G and x.dt < op["dt"]][-n:]
        if cat.latest_price > max([x.high for x in fxs]):
            v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_bar_stop_V230524(cat: CzscTrader, **kwargs) -> OrderedDict:
    """按照开仓点附近的N根K线极值止损

    参数模板："{pos_name}_{freq1}N{n}K_止损V230524"

    **信号逻辑：**

    多头止损逻辑如下，反之为空头止损逻辑：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上向前找 N 个K线，记为 F1
    2. 将这 N 个K线的最低点，记为 L1，如果最新价跌破 L1，则止损

    **信号列表：**

    - Signal('日线三买多头_日线N3K_止损V230524_多头止损_任意_任意_0')
    - Signal('日线三买多头_日线N3K_止损V230524_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，向前找的K线个数，默认为 3

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 3))
    k1, k2, k3 = f"{pos_name}_{freq1}N{n}K_止损V230524".split("_")
    v1 = "其他"
    assert 20 >= n >= 1, "参数 n 取值范围为 1~20"
    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos_ = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos_.operates) == 0 or pos_.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c: CZSC = cat.kas[freq1]
    op = pos_.operates[-1]

    # 多头止损逻辑
    if op["op"] == Operate.LO:
        bars = [x for x in c.bars_raw[-100:] if x.dt < op["dt"]][-n:]
        if cat.latest_price < min([x.low for x in bars]):
            v1 = "多头止损"

    # 空头止损逻辑
    if op["op"] == Operate.SO:
        bars = [x for x in c.bars_raw[-100:] if x.dt < op["dt"]][-n:]
        if cat.latest_price > max([x.high for x in bars]):
            v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_holds_V230414(cat: CzscTrader, **kwargs) -> OrderedDict:
    """开仓后N根K线涨幅小于M%%，则平仓

    参数模板："{pos_name}_{freq1}N{n}M{m}_趋势判断V230414"

    **信号逻辑：**

    1. 找出开仓后的 N 根K线，计算涨幅，如果涨幅小于 M%%，则平仓
    2. 这里面的逻辑是，如果开仓后的 N 根K线涨幅小于 M%%，则说明趋势不明朗，平仓等待

    **信号列表：**

    - Signal('日线三买多头N1_60分钟N5M100_趋势判断V230414_多头存疑_任意_任意_0')
    - Signal('日线三买多头N1_60分钟N5M100_趋势判断V230414_多头良好_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，最少持有K线数量，默认为 5，表示5根K线之后开始判断趋势
        - m: int，涨幅阈值，默认为 100，表示涨幅小于 100BP 时，平仓
    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 5))
    m = int(kwargs.get("m", 100))
    k1, k2, k3 = f"{pos_name}_{freq1}N{n}M{m}_趋势判断V230414".split("_")
    v1 = "其他"
    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
    if len(bars) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if op["op"] == Operate.LO:
        zdf = (bars[-1].close - op["price"]) / op["price"] * 10000
        v1 = "多头存疑" if zdf < m else "多头良好"

    if op["op"] == Operate.SO:
        zdf = (op["price"] - bars[-1].close) / op["price"] * 10000
        v1 = "空头存疑" if zdf < m else "空头良好"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_fix_exit_V230624(cat: CzscTrader, **kwargs) -> OrderedDict:
    """固定比例止损，止盈

    参数模板："{pos_name}_固定{th}BP止盈止损_出场V230624"

    **信号逻辑：**

    以多头为例，如果持有收益超过 th 个BP，则止盈；如果亏损超过 th 个BP，则止损。

    **信号列表：**

    - Signal('日线三买多头_固定100BP止盈止损_出场V230624_多头止损_任意_任意_0')
    - Signal('日线三买多头_固定100BP止盈止损_出场V230624_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，向前找的K线个数，默认为 3
    :return:
    """
    pos_name = kwargs["pos_name"]
    th = int(kwargs.get("th", 300))
    k1, k2, k3 = f"{pos_name}_固定{th}BP止盈止损_出场V230624".split("_")
    v1 = "其他"
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos_ = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos_.operates) == 0 or pos_.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos_.operates[-1]
    op_price = op["price"]

    if op["op"] == Operate.LO:
        if cat.latest_price < op_price * (1 - th / 10000):
            v1 = "多头止损"
        if cat.latest_price > op_price * (1 + th / 10000):
            v1 = "多头止盈"

    if op["op"] == Operate.SO:
        if cat.latest_price > op_price * (1 + th / 10000):
            v1 = "空头止损"
        if cat.latest_price < op_price * (1 - th / 10000):
            v1 = "空头止盈"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_profit_loss_V230624(cat: CzscTrader, **kwargs) -> OrderedDict:
    """开仓后盈亏比达到一定比值，才允许平仓  贡献者：谌意勇

    参数模板："{pos_name}_{freq1}YKB{ykb}N{n}_盈亏比判断V230624"

    **信号逻辑：**

    1. 通过公式 计算盈亏比=abs(现价-开仓价）/abs(开仓价-止损价）* 10,当比值大于一定阀值时才允许平仓

    **信号列表：**

    - Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_空头止损_任意_任意_0')
    - Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_多头止损_任意_任意_0')
    - Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_多头达标_任意_任意_0')
    - Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_空头达标_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - ykb: int，默认为 20, 表示2倍盈亏比，计算盈亏比=abs(现价-开仓价）/abs(开仓价-止损价）
        - n: int 默认为3  止损取最近n个分型的最低点或最高点

    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    ykb = int(kwargs.get("ykb", 20))
    n = int(kwargs.get("n", 3))
    k1, k2, k3 = f"{pos_name}_{freq1}YKB{ykb}N{n}_盈亏比判断V230624".split("_")
    v1 = "其他"
    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    last_close = c.bars_raw[-1].close

    if op["op"] == Operate.LO:
        fxs = [x for x in c.fx_list if x.mark == Mark.D and x.dt < op["dt"]][-n:]
        stop_price = min([x.low for x in fxs])
        ykb_ = ((last_close - op["price"]) / (op["price"] - stop_price)) * 10
        if ykb_ > ykb:
            v1 = "多头达标"
        else:
            if last_close < stop_price:
                v1 = "多头止损"

    if op["op"] == Operate.SO:
        fxs = [x for x in c.fx_list if x.mark == Mark.G and x.dt < op["dt"]][-n:]
        stop_price = max([x.high for x in fxs])
        ykb_ = ((last_close - op["price"]) / (op["price"] - stop_price)) * 10
        if ykb_ > ykb:
            v1 = "空头达标"
        else:
            if last_close > stop_price:
                v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_status_V230808(cat: CzscTrader, **kwargs) -> OrderedDict:
    """Position策略的持仓状态

    参数模板："{pos_name}_持仓状态_BS辅助V230808"

    **信号逻辑：**

    对指定的持仓策略，有三种状态：持多、持空、持币。

    **信号列表：**

    - Signal('日线三买多头N1_持仓状态_BS辅助V230808_持多_任意_任意_0')
    - Signal('日线三买多头N1_持仓状态_BS辅助V230808_持空_任意_任意_0')
    - Signal('日线三买多头N1_持仓状态_BS辅助V230808_持币_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
    :return:
    """
    pos_name = kwargs["pos_name"]
    k1, k2, k3 = f"{pos_name}_持仓状态_BS辅助V230808".split("_")
    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    pos = cat.get_position(pos_name)
    v1 = "持币"
    if len(pos.operates) == 0:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos.operates[-1]
    if op["op"] == Operate.LO:
        v1 = "持多"
    if op["op"] == Operate.SO:
        v1 = "持空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_holds_V230807(cat: CzscTrader, **kwargs) -> OrderedDict:
    """开仓后N根K线收益小于M%%，且当前收益大于T%%，平仓保本

    参数模板："{pos_name}_{freq1}N{n}M{m}T{t}_BS辅助V230807"

    **信号逻辑：**

    1. 针对某个开仓点，如果 N 根K线之后，收益低于 M，则认为开仓失误；
    2. 开仓的失误发生后，如果市场给了逃命的机会，不贪心，等待收益大于 T 时，平仓保本；
    3. 保本有两种场景：开仓后先亏损后反弹；开仓后先盈利后回落。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟N5M50T10_BS辅助V230807_多头保本_任意_任意_0')
    - Signal('日线三买多头N1_60分钟N5M50T10_BS辅助V230807_空头保本_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，最少持有K线数量，默认为 5，表示5根K线之后开始判断
        - m: int，收益最小阈值，默认为 100，表示收益小于 100BP 时，需要开始判断保本单
        - t: int，保本收益阈值，默认为 10，表示收益大于 10BP 时，可以平仓保本

    :return:
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 5))
    m = int(kwargs.get("m", 50))
    t = int(kwargs.get("t", 10))
    assert m > t > 0, "参数 m 必须大于 t"
    k1, k2, k3 = f"{pos_name}_{freq1}N{n}M{m}T{t}_BS辅助V230807".split("_")
    v1 = "其他"
    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
    if len(bars) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if op["op"] == Operate.LO:
        zdf = (bars[-1].close - op["price"]) / op["price"] * 10000
        if t < zdf < m:
            v1 = "多头保本"

    if op["op"] == Operate.SO:
        zdf = (op["price"] - bars[-1].close) / op["price"] * 10000
        if t < zdf < m:
            v1 = "空头保本"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_holds_V240428(cat: CzscTrader, **kwargs) -> OrderedDict:
    """保本单：开仓后最大盈利超过H个BP，且当前收益低于最大盈利的T%，平仓保本

    参数模板："{pos_name}_{freq1}H{h}T{t}N{n}_保本V240428"

    **信号逻辑：**

    以多头保本单为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上计算开仓后的最大盈利，记为 Y1；
    2. 计算当前收益，记为 Y2；
    3. 如果Y1 大于H，且 Y2 < Y1 * T / 100，则平仓保本。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟H100T20N5_保本V240428_空头保本_任意_任意_0')
    - Signal('日线三买多头N1_60分钟H100T20N5_保本V240428_多头保本_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - h: int，最大盈利，单位BP，默认为 100
        - t: int，最大盈利的T%，默认为 20
        - n: int，最少持有K线数量，默认为 5，表示5根K线之后开始判断

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    h = int(kwargs.get("h", 100))  # 最大盈利，单位BP
    t = int(kwargs.get("t", 20))  # 最大盈利的T%
    n = int(kwargs.get("n", 5))  # 最少持有K线数量，默认为 5，表示5根K线之后开始判断

    k1, k2, k3 = f"{pos_name}_{freq1}H{h}T{t}N{n}_保本V240428".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
    if len(bars) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if op["op"] == Operate.LO:
        y1 = (max([x.close for x in bars]) - op["price"]) / op["price"] * 10000
        y2 = (bars[-1].close - op["price"]) / op["price"] * 10000
        if y1 > h and y2 < y1 * t / 100:
            v1 = "多头保本"

    if op["op"] == Operate.SO:
        y1 = (op["price"] - min([x.close for x in bars])) / op["price"] * 10000
        y2 = (op["price"] - bars[-1].close) / op["price"] * 10000
        if y1 > h and y2 < y1 * t / 100:
            v1 = "空头保本"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_holds_V240608(cat: CzscTrader, **kwargs) -> OrderedDict:
    """保本单：多头开仓后，最低价跌破前低，当前价在成本价上方N个价位，平仓保本；空头反之。

    参数模板："{pos_name}_{freq1}W{w}N{n}_保本V240608"

    **信号逻辑：**

    以多头保本单为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上计算开仓前 W 个K线的最低价，记为 L1；
    2. 计算开仓后的最低价，记为 L2；
    3. 如果 L2 < L1，且当前价比开仓价高 N 个价位，则平仓保本。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟W20N2_保本V240608_空头保本_任意_任意_0')
    - Signal('日线三买多头N1_60分钟W20N2_保本V240608_多头保本_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - w: int，开仓前W根K线，默认为 20
        - n: int，成本价上方N个价位，默认为 2

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    w = int(kwargs.get("w", 20))  # 开仓前W根K线
    n = int(kwargs.get("n", 2))  # 成本价上方N个价位

    k1, k2, k3 = f"{pos_name}_{freq1}W{w}N{n}_保本V240608".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    # 开仓前W根K线
    w_bars = [x for x in c.bars_raw[-200:] if x.dt <= op["dt"]][-w:]
    # 开仓后的K线
    a_bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
    unique_prices = [p for x in c.bars_raw[-200:] for p in [x.high, x.low, x.close, x.open]]
    unique_prices = sorted(list(set(unique_prices)))

    if op["op"] == Operate.LO and w_bars:
        w_low = min([x.low for x in w_bars])  # 开仓前最低价
        a_low = min([x.low for x in a_bars])  # 开仓后最低价
        up_prices = [x for x in unique_prices if x > op["price"]]  # 成本价上方的价位
        # 如果开仓后的最低价低于开仓前的最低价，且当前价比开仓价高 N 个价位，则平仓保本
        if len(up_prices) > n and a_low < w_low and cat.latest_price > up_prices[n]:
            v1 = "多头保本"

    if op["op"] == Operate.SO and w_bars:
        w_high = max([x.high for x in w_bars])  # 开仓前最高价
        a_high = max([x.high for x in a_bars])  # 开仓后最高价
        down_prices = [x for x in unique_prices if x < op["price"]]  # 成本价下方的价位
        # 如果开仓后的最高价高于开仓前的最高价，且当前价比开仓价低 N 个价位，则平仓保本
        if len(down_prices) > n and a_high > w_high and cat.latest_price < down_prices[-n]:
            v1 = "空头保本"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_stop_V240428(cat: CzscTrader, **kwargs) -> OrderedDict:
    """止损单，持有N根K线后，多头跌破前低或空头升破前高，平仓

    参数模板："{pos_name}_{freq1}T{t}N{n}_止损V240428"

    **信号逻辑：**

    以多头止损为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上计算开仓 N 根K线后的最新价 close；
    2. 计算开仓前的 unique_price 列表，获取低于开仓价的列表，降序排列后的第 t 个价位作为止损价 Y；
    3. 如果 close < Y，则止损平仓。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟T5N5_止损V240428_空头止损_任意_任意_0')
    - Signal('日线三买多头N1_60分钟T5N5_止损V240428_多头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - t: int，止损多少跳，默认为 20
        - n: int，最少持有K线数量，默认为 5，表示5根K线之后开始判断

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    t = int(kwargs.get("t", 20))  # 止损多少跳
    n = int(kwargs.get("n", 5))  # 最少持有K线数量，默认为 5，表示5根K线之后开始判断

    k1, k2, k3 = f"{pos_name}_{freq1}T{t}N{n}_止损V240428".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    right_bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]

    if len(right_bars) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    left_bars = [x for x in c.bars_raw if x.dt < op["dt"]]
    unique_prices = [p for x in left_bars for p in [x.high, x.low, x.close, x.open]]
    unique_prices = sorted(list(set(unique_prices)))

    if op["op"] == Operate.LO:
        low_prices = sorted([x for x in unique_prices if x < op["price"]], reverse=True)
        if not low_prices:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        y = low_prices[-t] if len(low_prices) > t else low_prices[0]
        if right_bars[-1].close < y:
            v1 = "多头止损"

    if op["op"] == Operate.SO:
        high_prices = sorted([x for x in unique_prices if x > op["price"]])
        if not high_prices:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        y = high_prices[t] if len(high_prices) > t else high_prices[-1]
        if right_bars[-1].close > y:
            v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_take_V240428(cat: CzscTrader, **kwargs) -> OrderedDict:
    """止盈单，持有N根K线后，多头持仓期间出现T根倍量阳线或空头持仓期间出现T根倍量阴线，平仓

    参数模板："{pos_name}_{freq1}T{t}N{n}_止盈V240428"

    **信号逻辑：**

    以多头为例，计算过程如下：

    1. 从多头开仓点后N根K线开始，寻找倍量阳线，计算数量为 C；
    2. 如果 C >= T，则止盈平仓。

    **信号列表：**

    - Signal('日线三买多头N1_60分钟T5N5_止盈V240428_空头止盈_任意_任意_0')
    - Signal('日线三买多头N1_60分钟T5N5_止盈V240428_多头止盈_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - t: int，倍量K线数量止盈，默认为 3
        - n: int，最少持有K线数量，默认为 5，表示5根K线之后开始判断

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    t = int(kwargs.get("t", 3))  # 倍量K线数量止盈
    n = int(kwargs.get("n", 5))  # 最少持有K线数量，默认为 5，表示5根K线之后开始判断

    k1, k2, k3 = f"{pos_name}_{freq1}T{t}N{n}_止盈V240428".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]
    bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]

    if len(bars) < n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if op["op"] == Operate.LO:
        c1 = 0
        for i in range(1, len(bars)):
            if bars[i].close > bars[i].open and bars[i].vol > bars[i - 1].vol * 2:
                c1 += 1
        if c1 >= t:
            v1 = "多头止盈"

    if op["op"] == Operate.SO:
        c2 = 0
        for i in range(1, len(bars)):
            if bars[i].close < bars[i].open and bars[i].vol > bars[i - 1].vol * 2:
                c2 += 1
        if c2 >= t:
            v1 = "空头止盈"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_stop_V240331(cat: CzscTrader, **kwargs) -> OrderedDict:
    """根据最近N根K线的最高最低价止损，追踪止损，贡献者：谢磊

    参数模板："{pos_name}_{freq1}#{n}_止损V240331"

    **信号逻辑：**

    以多头止损为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上获取最近 N 根K线，记为 bars；
    2. 计算 bars 中的最低价，记为 ll；
    3. 如果当前价格 low < ll，则多头止损。

    空头止损逻辑同理。

    **信号列表：**

    - Signal('SMA5多头_15分钟#10_止损V240331_多头止损_任意_任意_0')
    - Signal('SMA5空头_15分钟#10_止损V240331_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，观察的K线数量，默认为 10，表示观察前10根K线

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    n = int(kwargs.get("n", 10))
    freq1 = kwargs["freq1"]
    k1, k2, k3 = f"{pos_name}_{freq1}#{n}_止损V240331".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # pos_ = [x for x in cat.positions if x.name == pos_name][0]
    pos_ = cat.get_position(pos_name)
    # 如果 pos 没有操作记录，或者最后一次操作是平仓，则不产生信号
    if len(pos_.operates) == 0 or pos_.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c: CZSC = cat.kas[freq1]
    op = pos_.operates[-1]
    bars = get_sub_elements(c.bars_raw, di=1, n=n + 1)
    _bar = bars[-1]

    # 多头止损逻辑：当前价格低于前n根K线的最低价
    if op["op"] == Operate.LO:
        ll = min([x.low for x in bars[:-1]])
        if _bar.low < ll and _bar.id > op["bid"]:
            v1 = "多头止损"

    # 空头止损逻辑：当前价格高于前n根K线的最高价
    if op["op"] == Operate.SO:
        hh = max([x.high for x in bars[:-1]])
        if _bar.high > hh and _bar.id > op["bid"]:
            v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_stop_V240608(cat: CzscTrader, **kwargs) -> OrderedDict:
    """止损：多头开仓后，最低价跌破前W根K线最低价N个价位，提示止损；空头反之。

    参数模板："{pos_name}_{freq1}W{w}N{n}_止损V240608"

    **信号逻辑：**

    以多头止损为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上计算开仓前 W 个K线的最低价，记为 L1；
    2. 计算开仓后的最低价，记为 L2；
    3. 如果 L2 < L1 - N 个价位，则提示多头止损信号。

    空头止损逻辑同理。

    **信号列表：**

    - Signal('SMA5多头_15分钟W20N10_止损V240608_多头止损_任意_任意_0')
    - Signal('SMA5空头_15分钟W20N10_止损V240608_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - w: int，开仓前W根K线，默认为 20
        - n: int，最低价下方N个价位，默认为 10

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    w = int(kwargs.get("w", 20))  # 开仓前W根K线
    n = int(kwargs.get("n", 10))  # N个价位

    k1, k2, k3 = f"{pos_name}_{freq1}W{w}N{n}_止损V240608".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    # 开仓前W根K线
    w_bars = [x for x in c.bars_raw if x.dt < op["dt"]][-w:]
    # 开仓后的K线
    a_bars = [x for x in c.bars_raw[-100:] if x.dt > op["dt"]]
    unique_prices = [p for x in c.bars_raw[-200:] for p in [x.high, x.low, x.close, x.open]]
    unique_prices = sorted(list(set(unique_prices)))  # 去重并按升序排列

    if op["op"] == Operate.LO and w_bars:
        w_low = min([x.low for x in w_bars])  # 开仓前最低价
        a_low = min([x.low for x in a_bars])  # 开仓后最低价
        w_low_prices = [x for x in unique_prices if x < w_low]  # 开仓前最低价下方的价位，升序排列
        # 如果开仓后的最低价低于开仓前的最低价向下的 N 个价位，则提示多头止损
        if len(w_low_prices) > n and a_low < w_low_prices[-n]:
            v1 = "多头止损"

    if op["op"] == Operate.SO and w_bars:
        w_high = max([x.high for x in w_bars])
        a_high = max([x.high for x in a_bars])
        w_high_prices = [x for x in unique_prices if x > w_high]
        if len(w_high_prices) > n and a_high > w_high_prices[n]:
            v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_stop_V240614(cat: CzscTrader, **kwargs) -> OrderedDict:
    """止损：多头开仓后，有超过N根K线的最低价在成本价下方，提示止损；空头反之。

    参数模板："{pos_name}_{freq1}N{n}_止损V240614"

    **信号逻辑：**

    以多头止损为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上获取开仓后的所有K线，记为 bars；
    2. 计算 bars 中的最低价小于开仓价的数量，记为 C；
    3. 如果 C >= N，则提示多头止损信号。

    空头止损逻辑同理。

    **信号列表：**

    - Signal('SMA5多头_15分钟N10_止损V240614_多头止损_任意_任意_0')
    - Signal('SMA5空头_15分钟N10_止损V240614_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，最低价下方N个价位，默认为 10

    :return: OrderedDict
    """
    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 10))  # N根K线

    k1, k2, k3 = f"{pos_name}_{freq1}N{n}_止损V240614".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    # 开仓后的K线
    a_bars = [x for x in c.bars_raw if x.dt >= op["dt"]]

    if op["op"] == Operate.LO and len([x for x in a_bars if x.low < op["price"]]) >= n:
        v1 = "多头止损"

    if op["op"] == Operate.SO and len([x for x in a_bars if x.high > op["price"]]) >= n:
        v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def pos_stop_V240717(cat: CzscTrader, **kwargs) -> OrderedDict:
    """止损：多头开仓后，有超过N根K线的最低价在成本价-ATR*0.67下方，提示止损；空头反之。贡献者：谢磊

    参数模板："{pos_name}_{freq1}N{n}T{timeperiod}_止损V240717"

    **信号逻辑：**

    以多头止损为例，计算过程如下：

    1. 从多头开仓点开始，在给定的K线周期 freq1 上获取开仓后的所有K线，记为 bars；
    2. 计算 bars 中的最低价小于（开仓价-ATR*0.67）的数量，记为 C；
    3. ATR的参数为默认参数，可以调整；
    3. 如果 C >= N，则提示多头止损信号。

    空头止损逻辑同理。

    **信号列表：**

    - Signal('SMA5多头_15分钟N3T20_止损V240717_多头止损_任意_任意_0')
    - Signal('SMA5空头_15分钟N3T20_止损V240717_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典

        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，最低价下方N个价位，默认为 3

    :return: OrderedDict
    """
    from czsc.signals.tas import update_atr_cache

    pos_name = kwargs["pos_name"]
    freq1 = kwargs["freq1"]
    n = int(kwargs.get("n", 10))  # N根K线
    timeperiod = int(kwargs.get("timeperiod", 20))  # ATR参数

    c = cat.kas[freq1]
    cache_key = update_atr_cache(c, timeperiod=timeperiod)

    k1, k2, k3 = f"{pos_name}_{freq1}N{n}T{timeperiod}_止损V240717".split("_")
    v1 = "其他"

    # 如果没有持仓策略，则不产生信号
    if not cat.kas or not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]["op"] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos.operates[-1]
    atr = [x.cache[cache_key] if x.cache.get(cache_key) is not None else 0 for x in c.bars_raw if x.dt == op["dt"]]

    # 开仓后的K线
    a_bars = [x for x in c.bars_raw if x.dt >= op["dt"]]

    if op["op"] == Operate.LO and len([x for x in a_bars if x.low < op["price"] - atr[0] * 0.67]) >= n:
        v1 = "多头止损"

    if op["op"] == Operate.SO and len([x for x in a_bars if x.high > op["price"] + atr[0] * 0.67]) >= n:
        v1 = "空头止损"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
