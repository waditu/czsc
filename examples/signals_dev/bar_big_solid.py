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


def bar_big_solid_V230215(c: CZSC, di: int = 1, n: int = 20, **kwargs):
    """窗口内最大实体K线的中间价区分多空

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
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}_MID".split('_')
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)

    # 找到窗口内最大实体K线
    max_i = np.argmax([x.solid for x in _bars])
    max_solid_bar = _bars[max_i]
    max_solid_mid = min(max_solid_bar.open, max_solid_bar.close) + 0.5 * max_solid_bar.solid

    v1 = '看多' if c.bars_raw[-1].close > max_solid_mid else '看空'
    v2 = '大阳' if max_solid_bar.close > max_solid_bar.open else '大阴'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_big_solid_V230215(cat.kas['日线'], di=1, n=10))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)







