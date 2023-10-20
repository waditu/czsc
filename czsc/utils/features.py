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
    if df[x_col].isna().sum() > 0:
        logger.warning(f"因子列 {x_col} 存在缺失值，已自动剔除，这有可能导致后续分析结果不准确")
        df = df.dropna(subset=[x_col])

    q = kwargs.get("q", 0.05)           # 缩尾比例
    df[x_col] = df.groupby("dt")[x_col].transform(lambda x: scale(x.clip(lower=x.quantile(q), upper=x.quantile(1 - q))))
    return df


def normalize_ts_feature(df, x_col, n=10, **kwargs):
    """对时间序列数据进行归一化处理

    :param df: 因子数据，必须包含 dt, x_col 列，其中 dt 为日期，x_col 为因子值，数据样例：
    :param x_col: 因子列名
    :param n: 分层数量，默认为10
    :param kwargs:

        - min_periods: expanding 时的最小样本数量，默认为300

    :return: df, 添加了 x_col_norm, x_col_qcut, x_col分层 列
    """
    assert df[x_col].nunique() > n, "因子值的取值数量必须大于分层数量"
    min_periods = kwargs.get("min_periods", 300)
    if df[x_col].isna().sum() > 0:
        logger.warning(f"因子列 {x_col} 存在缺失值，请注意！建议先对因子缺失值进行填充")

    if f"{x_col}_norm" not in df.columns:
        df[f"{x_col}_norm"] = df[x_col].expanding(min_periods=min_periods).apply(
            lambda x: (x.iloc[-1] - x.mean()) / x.std(), raw=False)

        # 用标准化后的值填充原始值中的缺失值
        na_x = df[df[f"{x_col}_norm"].isna()][x_col].values
        df.loc[df[f"{x_col}_norm"].isna(), f"{x_col}_norm"] = na_x - na_x.mean() / na_x.std()

    if f"{x_col}_qcut" not in df.columns:
        df[f'{x_col}_qcut'] = df[x_col].expanding(min_periods=min_periods).apply(
            lambda x: pd.qcut(x, q=n, labels=False, duplicates='drop', retbins=False).values[-1], raw=False)

        na_x = df[df[f"{x_col}_qcut"].isna()][x_col].values
        df.loc[df[f"{x_col}_qcut"].isna(), f"{x_col}_qcut"] = pd.qcut(na_x, q=n, labels=False, duplicates='drop', retbins=False)
        df[f'{x_col}分层'] = df[f'{x_col}_qcut'].apply(lambda x: f'第{str(int(x+1)).zfill(2)}层')

    return df
