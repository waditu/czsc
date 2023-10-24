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
    for t in kwargs.get('t_seq', (5, 10, 15, 20, 30, 60)):
        df[f"TWAP{t}"] = df['close'].rolling(t).mean().shift(-t)
        df[f"sum_vol_{t}"] = df['vol'].rolling(t).sum()
        df[f"sum_vcp_{t}"] = df['vol_close_prod'].rolling(t).sum()
        df[f"VWAP{t}"] = (df[f"sum_vcp_{t}"] / df[f"sum_vol_{t}"]).shift(-t)
        price_cols.extend([f"TWAP{t}", f"VWAP{t}"])
        df.drop(columns=[f"sum_vol_{t}", f"sum_vcp_{t}"], inplace=True)

    df.drop(columns=['vol_close_prod'], inplace=True)
    # 用当前K线的收盘价填充交易价中的 nan 值
    for price_col in price_cols:
        df.loc[df[price_col].isnull(), price_col] = df[df[price_col].isnull()]['close']

    df[price_cols] = df[price_cols].round(decimals)
    return df


def update_nbars(da, price_col='close', numbers=(1, 2, 5, 10, 20, 30), move=0) -> None:
    """在da数据上新增后面 n 根 bar 的累计收益

    收益计量单位：BP；1倍涨幅 = 10000BP

    :param da: 数据，DataFrame结构
    :param price_col: 价格列
    :param numbers: 考察的bar的数目的列表
    :param move: 收益计算是否要整体移位，move必须是非负整数
        一般是当前bar的close计算收益，也可以考虑是下根bar的open。这个时候 move=1。
    :return nbars_cols: 后面n根bar的bp值列名
    """
    if price_col not in da.columns:
        raise ValueError(f"price_col {price_col} not in da.columns")

    assert move >= 0
    for n in numbers:
        da[f"n{n}b"] = (da[price_col].shift(-n - move) / da[price_col].shift(-move) - 1) * 10000.0


def update_bbars(da, price_col='close', numbers=(1, 2, 5, 10, 20, 30)) -> None:
    """在da数据上新增前面 n 根 bar 的累计收益

    :param da: K线数据，DataFrame结构
    :param price_col: 价格列
    :param numbers: 考察的bar的数目的列表
    :return: bbars_cols: 后面n根bar的bp值列名
    """
    if price_col not in da.columns:
        raise ValueError(f"price_col {price_col} not in da.columns")

    for n in numbers:
        # 收益计量单位：BP；1倍涨幅 = 10000BP
        da[f"b{n}b"] = (da[price_col] / da[price_col].shift(n) - 1) * 10000


def update_tbars(da: pd.DataFrame, event_col: str) -> None:
    """计算带 Event 方向信息的未来收益

    :param da: K线数据，DataFrame结构
    :param event_col: 事件信号列名，含有 0, 1, -1 三种值，0 表示无事件，1 表示看多事件，-1 表示看空事件
    :return:
    """
    n_seq = [int(x.strip('nb')) for x in da.columns if x[0] == 'n' and x[-1] == 'b']
    for n in n_seq:
        da[f't{n}b'] = da[f'n{n}b'] * da[event_col]
