# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 18:50
"""
import warnings
import pandas as pd
import numpy as np
from tqdm import tqdm
from typing import Callable, List, AnyStr
from czsc.traders.advanced import CzscAdvancedTrader, BarGenerator, RawBar
from czsc.data.ts_cache import TsDataCache


def get_index_beta(dc: TsDataCache, sdt: str, edt: str, indices=None):
    """获取基准指数的Beta

    :param dc: Tushare 数据缓存对象
    :param sdt: 开始日期
    :param edt: 结束日期
    :param indices: 基准指数列表
    :return: beta
    """
    if not indices:
        indices = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']

    beta = {}
    for ts_code in indices:
        df = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq='D', asset="I", raw_bar=False)
        beta[ts_code] = df
    return beta


def generate_signals(bars: List[RawBar], sdt: AnyStr, base_freq: AnyStr, freqs: List[AnyStr], get_signals: Callable):
    """获取历史信号

    :param bars: 日线
    :param sdt: 信号计算开始时间
    :param base_freq: 合成K线的基础周期
    :param freqs: K线周期列表
    :param get_signals: 单级别信号计算函数
    :return: signals
    """
    sdt = pd.to_datetime(sdt)
    bars_left = [x for x in bars if x.dt < sdt]
    if len(bars_left) <= 500:
        bars_left = bars[:500]
        bars_right = bars[500:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]

    if len(bars_right) == 0:
        warnings.warn("右侧K线为空，无法进行信号生成", category=RuntimeWarning)
        return []

    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    signals = []
    ct = CzscAdvancedTrader(bg, get_signals)
    for bar in tqdm(bars_right, desc=f'generate signals of {bg.symbol}'):
        ct.update(bar)
        signals.append(dict(ct.s))
    return signals


def max_draw_down(n1b: List):
    """最大回撤

    参考：https://blog.csdn.net/weixin_38997425/article/details/82915386

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 最大回撤起止位置和最大回撤
    """
    curve = np.cumsum(n1b)
    # 获取结束位置
    i = np.argmax((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve))
    if i == 0:
        return 0, 0, 0

    # 获取开始位置
    j = np.argmax(curve[:i])
    mdd = int((curve[j] - curve[i]) / curve[j] * 10000) / 10000
    return j, i, mdd
