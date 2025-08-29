# 标准量价因子
import inspect
import numpy as np
import pandas as pd


def VPF001(df, **kwargs):
    """比较开盘价、收盘价与当日最高价和最低价的中点的关系，来判断市场的强弱

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数
        - tag: str, defaults to 'N2'  因子字段标记
        - num: int, defaults to 2  参数值
    """
    num = kwargs.get('num', 2)
    tag = kwargs.get('tag', f'N{num}')

    factor_name = inspect.stack()[0].function
    factor_col = f'F#{factor_name}#{tag}'

    con = df['open'] >= 1 / num * (df['high'] + df['low'])
    con &= df['close'] >= 1 / num * (df['high'] + df['low'])

    red = df['open'] < 1 / num * (df['high'] + df['low'])
    red &= df['close'] < 1 / num * (df['high'] + df['low'])

    df[factor_col] = 0
    df[factor_col] = np.where(con, -1, df[factor_col])
    df[factor_col] = np.where(red, 1, df[factor_col])


def VPF002(df, **kwargs):
    """比较过去收益率的正负，以及当日最高价、最低价与开盘价或收盘价的关系

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, defaults to 'N4'  因子字段标记
        - num: int, defaults to 4  参数值

    :return: None
    """
    num = kwargs.get('num', 4)
    tag = kwargs.get('tag', f'N{num}')

    factor_name = inspect.stack()[0].function
    factor_col = f'F#{factor_name}#{tag}'

    df['return'] = df['close'] / df['close'].shift(1) - 1
    red1 = df['return'].rolling(window=num, min_periods=1).sum() >= 0
    red2 = (df['high'] - df['close']) / (df['close'] - df['low']) >= 1

    df[factor_col] = np.where(red1 | red2, 1, -1)
    df.drop(columns=['return'], axis=1, inplace=True)


def VPF003(df, **kwargs):
    """比较过去N天最高价、最低价、开盘价和收盘价的比例，判断市场强弱

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str
        - num: int, defaults to 60  参数值
    """
    num = kwargs.get('num', 2)
    tag = kwargs.get('tag', f'N{num}')

    factor_name = inspect.stack()[0].function
    factor_col = f'F#{factor_name}#{tag}'

    df['hol'] = (df['high'] - df['open']) / (df['high'] - df['low'])
    df['clh'] = (df['close'] - df['low']) / (df['high'] - df['low'])

    con = df['hol'].rolling(window=num, min_periods=1).mean() >= 0.5
    con1 = (df['high'] + df['low'] - df['open'] - df['close']) >= 0
    df[factor_col] = np.where(con | con1, 1, -1)
    red = df['clh'].rolling(window=num, min_periods=1).mean() >= 0.5
    df.loc[red, factor_col] = -1

    df.drop(['hol', 'clh'], axis=1, inplace=True)


def VPF004(df, **kwargs):
    """EMA指标

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, EMA的周期参数

    :return: None
    """
    n = kwargs.get('n', 7)
    tag = kwargs.get('tag', f'N{n}')

    factor_name = inspect.stack()[0].function
    factor_col = f'F#{factor_name}#{tag}'

    ema1 = df['close'].ewm(span=n, adjust=False).mean()
    ema2 = ema1.ewm(span=n, adjust=False).mean()
    ema3 = ema2.ewm(span=n, adjust=False).mean()
    df[factor_col] = 3 * (ema1 - ema2) + ema3
    df[factor_col] = df[factor_col].fillna(0)
