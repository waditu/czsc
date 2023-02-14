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
from typing import List
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CzscAdvancedTrader, CZSC
from czsc.objects import Signal, Freq, RawBar
from czsc.utils import get_sub_elements, create_single_signal
from czsc.sensors.utils import check_signals_acc
from czsc import signals


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def bar_single_V230214(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
    """单根K线的状态

    **信号描述：**

    1. 上涨阳线，下跌阴线；
    2. 长实体，长上影，长下影，其他；

    **信号列表：**

    - Signal('日线_D2T10_状态_阴线_长实体_任意_0')
    - Signal('日线_D2T10_状态_阳线_长实体_任意_0')
    - Signal('日线_D2T10_状态_阴线_长上影_任意_0')
    - Signal('日线_D2T10_状态_阳线_长上影_任意_0')
    - Signal('日线_D2T10_状态_阴线_长下影_任意_0')
    - Signal('日线_D2T10_状态_阳线_长下影_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param kwargs:
        t: 长实体、长上影、长下影的阈值，默认为 1.0
    :return: 信号识别结果
    """
    t = kwargs.get("t", 1.0)
    t = int(round(t, 1) * 10)

    k1, k2, k3 = f"{c.freq.value}", f"D{di}T{t}", "状态"
    v1 = "其他"
    if len(c.bars_raw) < di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    k = c.bars_raw[-di]
    v1 = "阳线" if k.close > k.open else "阴线"

    if k.solid > (k.upper + k.lower) * t / 10:
        v2 = "长实体"
    elif k.upper > (k.solid + k.lower) * t / 10:
        v2 = "长上影"
    elif k.lower > (k.solid + k.upper) * t / 10:
        v2 = "长下影"
    else:
        v2 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_single_V230214(cat.kas['日线'], di=2))
    return s


def trader_strategy_base(symbol):
    tactic = {
        "symbol": symbol,
        "base_freq": '15分钟',
        "freqs": ['30分钟', '60分钟', '日线'],
        "get_signals": get_signals,
        "signals_n": 0,
    }
    return tactic


if __name__ == '__main__':
    # 直接查看全部信号的隔日快照
    check_signals_acc(bars, strategy=trader_strategy_base)

    # 查看指定信号的隔日快照
    # signals = [
    #     Signal("5分钟_倒9笔_类买卖点_类一买_任意_任意_0"),
    #     Signal("5分钟_倒9笔_类买卖点_类一卖_任意_任意_0"),
    # ]
    # check_signals_acc(bars, signals=signals, get_signals=get_signals)






