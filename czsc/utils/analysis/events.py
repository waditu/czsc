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

    :return: pd.DataFrame

    Example:
    =======================
    >>> df = pd.DataFrame({"dt": pd.date_range("2022-01-01", periods=10, freq="D"),
    >>>                   "symbol": "000001",
    >>>                   "close": [1, 1, 2, 2, 2, 3, 3, 3, 3, 3]})
    >>> df = overlap(df, "close")
    >>> print(df)
    =======================
    输出：
                  dt  symbol  close  close_overlap
        0 2022-01-01  000001      1            1.0
        1 2022-01-02  000001      1            2.0
        2 2022-01-03  000001      2            1.0
        3 2022-01-04  000001      2            2.0
        4 2022-01-05  000001      2            3.0
        5 2022-01-06  000001      3            1.0
        6 2022-01-07  000001      3            2.0
        7 2022-01-08  000001      3            3.0
        8 2022-01-09  000001      3            4.0
        9 2022-01-10  000001      3            5.0
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
