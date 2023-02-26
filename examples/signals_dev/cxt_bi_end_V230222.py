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
from czsc.objects import Mark
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


def cxt_bi_end_V230222(c: CZSC, **kwargs) -> OrderedDict:
    """当前是最后笔的第几次新低底分型或新高顶分型，用于笔结束辅助

    **信号逻辑：**

    1. 取最后笔及未成笔的分型，
    2. 当前如果是顶分型，则看当前顶分型是否新高，是第几个新高
    2. 当前如果是底分型，则看当前底分型是否新低，是第几个新低

    **信号列表：**

    - Signal('15分钟_D1MO3_结束辅助_新低_第1次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第2次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第1次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第2次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第3次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第4次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第3次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第4次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第5次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第5次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第6次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第6次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第7次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第7次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    max_overlap = int(kwargs.get('max_overlap', 3))
    k1, k2, k3 = f"{c.freq.value}_D1MO{max_overlap}_结束辅助".split('_')
    v1 = '其他'
    v2 = '其他'

    if not c.ubi_fxs:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    # 为了只取最后一笔以来的分型，没有用底层fx_list
    fxs = []
    if c.bi_list:
        fxs.extend(c.bi_list[-1].fxs[1:])
    ubi_fxs = c.ubi_fxs
    for x in ubi_fxs:
        if not fxs or x.dt > fxs[-1].dt:
            fxs.append(x)

    # 出分型那刻出信号，或者分型和最后一根bar相差 max_overlap 根K线时间内
    if (fxs[-1].elements[-1].dt == c.bars_ubi[-1].dt) or (c.bars_raw[-1].id - fxs[-1].raw_bars[-1].id <= max_overlap):
        if fxs[-1].mark == Mark.G:
            up = [x for x in fxs if x.mark == Mark.G]
            high_max = float('-inf')
            cnt = 0
            for fx in up:
                if fx.high > high_max:
                    cnt += 1
                    high_max = fx.high
            if fxs[-1].high == high_max:
                v1 = '新高'
                v2 = cnt

        else:
            down = [x for x in fxs if x.mark == Mark.D]
            low_min = float('inf')
            cnt = 0
            for fx in down:
                if fx.low < low_min:
                    cnt += 1
                    low_min = fx.low
            if fxs[-1].low == low_min:
                v1 = '新低'
                v2 = cnt

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{v2}次")


def get_signals(cat: CzscTrader) -> OrderedDict:
    s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
    # 使用缓存来更新信号的方法
    s.update(cxt_bi_end_V230222(cat.kas['15分钟']))
    return s


if __name__ == '__main__':
    check_signals_acc(bars, get_signals)







