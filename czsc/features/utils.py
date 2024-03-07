# 工具函数
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import minmax_scale, scale, maxabs_scale, robust_scale


def is_event_feature(df, col, **kwargs):
    """事件类因子的判断函数

    事件因子的特征：多头事件发生时，因子值为1；空头事件发生时，因子值为-1；其他情况，因子值为0。

    :param df: DataFrame
    :param col: str, 因子字段名称
    """
    unique_values = df[col].unique()
    return all([x in [0, 1, -1] for x in unique_values])


def rolling_corr(df, col1, col2, window=300, min_periods=100, **kwargs):
    """滚动计算两个序列的相关系数

    :param df: pd.DataFrame
    :param col1: str
    :param col2: str
    :param window: int, default 300, 滚动窗口大小, None表示扩展窗口
    :param min_periods: int, default 100, 最小观测数量, 用于计算相关系数的最小观测数量
    """
    if kwargs.get("copy", False):
        df = df.copy()

    assert isinstance(df, pd.DataFrame), "df must be pd.DataFrame"
    assert col1 in df.columns, f"{col1} not in df.columns"
    assert col2 in df.columns, f"{col2} not in df.columns"

    new_col = kwargs.get("new_col", f"{col1}_corr_{col2}")
    assert min_periods < window, "min_periods must be less than window"
    df[new_col] = df[col1].rolling(window=window, min_periods=min_periods).corr(df[col2]).fillna(0)
    return df


def rolling_rank(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动排名

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_rank' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    min_periods = kwargs.get('min_periods', 2)
    new_col = new_col if new_col else f'{col}_rank'
    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).rank(pct=True)
    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_norm(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动归一化值

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_norm' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    min_periods = kwargs.get('min_periods', 2)
    new_col = new_col if new_col else f'{col}_norm'
    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: (x[-1] - x.mean()) / x.std(), raw=True)
    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_qcut(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动分位数

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_qcut' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    q = kwargs.get('q', 10)
    min_periods = kwargs.get('min_periods', q)
    new_col = new_col if new_col else f'{col}_qcut'

    def __qcut_func(x):
        return pd.qcut(x, q=q, labels=False, duplicates='drop')[-1]

    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(__qcut_func, raw=True)
    df[new_col] = df[new_col].fillna(-1)
    return df


def rolling_compare(df, col1, col2, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动归一化值

    :param df: pd.DataFrame
        待计算的数据
    :param col1: str
        第一个列名
    :param col2: str
        第二个列名
    :param window: int
        滚动窗口大小, 默认为300
    :param new_col: str
        新列名，默认为 None, 表示使用 f'{col}_norm' 作为新列名
    :param kwargs:
        min_periods: int
            最小计算周期
    """
    window = kwargs.get('window', 300)
    min_periods = kwargs.get('min_periods', 2)
    new_col = new_col if new_col else f'compare_{col1}_{col2}'
    method = kwargs.get('method', 'sub')
    assert method in ['sub', 'divide', 'lr_intercept', 'lr_coef'], "method 必须为 sub, divide, lr_intercept, lr_coef 中的一种"

    for i in range(len(df)):
        dfi = df.loc[i - window + 1:i, [col1, col2]]
        dfi = dfi.copy()
        if i < min_periods:
            df.loc[i, new_col] = 0
            continue

        if method == 'sub':
            df.loc[i, new_col] = dfi[col1].sub(dfi[col2]).mean()

        elif method == 'divide':
            df.loc[i, new_col] = dfi[col1].divide(dfi[col2]).mean()

        elif method == 'lr_intercept':
            x = dfi[col2].values.reshape(-1, 1)
            y = dfi[col1].values.reshape(-1, 1)
            reg = LinearRegression().fit(x, y)
            df.loc[i, new_col] = reg.intercept_[0]

        elif method == 'lr_coef':
            x = dfi[col2].values.reshape(-1, 1)
            y = dfi[col1].values.reshape(-1, 1)
            reg = LinearRegression().fit(x, y)
            df.loc[i, new_col] = reg.coef_[0][0]

        else:
            raise ValueError(f"method {method} not support")


def rolling_scale(df: pd.DataFrame, col: str, window=300, min_periods=100, new_col=None, **kwargs):
    """对序列进行滚动归一化

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_scale' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    df = df.sort_values("dt", ascending=True).reset_index(drop=True)
    new_col = new_col if new_col else f'{col}_scale'

    method = kwargs.get("method", "scale")
    method_map = {
        "scale": scale,
        "minmax_scale": minmax_scale,
        "maxabs_scale": maxabs_scale,
        "robust_scale": robust_scale
    }
    assert method in method_map, f"method must be one of {list(method_map.keys())}"
    scale_method = method_map[method]

    if method == "minmax_scale":
        df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: minmax_scale(x, feature_range=(-1, 1))[-1])
    else:
        df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: scale_method(x)[-1])

    df[new_col] = df[new_col].fillna(0)
    return df
