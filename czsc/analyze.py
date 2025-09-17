# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/3/10 11:21
describe: 缠论分型、笔的识别
"""
from loguru import logger
from typing import List
from czsc.enum import Mark, Direction
from czsc.objects import BI, FX, RawBar, NewBar
from czsc.utils.echarts_plot import kline_pro
from czsc import envs
from rs_czsc import CZSC

__all__ = ['remove_include', 'check_fx', 'check_fxs', 'check_bi', 'CZSC', 'kline_pro']

logger.disable('czsc.analyze')


def remove_include(k1: NewBar, k2: NewBar, k3: RawBar):
    """去除包含关系：输入三根k线，其中k1和k2为没有包含关系的K线，k3为原始K线

    处理逻辑如下：

    1. 首先，通过比较k1和k2的高点(high)的大小关系来确定direction的值。如果k1的高点小于k2的高点，
       则设定direction为Up；如果k1的高点大于k2的高点，则设定direction为Down；如果k1和k2的高点相等，
       则创建一个新的K线k4，与k3具有相同的属性，并返回False和k4。

    2. 接下来，判断k2和k3之间是否存在包含关系。如果存在，则根据direction的值进行处理。
        - 如果direction为Up，则选择k2和k3中的较大高点作为新K线k4的高点，较大低点作为低点，较大高点所在的时间戳(dt)作为k4的时间戳。
        - 如果direction为Down，则选择k2和k3中的较小高点作为新K线k4的高点，较小低点作为低点，较小低点所在的时间戳(dt)作为k4的时间戳。
        - 如果direction的值不是Up也不是Down，则抛出ValueError异常。

    3. 根据上述处理得到的高点、低点、开盘价(open_)、收盘价(close)，计算新K线k4的成交量(vol)和成交金额(amount)，
       并将k2中除了与k3时间戳相同的元素之外的其他元素与k3一起作为k4的元素列表(elements)。

    4. 返回一个布尔值和新的K线k4。如果k2和k3之间存在包含关系，则返回True和k4；否则返回False和k4，其中k4与k3具有相同的属性。
    """
    if k1.high < k2.high:
        direction = Direction.Up
    elif k1.high > k2.high:
        direction = Direction.Down
    else:
        k4 = NewBar(symbol=k3.symbol, id=k3.id, freq=k3.freq, dt=k3.dt, open=k3.open,
                    close=k3.close, high=k3.high, low=k3.low, vol=k3.vol, amount=k3.amount, elements=[k3])
        return False, k4

    # 判断 k2 和 k3 之间是否存在包含关系，有则处理
    if (k2.high <= k3.high and k2.low >= k3.low) or (k2.high >= k3.high and k2.low <= k3.low):

        if direction == Direction.Up:
            high = max(k2.high, k3.high)
            low = max(k2.low, k3.low)
            dt = k2.dt if k2.high > k3.high else k3.dt

        elif direction == Direction.Down:
            high = min(k2.high, k3.high)
            low = min(k2.low, k3.low)
            dt = k2.dt if k2.low < k3.low else k3.dt

        else:
            raise ValueError

        open_, close = (high, low) if k3.open > k3.close else (low, high)
        vol = k2.vol + k3.vol
        amount = k2.amount + k3.amount

        # 这里有一个隐藏Bug，len(k2.elements) 在一些及其特殊的场景下会有超大的数量，具体问题还没找到；
        # 临时解决方案是直接限定len(k2.elements)<=100
        elements = [x for x in k2.elements[:100] if x.dt != k3.dt] + [k3]
        k4 = NewBar(symbol=k3.symbol, id=k2.id, freq=k2.freq, dt=dt, open=open_,
                    close=close, high=high, low=low, vol=vol, amount=amount, elements=elements)
        return True, k4

    else:
        k4 = NewBar(symbol=k3.symbol, id=k3.id, freq=k3.freq, dt=k3.dt, open=k3.open,
                    close=k3.close, high=k3.high, low=k3.low, vol=k3.vol, amount=k3.amount, elements=[k3])
        return False, k4


def check_fx(k1: NewBar, k2: NewBar, k3: NewBar):
    """查找分型

    函数计算逻辑：

    1. 如果第二个`NewBar`对象的最高价和最低价都高于第一个和第三个`NewBar`对象的对应价格，那么它被认为是顶分型（G）。
       在这种情况下，函数会创建一个新的`FX`对象，其标记为`Mark.G`，并将其赋值给`fx`。

    2. 如果第二个`NewBar`对象的最高价和最低价都低于第一个和第三个`NewBar`对象的对应价格，那么它被认为是底分型（D）。
       在这种情况下，函数会创建一个新的`FX`对象，其标记为`Mark.D`，并将其赋值给`fx`。

    3. 函数最后返回`fx`，如果没有找到分型，`fx`将为`None`。

    :param k1: 第一个`NewBar`对象
    :param k2: 第二个`NewBar`对象
    :param k3: 第三个`NewBar`对象
    :return: `FX`对象或`None`
    """
    fx = None
    if k1.high < k2.high > k3.high and k1.low < k2.low > k3.low:
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.G, high=k2.high,
                low=k2.low, fx=k2.high, elements=[k1, k2, k3])

    if k1.low > k2.low < k3.low and k1.high > k2.high < k3.high:
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.D, high=k2.high,
                low=k2.low, fx=k2.low, elements=[k1, k2, k3])

    return fx


def check_fxs(bars: List[NewBar]) -> List[FX]:
    """输入一串无包含关系K线，查找其中所有分型

    函数的主要步骤：

    1. 创建一个空列表`fxs`用于存储找到的分型。
    2. 遍历`bars`列表中的每个元素（除了第一个和最后一个），并对每三个连续的`NewBar`对象调用`check_fx`函数。
    3. 如果`check_fx`函数返回一个`FX`对象，检查它的标记是否与`fxs`列表中最后一个`FX`对象的标记相同。如果相同，记录一个错误日志。
       如果不同，将这个`FX`对象添加到`fxs`列表中。
    4. 最后返回`fxs`列表，它包含了`bars`列表中所有找到的分型。

    这个函数的主要目的是找出`bars`列表中所有的顶分型和底分型，并确保它们是交替出现的。如果发现连续的两个分型标记相同，它会记录一个错误日志。

    :param bars: 无包含关系K线列表
    :return: 分型列表
    """
    fxs = []
    for i in range(1, len(bars) - 1):
        fx = check_fx(bars[i - 1], bars[i], bars[i + 1])
        if isinstance(fx, FX):
            # 默认情况下，fxs本身是顶底交替的，但是对于一些特殊情况下不是这样; 临时强制要求fxs序列顶底交替
            if len(fxs) >= 2 and fx.mark == fxs[-1].mark:
                logger.error(f"check_fxs错误: {bars[i].dt}，{fx.mark}，{fxs[-1].mark}")
            else:
                fxs.append(fx)
    return fxs


def check_bi(bars: List[NewBar], **kwargs):
    """输入一串无包含关系K线，查找其中的一笔

    :param bars: 无包含关系K线列表
    :return:
    """
    min_bi_len = envs.get_min_bi_len()
    fxs = check_fxs(bars)
    if len(fxs) < 2:
        return None, bars

    fx_a = fxs[0]
    if fx_a.mark == Mark.D:
        direction = Direction.Up
        fxs_b = (x for x in fxs if x.mark == Mark.G and x.dt > fx_a.dt and x.fx > fx_a.fx)
        fx_b = max(fxs_b, key=lambda fx: fx.high, default=None)

    elif fx_a.mark == Mark.G:
        direction = Direction.Down
        fxs_b = (x for x in fxs if x.mark == Mark.D and x.dt > fx_a.dt and x.fx < fx_a.fx)
        fx_b = min(fxs_b, key=lambda fx: fx.low, default=None)

    else:
        raise ValueError

    if fx_b is None:
        return None, bars

    bars_a = [x for x in bars if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
    bars_b = [x for x in bars if x.dt >= fx_b.elements[0].dt]

    # 判断fx_a和fx_b价格区间是否存在包含关系
    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)

    # 成笔的条件：1）顶底分型之间没有包含关系；2）笔长度大于等于min_bi_len
    if (not ab_include) and (len(bars_a) >= min_bi_len):
        fxs_ = [x for x in fxs if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, fxs=fxs_, direction=direction, bars=bars_a)
        return bi, bars_b
    else:
        return None, bars
