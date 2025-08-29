"""
用于计算未来收益相关的因子，含有未来信息，不可用于实际交易
通常用作模型训练、因子评价的标准
"""
import numpy as np
import pandas as pd


def RET001(df, **kwargs):
    """用 close 价格计算未来 N 根K线的收益率

    参数空间：

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET001#{tag}'
    df[col] = df['close'].shift(-n) / df['close'] - 1
    df[col] = df[col].fillna(0)


def RET002(df, **kwargs):
    """用 open 价格计算未来 N 根K线的收益率

    参数空间：

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET002#{tag}'
    df[col] = df['open'].shift(-n - 1) / df['open'].shift(-1) - 1
    df[col] = df[col].fillna(0)


def RET003(df, **kwargs):
    """未来 N 根K线的收益波动率

    参数空间：

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 计算未来 N 根K线的收益波动率

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET003#{tag}'
    df['tmp'] = df['close'].pct_change()
    df[col] = df['tmp'].rolling(n).std().shift(-n)
    df[col] = df[col].fillna(0)
    df.drop(columns=['tmp'], inplace=True)


def RET004(df, **kwargs):
    """未来 N 根K线的最大收益盈亏比

    注意：
    1. 约束盈亏比的范围是 [0, 10]
    2. 当未来 N 根K线内收益最小值为0时，会导致计算结果为无穷大，此时将结果设置为10

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 计算未来 N 根K线的收益盈亏比

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET004#{tag}'
    df['max_ret'] = df['close'].rolling(n).apply(lambda x: x.max() / x[0] - 1, raw=True)
    df['min_ret'] = df['close'].rolling(n).apply(lambda x: x.min() / x[0] - 1, raw=True)
    df[col] = (df['max_ret'] / df['min_ret'].abs()).shift(-n)
    df[col] = df[col].fillna(0)
    df[col] = df[col].clip(0, 10)
    df.drop(columns=['max_ret', 'min_ret'], inplace=True)


def RET005(df, **kwargs):
    """未来 N 根K线的逐K胜率

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 滚动窗口大小

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET005#{tag}'
    df['ret'] = df['close'].pct_change()
    df[col] = df['ret'].rolling(n).apply(lambda x: np.sum(x > 0) / n).shift(-n)
    df[col] = df[col].fillna(0)
    df.drop(columns=['ret'], inplace=True)


def RET006(df, **kwargs):
    """未来 N 根K线的逐K盈亏比

    注意：
    1. 约束盈亏比的范围是 [0, 10]

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 滚动窗口大小

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET006#{tag}'
    df['ret'] = df['close'].pct_change()
    df['mean_win'] = df['ret'].rolling(n).apply(lambda x: np.sum(x[x > 0]) / np.sum(x > 0))
    df['mean_loss'] = df['ret'].rolling(n).apply(lambda x: np.sum(x[x < 0]) / np.sum(x < 0))
    df[col] = (df['mean_win'] / df['mean_loss'].abs()).shift(-n)
    df[col] = df[col].fillna(0)
    df[col] = df[col].clip(0, 10)
    df.drop(columns=['ret', 'mean_win', 'mean_loss'], inplace=True)


def RET007(df, **kwargs):
    """未来 N 根K线的最大跌幅

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 滚动窗口大小

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET007#{tag}'
    df[col] = df['close'].rolling(n).apply(lambda x: np.min(x) / x[0] - 1, raw=True).shift(-n)
    df[col] = df[col].fillna(0)


def RET008(df, **kwargs):
    """未来 N 根K线的最大涨幅

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - tag: str, 因子字段标记
        - n: int, 滚动窗口大小

    :return: None
    """
    tag = kwargs.get('tag', 'A')
    n = kwargs.get('n', 5)

    col = f'F#RET008#{tag}'
    df[col] = df['close'].rolling(n).apply(lambda x: np.max(x) / x[0] - 1, raw=True).shift(-n)
    df[col] = df[col].fillna(0)


def test_ret_functions():
    from czsc.connectors import cooperation as coo

    df = coo.dc.pro_bar(code="000001.SZ", freq="day", sdt="2020-01-01", edt="2021-01-31")
    df['dt'] = pd.to_datetime(df['dt'])
    df.rename(columns={'code': 'symbol'}, inplace=True)

    RET001(df, tag='A')
    assert 'F#RET001#A' in df.columns

    RET002(df, tag='A')
    assert 'F#RET002#A' in df.columns

    RET003(df, tag='A')
    assert 'F#RET003#A' in df.columns

    RET004(df, tag='A')
    assert 'F#RET004#A' in df.columns

    RET005(df, tag='A')
    assert 'F#RET005#A' in df.columns

    RET006(df, tag='A')
    assert 'F#RET006#A' in df.columns

    RET007(df, tag='A')
    assert 'F#RET007#A' in df.columns

    RET008(df, tag='A')
    assert 'F#RET008#A' in df.columns
