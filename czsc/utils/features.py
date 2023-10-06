# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/10/06 15:01
describe: 因子（特征）处理
"""
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
