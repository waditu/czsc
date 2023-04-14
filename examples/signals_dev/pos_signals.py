# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/14 18:41
describe: 
"""
from collections import OrderedDict
from czsc.signals import *
from czsc.traders.base import CzscTrader
from czsc.utils import create_single_signal
from czsc.objects import Operate, Direction, Mark


def pos_fx_stop_V230414(cat: CzscTrader, **kwargs) -> OrderedDict:
    """按照开仓点附近的分型止损

    参数模板："{freq1}_{pos_name}N{n}_止损V230414"

    **信号逻辑：**

    多头止损逻辑如下，反之为空头止损逻辑：

    1. 从多头开仓点开始，在给定对的K线周期 freq1 上向前找 N 个底分型，记为 F1
    2. 将这 N 个底分型的最低点，记为 L1，如果 L1 的价格低于开仓点的价格，则止损

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
    n = int(kwargs.get('n', 3))
    k1, k2, k3 = f"{freq1}_{pos_name}N{n}_止损V230414".split("_")
    v1 = '其他'

    pos = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos.operates) == 0 or pos.operates[-1]['op'] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c = cat.kas[freq1]
    op = pos.operates[-1]

    # 多头止损逻辑
    if op['op'] == Operate.LO:
        fxs = [x for x in c.fx_list if x.mark == Mark.D and x.dt < op['dt']][-n:]
        if cat.latest_price < min([x.low for x in fxs]):
            v1 = '多头止损'

    # 空头止损逻辑
    if op['op'] == Operate.SO:
        fxs = [x for x in c.fx_list if x.mark == Mark.G and x.dt < op['dt']][-n:]
        if cat.latest_price > max([x.high for x in fxs]):
            v1 = '空头止损'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
