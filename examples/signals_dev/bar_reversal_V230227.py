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


def bar_reversal_V230227(c: CZSC, di=1, avg_bp: int = 300, **kwargs) -> OrderedDict:
    """判断最近一根K线是否具有反转迹象

    **信号逻辑：**

    - 看多：当前K线为阴线，或阳线长上影; 且截止前一根K线，连续 3 / 5 / 8根K线累计涨幅超过 avg_bp * n，或 连续13根K线都是阳线
    - 反之，看空

    **信号列表：**

    - Signal('日线_D2A100_反转V230227_看多_任意_任意_0')
    - Signal('日线_D2A100_反转V230227_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param avg_bp: 平均单根K线的涨跌幅，用于判断是否是反转
    :return:
    """
    k1, k2, k3 = str(c.freq.value), f"D{di}A{avg_bp}", "反转V230227"
    v1 = "其他"
    _bars = get_sub_elements(c.bars_raw, di=di, n=14)

    if len(_bars) != 14:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bar = _bars[-1]
    left_bar = _bars[:-1]

    # 阳线长上影
    last_bar_up_c1 = last_bar.close > last_bar.open and last_bar.upper > 2 * max(last_bar.solid, last_bar.lower)

    # 阴线长下影
    last_bar_dn_c1 = last_bar.close < last_bar.open and last_bar.lower > 2 * max(last_bar.solid, last_bar.upper)

    if last_bar.close < last_bar.open or last_bar_up_c1:
        # 连续3 / 5 / 8根K线累计涨幅超过 avg_bp * n / 10000
        up_c1 = (left_bar[-1].close / left_bar[-3].open - 1) / 3 > avg_bp / 10000
        up_c2 = (left_bar[-1].close / left_bar[-5].open - 1) / 5 > avg_bp / 10000
        up_c3 = (left_bar[-1].close / left_bar[-8].open - 1) / 8 > avg_bp / 10000

        # 连续13根K线都是阳线
        up_c4 = all(bar.close > bar.open for bar in left_bar)

        if any([up_c1, up_c2, up_c3, up_c4]):
            v1 = "看空"

    if last_bar.close > last_bar.open or last_bar_dn_c1:
        # 连续3 / 5 / 8根K线累计跌幅超过 avg_bp * n / 10000
        dn_c1 = (left_bar[-1].close / left_bar[-3].open - 1) / 3 < -avg_bp / 10000
        dn_c2 = (left_bar[-1].close / left_bar[-5].open - 1) / 5 < -avg_bp / 10000
        dn_c3 = (left_bar[-1].close / left_bar[-8].open - 1) / 8 < -avg_bp / 10000

        # 连续13根K线都是阴线
        dn_c4 = all(bar.close < bar.open for bar in left_bar)

        if any([dn_c1, dn_c2, dn_c3, dn_c4]):
            v1 = "看多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(bar_reversal_V230227(cat.kas['日线'], di=2, avg_bp=300))
    return s


if __name__ == '__main__':
    data_path = r'C:\ts_data'
    dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

    symbol = '000001.SZ'
    bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                              sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)

    check_signals_acc(bars, get_signals)
