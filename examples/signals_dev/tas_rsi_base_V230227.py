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
from czsc.signals import update_rsi_cache


os.environ['czsc_verbose'] = '1'


def tas_rsi_base_V230227(c: CZSC, di=1, n: int = 6, th: int = 20, **kwargs) -> OrderedDict:
    """RSI超买超卖信号

    **信号逻辑：**

    在正常情况下，RSI指标都会在30-70的区间内波动。当6日RSI超过80时，表示市场已经处于超买区间。6日RSI达到90以上时，
    表示市场已经严重超买，股价极有可能已经达到阶段顶点。这时投资者应该果断卖出。当6日RSI下降到20时，表示市场已经处于
    超卖区间。6日RSI一旦下降到10以下，则表示市场已经严重超卖，股价极有可能会止跌回升，是很好的买入信号。

    **信号列表：**

    - Signal('日线_D2T20_RSI6V230227_超卖_向下_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超买_向上_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超买_向下_任意_0')
    - Signal('日线_D2T20_RSI6V230227_超卖_向上_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: RSI的计算周期
    :param th: RSI阈值
    :return: 信号识别结果
    """
    cache_key = update_rsi_cache(c, timeperiod=n)
    k1, k2, k3, v1 = str(c.freq.value), f"D{di}T{th}", f"{cache_key}V230227", "其他"
    _bars = get_sub_elements(c.bars_raw, di=di, n=2)
    if len(_bars) != 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    rsi1 = _bars[-1].cache[cache_key]
    rsi2 = _bars[-2].cache[cache_key]

    if rsi1 <= th:
        v1 = "超卖"
    elif rsi1 >= 100 - th:
        v1 = "超买"
    else:
        v1 = "其他"

    v2 = "向上" if rsi1 >= rsi2 else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(tas_rsi_base_V230227(cat.kas['日线'], di=2, n=6, th=20))
    return s


if __name__ == '__main__':
    data_path = r'C:\ts_data'
    dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

    symbol = '000001.SZ'
    raw_bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                                  sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)

    check_signals_acc(raw_bars, get_signals)
