# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: 验证信号计算的准确性，仅适用于缠论笔相关的信号，
          技术指标构建的信号，用这个工具检查不是那么方便
"""
import sys

sys.path.insert(0, '..')
import os
import numpy as np
from loguru import logger
from typing import List
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CZSC, Signal
from czsc.objects import BI, Direction
from czsc.traders.base import CzscTrader, check_signals_acc
from czsc.signals.tas import update_ma_cache
from czsc.utils import get_sub_elements, create_single_signal
from czsc import signals
from czsc.utils.sig import get_zs_seq

os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def cxt_double_zs_V230311(c: CZSC, di=1, **kwargs):
    """两个中枢组合辅助判断BS1

    **信号逻辑：**

    1. 最后一笔向下，最近两个中枢依次向下，最后一个中枢的倒数第一笔的K线长度大于倒数第二笔的K线长度，看多；
    2. 最后一笔向上，最近两个中枢依次向上，最后一个中枢的倒数第一笔的K线长度大于倒数第二笔的K线长度，看空；

    **信号列表：**

    - Signal('15分钟_D1双中枢_BS1辅助V230311_看多_任意_任意_0')
    - Signal('15分钟_D1双中枢_BS1辅助V230311_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第 di 笔
    :return: s
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}双中枢_BS1辅助V230311".split("_")
    v1 = "其他"

    bis: List[BI] = get_sub_elements(c.bi_list, di=di, n=20)
    zss = get_zs_seq(bis)

    if len(zss) >= 2 and len(zss[-2].bis) >= 2 and len(zss[-1].bis) >= 2:
        zs1, zs2 = zss[-2], zss[-1]

        ts1 = len(zs2.bis[-1].bars)
        ts2 = len(zs2.bis[-2].bars)

        if bis[-1].direction == Direction.Down and ts1 >= ts2 * 2 and zs1.gg > zs2.gg:
            v1 = "看多"

        if bis[-1].direction == Direction.Up and ts1 >= ts2 * 2 and zs1.dd < zs2.dd:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(cxt_double_zs_V230311(cat.kas['15分钟'], di=1))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)
