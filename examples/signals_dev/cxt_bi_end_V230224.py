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


def cxt_bi_end_V230224(c: CZSC, **kwargs):
    """量价配合的笔结束辅助

    **信号逻辑：**

    1. 向下笔结束：fx_b 内最低的那根K线下影大于上影的两倍，同时fx_b内的平均成交量小于当前笔的平均成交量的0.618
    2. 向上笔结束：fx_b 内最高的那根K线上影大于下影的两倍，同时fx_b内的平均成交量大于当前笔的平均成交量的2倍

    **信号列表：**

    - Signal('15分钟_D1MO3_笔结束V230224_看多_任意_任意_0')
    - Signal('15分钟_D1MO3_笔结束V230224_看空_任意_任意_0')

    :param c: CZSC 对象
    :return: 信号字典
    """
    max_overlap = int(kwargs.get('max_overlap', 3))
    k1, k2, k3 = f"{c.freq.value}_D1MO{max_overlap}_笔结束V230224".split('_')
    v1 = '其他'
    if len(c.bi_list) <= 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    bi_bars = last_bi.raw_bars
    bi_vol_mean = np.mean([x.vol for x in bi_bars])
    fx_bars = last_bi.fx_b.raw_bars
    fx_vol_mean = np.mean([x.vol for x in fx_bars])

    bar1 = fx_bars[np.argmin([x.low for x in fx_bars])]
    bar2 = fx_bars[np.argmax([x.high for x in fx_bars])]

    if bar1.upper > bar1.lower * 2 and fx_vol_mean > bi_vol_mean * 2:
        v1 = '看空'
    elif 2 * bar2.upper < bar2.lower and fx_vol_mean < bi_vol_mean * 0.618:
        v1 = '看多'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(cxt_bi_end_V230224(cat.kas['15分钟'], max_overlap=3))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)
