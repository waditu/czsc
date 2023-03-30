# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/30 16:57
describe: 
"""
"""
author: nora
email: cjz741262008cjz@gmail.com
create_dt: 2023/03/28
describe: r-breaker
"""
import sys
sys.path.insert(0, '../..')
import os
import numpy as np
from collections import OrderedDict
from czsc import CZSC, CzscSignals
from czsc.data.ts_cache import TsDataCache
from czsc.traders.base import CzscTrader, check_signals_acc
from czsc.utils import get_sub_elements, create_single_signal, resample_bars


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='1min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def bar_r_breaker_V230326(c: CZSC, **kwargs):
    """窗口内最大实体K线的中间价区分多空

    参数模板："{freq}_RBreaker_BS辅助V230326"

    **信号逻辑：**

    参见：https://www.myquant.cn/docs/python_strategyies/425

    空仓时：突破策略
    空仓时，当盘中价格>突破买入价，则认为上涨的趋势还会继续，开仓做多；
    空仓时，当盘中价格<突破卖出价，则认为下跌的趋势还会继续，开仓做空。

    持仓时：反转策略
    持多单时：当日内最高价>观察卖出价后，盘中价格回落，跌破反转卖出价构成的支撑线时，采取反转策略，即做空；
    持空单时：当日内最低价<观察买入价后，盘中价格反弹，超过反转买入价构成的阻力线时，采取反转策略，即做多。

    **信号列表：**

    - Signal('日线_RBreaker_BS辅助V230326_做多_反转_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做空_趋势_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做多_趋势_任意_0')
    - Signal('日线_RBreaker_BS辅助V230326_做空_反转_任意_0')

    :return: 信号字典
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_RBreaker_BS辅助V230326".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    # 计算六个价位
    H, C, L = c.bars_raw[-2].high, c.bars_raw[-2].close, c.bars_raw[-2].low
    P = (H + C + L) / 3
    break_buy = H + 2 * P - 2 * L
    see_sell = P + H - L
    verse_sell = 2 * P - L
    verse_buy = 2 * P - H
    see_buy = P - (H - L)
    break_sell = L - 2 * (H - P)

    # 根据价格位置判断信号
    current_bar = c.bars_raw[-1]
    if current_bar.close > break_buy:
        v1 = '做多'
        v2 = '趋势'
    elif current_bar.close < break_sell:
        v1 = '做空'
        v2 = '趋势'
    elif current_bar.high > see_sell and current_bar.close < verse_sell:
        v1 = '做空'
        v2 = '反转'
    elif current_bar.low > see_buy and current_bar.close > verse_buy:
        v1 = '做多'
        v2 = '反转'
    else:
        v1 = '其他'
        v2 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_r_breaker_V230326(cat.kas['日线']))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals, freqs=['1分钟', '日线'])
