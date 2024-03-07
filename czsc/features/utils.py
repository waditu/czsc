# 工具函数
import pandas as pd


def is_event_feature(df, col, **kwargs):
    """事件类因子的判断函数

    事件因子的特征：多头事件发生时，因子值为1；空头事件发生时，因子值为-1；其他情况，因子值为0。

    :param df: DataFrame
    :param col: str, 因子字段名称
    """
    unique_values = df[col].unique()
    return all([x in [0, 1, -1] for x in unique_values])


def rolling_corr(df, col1, col2, window=None, min_periods=10, **kwargs):
    """滚动计算两个序列的相关系数

    :param df: pd.DataFrame
    :param col1: str
    :param col2: str
    :param window: int, default None, 滚动窗口大小, None表示扩展窗口
    :param min_periods: int
    """
    if kwargs.get("copy", False):
        df = df.copy()

    assert isinstance(df, pd.DataFrame), "df must be pd.DataFrame"
    assert col1 in df.columns, f"{col1} not in df.columns"
    assert col2 in df.columns, f"{col2} not in df.columns"

    new_col = kwargs.get("new_col", f"{col1}_corr_{col2}")
    if window is None or window <= 0:
        df[new_col] = df[col1].expanding(min_periods=min_periods).corr(df[col2]).fillna(0)
    else:
        assert min_periods < window, "min_periods must be less than window"
        df[new_col] = df[col1].rolling(window=window, min_periods=min_periods).corr(df[col2]).fillna(0)
    return df
