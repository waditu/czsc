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

    函数计算逻辑：

    1. 首先，检查因子列x_col是否存在缺失值，如果存在缺失值，则抛出异常，提示缺失值的数量。
    2. 从kwargs参数中获取缩尾比例q的值，默认为0.05。
    3. 对因子列进行缩尾操作，首先根据 dt 分组，然后使用lambda函数对每个组内的因子进行缩尾处理，
       将超过缩尾比例的值截断，并使用scale函数进行标准化。
    4. 将处理后的因子列重新赋值给原始DataFrame对象的对应列。

    :param df: pd.DataFrame，数据
    :param x_col: str，因子列名
    :param kwargs:

        - q: float，缩尾比例, 默认 0.05

    :return: pd.DataFrame，处理后的数据
    """
    df = df.copy()
    assert df[x_col].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[x_col].isna().sum())
    q = kwargs.get("q", 0.05)           # 缩尾比例
    df[x_col] = df.groupby("dt")[x_col].transform(lambda x: scale(x.clip(lower=x.quantile(q), upper=x.quantile(1 - q))))
    return df


def normalize_ts_feature(df, x_col, n=10, **kwargs):
    """对时间序列数据进行归一化处理

    函数计算逻辑：

    1. 首先，进行一系列的断言检查，确保因子值的取值数量大于分层数量，并且因子列没有缺失值。
    2. 从kwargs参数中获取分层方法method的值，默认为"expanding"，以及min_periods的值，默认为300。
    3. 如果在DataFrame的列中不存在x_col_norm列，则进行以下操作：
        - 如果分层方法是"expanding"，则使用expanding函数对因子列进行处理，计算每个时间点的标准化值，公式为(当前值 - 平均值) / 标准差。
        - 如果分层方法是"rolling"，则使用rolling函数对因子列进行处理，计算每个窗口的标准化值，窗口大小为min_periods，公式同上。
        - 如果分层方法不是上述两种情况，则抛出错误。
        - 对于缺失值，获取原始值，然后进行标准化。

    4. 如果在DataFrame的列中不存在x_col_qcut列，则进行以下操作：
        - 如果分层方法是"expanding"，则使用expanding函数对因子列进行处理，计算每个时间点的分位数，将其转化为分位数的标签（0到n-1）。
        - 如果分层方法是"rolling"，则使用rolling函数对因子列进行处理，计算每个窗口的分位数，窗口大小为min_periods。
        - 如果分层方法不是上述两种情况，则抛出错误。
        - 使用分位数后的值填充原始值中的缺失值。
        - 对于缺失值，获取原始值，然后进行分位数处理分层。
        - 创建一个新的列x_col分层，根据分位数的标签值，将其转化为"第xx层"的字符串形式。

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

        # 对于缺失值，获取原始值，然后进行标准化
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

        # 对于缺失值，获取原始值，然后进行分位数处理分层
        na_x = df[df[f"{x_col}_qcut"].isna()][x_col].values
        df.loc[df[f"{x_col}_qcut"].isna(), f"{x_col}_qcut"] = pd.qcut(na_x, q=n, labels=False, duplicates='drop', retbins=False)

        if df[f'{x_col}_qcut'].isna().sum() > 0:
            logger.warning(f"因子 {x_col} 分层存在 {df[f'{x_col}_qcut'].isna().sum()} 个缺失值，已使用前值填充")
            df[f'{x_col}_qcut'] = df[f'{x_col}_qcut'].ffill()

        df[f'{x_col}分层'] = df[f'{x_col}_qcut'].apply(lambda x: f'第{str(int(x+1)).zfill(2)}层')

    return df


def feture_cross_layering(df, x_col, **kwargs):
    """对因子数据在时间截面上进行分层处理

    函数计算逻辑：

    1. 首先从参数中获取分层数量 n，默认为10。
    2. 确保数据 df 包含 dt、symbol 和指定的因子列 x_col， 确保标的数量大于分层数量。
    3. 如果因子列的唯一值数量大于分层数量，使用 pd.qcut 函数将因子列进行分层，按照分位数进行分组。
    4. 如果因子列的唯一值数量小于等于分层数量，按照因子列的唯一值进行排序，并将每个因子值映射为对应的层级。
    5. 将分层结果转换为字符串形式，以表示层级。

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
