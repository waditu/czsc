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


def tas_first_bs_V230217(c: CZSC, di: int = 1, n: int = 10, **kwargs) -> OrderedDict:
    """均线结合K线形态的一买一卖辅助判断

    **信号逻辑：**

    1. 窗口N内的K线的最低点全部小于SMA5，且阴线数量占比超过60%，且最近三根K线创新低，最后一根K线收在SMA5上方，看多；
    2. 反之，看空。

    **信号列表：**

    - Signal('日线_D1N10SMA5_BS1辅助_一买_任意_任意_0')
    - Signal('日线_D1N10SMA5_BS1辅助_一卖_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线，1表示最后一根K线
    :param n: 窗口大小
    :param kwargs:
    :return: 信号识别结果
    """
    ma_type = kwargs.get('ma_type', 'SMA')
    timeperiod = kwargs.get('timeperiod', 5)
    key = update_ma_cache(c, ma_type, timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}{ma_type}{timeperiod}_BS1辅助".split('_')
    v1 = '其他'
    if len(c.bars_raw) < n + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    sma = [x.cache[key] for x in _bars]
    low = [x.low for x in _bars]
    _open = [x.open for x in _bars]
    close = [x.close for x in _bars]
    high = [x.high for x in _bars]

    # 窗口N内的K线的最低点全部小于SMA5
    condition_1_down = np.all(np.array(sma) > np.array(low))
    condition_1_up = np.all(np.array(sma) < np.array(high))

    n1, m1 = 0, 0
    for i in range(len(low)):
        if close[i] < _open[i]:
            n1 += 1
        if close[i] > _open[i]:
            m1 += 1
    condition_2_down = True if (n1 / len(low)) > 0.6 else False
    condition_2_up = True if (m1 / len(low)) > 0.6 else False

    # 最近三根K线创新低
    condition_3_down = True if min(low[-3:]) < min(low[:-3]) else False
    condition_3_up = True if max(high[-3:]) > max(high[:-3]) else False

    # 最后一根K线收在MA5之上/下
    condition_4_down = True if close[-1] > sma[-1] else False
    condition_4_up = True if close[-1] < sma[-1] else False

    if condition_1_down and condition_2_down and condition_3_down and condition_4_down:
        v1 = '一买'
    elif condition_1_up and condition_2_up and condition_3_up and condition_4_up:
        v1 = '一卖'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(tas_first_bs_V230217(cat.kas['15分钟'], di=1, n=21))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)







