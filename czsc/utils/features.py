# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/10/06 15:01
describe: 因子（特征）处理
"""
import pandas as pd
from loguru import logger
from sklearn.preprocessing import scale


def normalize_feature(df, x_col, **kwargs):
    """因子标准化：缩尾，然后标准化

    :param df: pd.DataFrame，数据源
    :param x_col: str，因子列名
    :param kwargs:

        - q: float，缩尾比例, 默认 0.05
    """
    df = df.copy()
    assert df[x_col].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[x_col].isna().sum())
    q = kwargs.get("q", 0.05)           # 缩尾比例
    df[x_col] = df.groupby("dt")[x_col].transform(lambda x: scale(x.clip(lower=x.quantile(q), upper=x.quantile(1 - q))))
    return df


def normalize_ts_feature(df, x_col, n=10, **kwargs):
    """对时间序列数据进行归一化处理

    :param df: 因子数据，必须包含 dt, x_col 列，其中 dt 为日期，x_col 为因子值，数据样例：
    :param x_col: 因子列名
    :param n: 分层数量，默认为10
    :param kwargs:

        - method: 分层方法，expanding 或 rolling，默认为 expanding
        - min_periods: expanding 时的最小样本数量，默认为300

    :return: df, 添加了 x_col_norm, x_col_qcut, x_col分层 列
    """
    assert df[x_col].nunique() > n, "因子值的取值数量必须大于分层数量"
    assert df[x_col].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[x_col].isna().sum())
    method = kwargs.get("method", "expanding")
    min_periods = kwargs.get("min_periods", 300)

    if f"{x_col}_norm" not in df.columns:
        if method == "expanding":
            df[f"{x_col}_norm"] = df[x_col].expanding(min_periods=min_periods).apply(
                lambda x: (x.iloc[-1] - x.mean()) / x.std(), raw=False)

        elif method == "rolling":
            df[f"{x_col}_norm"] = df[x_col].rolling(min_periods=min_periods, window=min_periods).apply(
                lambda x: (x.iloc[-1] - x.mean()) / x.std(), raw=False)

        else:
            raise ValueError("method 必须为 expanding 或 rolling")

        # 用标准化后的值填充原始值中的缺失值
        na_x = df[df[f"{x_col}_norm"].isna()][x_col].values
        df.loc[df[f"{x_col}_norm"].isna(), f"{x_col}_norm"] = na_x - na_x.mean() / na_x.std()

    if f"{x_col}_qcut" not in df.columns:
        if method == "expanding":
            df[f'{x_col}_qcut'] = df[x_col].expanding(min_periods=min_periods).apply(
                lambda x: pd.qcut(x, q=n, labels=False, duplicates='drop', retbins=False).values[-1], raw=False)

        elif method == "rolling":
            df[f'{x_col}_qcut'] = df[x_col].rolling(min_periods=min_periods, window=min_periods).apply(
                lambda x: pd.qcut(x, q=n, labels=False, duplicates='drop', retbins=False).values[-1], raw=False)

        else:
            raise ValueError("method 必须为 expanding 或 rolling")

        # 用分位数后的值填充原始值中的缺失值
        na_x = df[df[f"{x_col}_qcut"].isna()][x_col].values
        df.loc[df[f"{x_col}_qcut"].isna(), f"{x_col}_qcut"] = pd.qcut(na_x, q=n, labels=False, duplicates='drop', retbins=False)

        if df[f'{x_col}_qcut'].isna().sum() > 0:
            logger.warning(f"因子 {x_col} 分层存在 {df[f'{x_col}_qcut'].isna().sum()} 个缺失值，已使用前值填充")
            df[f'{x_col}_qcut'] = df[f'{x_col}_qcut'].ffill()

        df[f'{x_col}分层'] = df[f'{x_col}_qcut'].apply(lambda x: f'第{str(int(x+1)).zfill(2)}层')

    return df


def feture_cross_layering(df, x_col, **kwargs):
    """因子在时间截面上分层

    :param df: 因子数据，数据样例：

        ===================  ========  ===========  ==========  ==========
        dt                   symbol       factor01    factor02    factor03
        ===================  ========  ===========  ==========  ==========
        2022-12-19 00:00:00  ZZUR9001  -0.0221211    0.034236    0.0793672
        2022-12-20 00:00:00  ZZUR9001  -0.0278691    0.0275818   0.0735083
        2022-12-21 00:00:00  ZZUR9001  -0.00617075   0.0512298   0.0990967
        2022-12-22 00:00:00  ZZUR9001  -0.0222238    0.0320096   0.0792036
        2022-12-23 00:00:00  ZZUR9001  -0.0375133    0.0129455   0.059491
        ===================  ========  ===========  ==========  ==========

    :param x_col: 因子列名
    :param kwargs:

        - n: 分层数量，默认为10

    :return: df, 添加了 x_col分层 列
    """
    n = kwargs.get("n", 10)
    assert 'dt' in df.columns, "因子数据必须包含 dt 列"
    assert 'symbol' in df.columns, "因子数据必须包含 symbol 列"
    assert x_col in df.columns, "因子数据必须包含 {} 列".format(x_col)
    assert df['symbol'].nunique() > n, "标的数量必须大于分层数量"

    if df[x_col].nunique() > n:
        def _layering(x):
            return pd.qcut(x, q=n, labels=False, duplicates='drop')
        df[f'{x_col}分层'] = df.groupby('dt')[x_col].transform(_layering)
    else:
        sorted_x = sorted(df[x_col].unique())
        df[f'{x_col}分层'] = df[x_col].apply(lambda x: sorted_x.index(x))
    df[f"{x_col}分层"] = df[f"{x_col}分层"].fillna(-1)
    df[f'{x_col}分层'] = df[f'{x_col}分层'].apply(lambda x: f'第{str(int(x+1)).zfill(2)}层')
    return df
