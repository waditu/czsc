# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:04
describe: 交易价格敏感性分析相关的工具函数
"""
import pandas as pd
from typing import List, Union
from czsc.objects import RawBar


def cal_trade_price(bars: Union[List[RawBar], pd.DataFrame], decimals=3, **kwargs):
    """计算给定品种基础周期K线数据的交易价格

    :param bars: 基础周期K线数据，一般是1分钟周期的K线
    :param decimals: 保留小数位数，默认值3
    :return: 交易价格表
    """
    df = pd.DataFrame(bars) if isinstance(bars, list) else bars

    # 下根K线开盘、收盘
    df['next_open'] = df['open'].shift(-1)
    df['next_close'] = df['close'].shift(-1)
    price_cols = ['next_open', 'next_close']

    # TWAP / VWAP 价格
    df['vol_close_prod'] = df['vol'] * df['close']
    for t in kwargs.get('t_seq', (5, 10, 15,  20, 30, 60)):
        df[f"TWAP{t}"] = df['close'].rolling(t).mean().shift(-t)
        df[f"sum_vol_{t}"] = df['vol'].rolling(t).sum()
        df[f"sum_vcp_{t}"] = df['vol_close_prod'].rolling(t).sum()
        df[f"VWAP{t}"] = (df[f"sum_vcp_{t}"] / df[f"sum_vol_{t}"]).shift(-t)
        price_cols.extend([f"TWAP{t}", f"VWAP{t}"])

    # 用当前K线的收盘价填充交易价中的 nan 值
    for price_col in price_cols:
        df.loc[df[price_col].isnull(), price_col] = df[df[price_col].isnull()]['close']

    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'amount'] + price_cols].round(decimals)
    return df
