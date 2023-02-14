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
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc import CZSC
from czsc.traders.base import CzscTrader, check_signals_acc
from czsc.utils import get_sub_elements, create_single_signal
from czsc import signals


os.environ['czsc_verbose'] = '1'

data_path = r'C:\ts_data'
dc = TsDataCache(data_path, sdt='2010-01-01', edt='20211209')

symbol = '000001.SZ'
bars = dc.pro_bar_minutes(ts_code=symbol, asset='E', freq='15min',
                          sdt='20181101', edt='20210101', adj='qfq', raw_bar=True)


def bar_amount_acc_V230214(c: CZSC, di=2, n=5, **kwargs) -> OrderedDict:
    """N根K线总成交额

    **信号描述：**

    1. 获取截至倒数第di根K线的前n根K线，计算总成交额，如果大于 t 千万，则为是，否则为否

    **信号列表：**

    - Signal('日线_D2N1_累计超10千万_是_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几根K线
    :param n: 前几根K线
    :param kwargs:
        t: 总成交额阈值
    :return: 信号识别结果
    """
    t = int(kwargs.get('t', 10))
    k1, k2, k3, v1 = f"{c.freq.value}", f"D{di}N{n}", f"累计超{t}千万", "其他"
    if len(c.bars_raw) <= di + n + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di, n)
    assert len(_bars) == n
    v1 = "是" if sum([x.amount for x in _bars]) > (t * 1e7) else "否"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(signals.vol.vol_double_ma_V230214(cat.kas['日线'], di=2))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals, freq=['日线'])







