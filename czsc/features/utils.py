# 工具函数


def is_event_feature(df, col, **kwargs):
    """事件类因子的判断函数

    事件因子的特征：多头事件发生时，因子值为1；空头事件发生时，因子值为-1；其他情况，因子值为0。

    :param df: DataFrame
    :param col: str, 因子字段名称
    """
    unique_values = df[col].unique()
    if not all([isinstance(x, (int, float)) for x in unique_values]):
        raise TypeError(f"字段 {col} 中包含非法值，只能包含 int 或 float 类型的值")
    return all([x in [0, 1, -1] for x in unique_values])
