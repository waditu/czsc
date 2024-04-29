# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/4/27 15:01
describe: 事件分析工具函数
"""
import numpy as np
import pandas as pd


def overlap(df: pd.DataFrame, col: str, **kwargs):
    """给定 df 和 col，计算 col 中相同值的连续出现次数

    :param df: pd.DataFrame, 至少包含 dt、symbol 和 col 列
    :param col: str，需要计算连续出现次数的列名
    :param kwargs: dict，其他参数

        - copy: bool, 是否复制 df，默认为 True
        - new_col: str, 计算结果的列名，默认为 f"{col}_overlap"
        - max_overlap: int, 最大允许连续出现次数，默认为 10

    """
    if kwargs.get("copy", True) is True:
        df = df.copy()

    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["dt"])

    new_col = kwargs.get("new_col", f"{col}_overlap")

    for symbol, dfg in df.groupby("symbol"):
        # 计算 col 相同值的连续个数，从 1 开始计数
        dfg[new_col] = dfg.groupby(df[col].ne(df[col].shift()).cumsum()).cumcount() + 1
        df.loc[dfg.index, new_col] = dfg[new_col]

    max_overlap = kwargs.get("max_overlap", 10)
    df[new_col] = np.where(df[new_col] > max_overlap, max_overlap, df[new_col])
    return df
