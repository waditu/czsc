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


def bar_bpm_V230227(c: CZSC, di=1, n: int = 20, th: int = 1000, **kwargs) -> OrderedDict:
    """以BP为单位的绝对动量

    **信号逻辑：**

    1. 以BP为单位的绝对动量，计算最近n根K线的涨幅，如果大于th，则为超强，否则为强势；
    2. 反之，如果小于-th，则为超弱，否则为弱势

    **信号列表：**

    - Signal('15分钟_D2N5T300_绝对动量V230227_弱势_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_强势_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_超强_任意_任意_0')
    - Signal('15分钟_D2N5T300_绝对动量V230227_超弱_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: 连续多少根K线
    :param th: 超过多少bp
    :return: 信号识别结果
    """
    k1, k2, k3, v1 = str(c.freq.value), f"D{di}N{n}T{th}", "绝对动量V230227", "其他"
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    if len(_bars) != n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bp = (_bars[-1].close / _bars[0].open - 1) * 10000
    if bp > 0:
        v1 = "超强" if bp > th else "强势"
    else:
        v1 = "超弱" if abs(bp) > th else "弱势"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_bpm_V230227(cat.kas['15分钟'], di=2, n=5, th=300))
    return s


if __name__ == '__main__':
    data_path = r'C:\ts_data'
    dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

    symbol = '000001.SZ'
    raw_bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                                  sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)

    check_signals_acc(raw_bars, get_signals)
