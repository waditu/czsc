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
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CZSC, Signal
from czsc.traders.base import CzscTrader, check_signals_acc
from czsc.signals.tas import update_ma_cache
from czsc.utils import get_sub_elements, create_single_signal
from czsc import signals

os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def bar_vol_bs1_V230224(c: CZSC, di: int = 1, n: int = 20, **kwargs):
    """量价配合的高低点判断

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


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_vol_bs1_V230224(cat.kas['15分钟'], di=2, n=34))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)
