# -*- coding: utf-8 -*-
# @Time    : 2023/6/10 13:56
# @Author  : 琅盎
# @FileName: ER.py
# @Software: PyCharm
from collections import OrderedDict

import numpy as np
import pandas as pd
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def er_up_dw_line_V230604(c: CZSC, **kwargs) -> OrderedDict:
    """ER价格动量指标，贡献者：琅盎

    参数模板："{freq}_D{di}W{w}N{n}_ER价格动量V230604"

    **信号逻辑：**

    er 为动量指标。用来衡量市场的多空力量对比。在多头市场，
    人们会更贪婪地在接近高价的地方买入，BullPower 越高则当前
    多头力量越强；而在空头市场，人们可能因为恐惧而在接近低价
    的地方卖出。BearPower 越低则当前空头力量越强。当两者都大
    于 0 时，反映当前多头力量占据主导地位；两者都小于 0 则反映
    空头力量占据主导地位。
    如果 BearPower 上穿 0，则产生买入信号；
    如果 BullPower 下穿 0，则产生卖出信号。

    **信号列表：**

    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第10层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第9层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第8层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第5层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第1层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第10层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第2层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第6层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第7层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第8层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第9层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第4层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第5层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第7层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第3层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第2层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第6层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第1层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线下方_第4层_任意_0')
    - Signal('日线_D1W21N10_ER价格动量V230604_均线上方_第3层_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为105

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 60))
    n = int(kwargs.get("n", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}N{n}_ER价格动量V230604".split('_')

    cache_key = f"ER{w}"
    for i, bar in enumerate(c.bars_raw, 1):
        if cache_key in bar.cache:
            continue
        _bars = c.bars_raw[i-w:i]
        ma = np.mean([x.close for x in _bars])
        bull_power = bar.high - ma if bar.high > ma else bar.low - ma
        bar.cache.update({cache_key: bull_power})

    v1 = "其他"
    if len(c.bars_raw) < di + w + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=w*10)
    factors = [x.cache[cache_key] for x in _bars]
    factors = [x for x in factors if x * factors[-1] > 0]

    v1 = "均线上方" if factors[-1] > 0 else "均线下方"
    q = pd.cut(factors, n, labels=list(range(1, n+1)), precision=5, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{q}层")


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20171101', '20210101', fq='前复权')

    signals_config = [
        {'name': er_up_dw_line_V230604, 'freq': '日线', 'di': 1, 'w': 21, 'n': 10},
    ]
    check_signals_acc(bars, signals_config=signals_config)


if __name__ == '__main__':
    main()