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
from czsc.utils import get_sub_elements
from czsc.sensors.utils import check_signals_acc
from czsc import signals


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def create_single_signal(**kwargs) -> OrderedDict:
    """创建单个信号"""
    s = OrderedDict()
    k1, k2, k3 = kwargs.get('k1', '任意'), kwargs.get('k2', '任意'), kwargs.get('k3', '任意')
    v1, v2, v3 = kwargs.get('v1', '任意'), kwargs.get('v2', '任意'), kwargs.get('v3', '任意')
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3, score=kwargs.get('score', 0))
    s[v.key] = v.value
    return s


def bar_fake_break_V230204(c: CZSC, di=1, **kwargs) -> OrderedDict:
    """假突破

    **信号描述：**

    1. 向下假突破，最近N根K线的滑动M窗口出现过大幅下跌破K线重叠中枢，随后几根K线快速拉回，看多；
    2. 反之，向上假突破，看空。

    **信号列表：**

    - Signal('15分钟_D1N20M5_假突破_看空_任意_任意_0')
    - Signal('15分钟_D1N20M5_假突破_看多_任意_任意_0')

    :param c: CZSC 对象
    :param di: 从最新的第几个 bar 开始计算
    :return: 信号字典
    """
    n = kwargs.get('n', 20)
    m = kwargs.get('m', 5)
    k1, k2, k3 = f"{c.freq.value}_D{di}N{n}M{m}_假突破".split("_")

    v1 = '其他'
    last_bars: List[RawBar] = get_sub_elements(c.bars_raw, di=di, n=n)

    def __is_overlap(_bars):
        """判断是否是重叠，如果是重叠，返回True和中枢的上下下轨"""
        if min([bar.high for bar in _bars]) > max([bar.low for bar in _bars]):
            return True, min([bar.low for bar in _bars]), max([bar.high for bar in _bars])
        else:
            return False, None, None

    if len(last_bars) != 20 or last_bars[-1].solid < last_bars[-1].upper + last_bars[-1].lower:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 找出最近N根K线的滑动M窗口出现过K线重叠中枢
    right_bars = []
    dd = 0
    gg = 0
    for i in range(m, n - m):
        _overlap, dd, gg = __is_overlap(last_bars[-i - m:-i])
        if _overlap:
            right_bars = last_bars[-i:]
            break

    if last_bars[-1].close > last_bars[-1].open:

        # 条件1：收盘价新高或者最高价新高
        c1_a = last_bars[-1].high == max([bar.high for bar in last_bars])
        c1_b = last_bars[-1].close == max([bar.close for bar in last_bars])
        c1 = c1_a or c1_b

        # 条件2：随后几根K线跌破中枢下跪快速拉回
        c2 = 0 < min([bar.low for bar in right_bars]) < dd if right_bars else False

        if c1 and c2:
            v1 = "看多"

    if last_bars[-1].close < last_bars[-1].open:
        # 条件1：收盘价新低或者最低价新低
        c1_a = last_bars[-1].low == min([bar.low for bar in last_bars])
        c1_b = last_bars[-1].close == min([bar.close for bar in last_bars])
        c1 = c1_a or c1_b

        # 条件2：随后几根K线跌破中枢下跪快速拉回
        c2 = max([bar.high for bar in right_bars]) > gg > 0 if right_bars else False

        if c1 and c2:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_fake_break_V230204(cat.kas['日线'], di=2))
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






