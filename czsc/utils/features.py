# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/10/06 15:01
describe: 因子（特征）处理
"""
import pandas as pd


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
    from sklearn.preprocessing import scale

    df = df.copy()
    assert df[x_col].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[x_col].isna().sum())
    q = kwargs.get("q", 0.05)  # 缩尾比例
    df[x_col] = df.groupby("dt")[x_col].transform(lambda x: scale(x.clip(lower=x.quantile(q), upper=x.quantile(1 - q))))
    return df


def normalize_ts_feature(df, x_col, n=10, **kwargs):
    """对时间序列数据进行归一化处理

    :param df: 因子数据，必须包含 dt, x_col 列，其中 dt 为日期，x_col 为因子值
    :param x_col: 因子列名
    :param n: 分层数量，默认为10
    :param kwargs:

        - window: 窗口大小，默认为2000
        - min_periods: 最小样本数量，默认为300

    :return: df, 添加了 x_col_norm, x_col_qcut, x_col分层 列
    """
    assert df[x_col].nunique() > n * 2, "因子值的取值数量必须大于分层数量"
    assert df[x_col].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[x_col].isna().sum())
    window = kwargs.get("window", 2000)
    min_periods = kwargs.get("min_periods", 300)

    # 不能有 inf 和 -inf
    if df.loc[df[x_col].isin([float("inf"), float("-inf")]), x_col].shape[0] > 0:
        raise ValueError(f"存在 {x_col} 为 inf / -inf 的数据")

    if f"{x_col}_qcut" not in df.columns:
        df[f"{x_col}_qcut"] = (
            df[x_col]
            .rolling(min_periods=min_periods, window=min_periods)
            .apply(lambda x: pd.qcut(x, q=n, labels=False, duplicates="drop", retbins=False).values[-1], raw=False)
        )
        df[f"{x_col}_qcut"] = df[f"{x_col}_qcut"].fillna(-1)
        # 第00层表示缺失值
        df[f"{x_col}分层"] = df[f"{x_col}_qcut"].apply(lambda x: f"第{str(int(x+1)).zfill(2)}层")

    return df


def feature_cross_layering(df, x_col, **kwargs):
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
    assert "dt" in df.columns, "因子数据必须包含 dt 列"
    assert "symbol" in df.columns, "因子数据必须包含 symbol 列"
    assert x_col in df.columns, "因子数据必须包含 {} 列".format(x_col)
    assert df["symbol"].nunique() > n, "标的数量必须大于分层数量"

    if df[x_col].nunique() > n:

        def _layering(x):
            return pd.qcut(x, q=n, labels=False, duplicates="drop")

        df[f"{x_col}分层"] = df.groupby("dt")[x_col].transform(_layering)
    else:
        sorted_x = sorted(df[x_col].unique())
        df[f"{x_col}分层"] = df[x_col].apply(lambda x: sorted_x.index(x))

    df[f"{x_col}分层"] = df[f"{x_col}分层"].fillna(-1)
    # 第00层表示缺失值
    df[f"{x_col}分层"] = df[f"{x_col}分层"].apply(lambda x: f"第{str(int(x+1)).zfill(2)}层")
    return df


def find_most_similarity(vector: pd.Series, matrix: pd.DataFrame, n=10, metric="cosine", **kwargs):
    """寻找向量在矩阵中最相似的n个向量

    :param vector: 1维向量, Series结构
    :param matrix: 2维矩阵, DataFrame结构, 每一列是一个向量，列名是向量的标记
    :param n: int, 返回最相似的n个向量
    :param metric: str, 计算相似度的方法，

        - From scikit-learn: ['cityblock', 'cosine', 'euclidean', 'l1', 'l2',
        'manhattan']. These metrics support sparse matrix
        inputs.
        ['nan_euclidean'] but it does not yet support sparse matrices.

        - From scipy.spatial.distance: ['braycurtis', 'canberra', 'chebyshev',
        'correlation', 'dice', 'hamming', 'jaccard', 'kulsinski', 'mahalanobis',
        'minkowski', 'rogerstanimoto', 'russellrao', 'seuclidean',
        'sokalmichener', 'sokalsneath', 'sqeuclidean', 'yule']
        See the documentation for scipy.spatial.distance for details on these
        metrics. These metrics do not support sparse matrix inputs.

    :param kwargs: 其他参数
    """
    from sklearn.metrics.pairwise import pairwise_distances

    metric = kwargs.get("metric", "cosine")
    sim = pairwise_distances(vector.values.reshape(1, -1), matrix.T, metric=metric).reshape(-1)
    sim = pd.Series(sim, index=matrix.columns)
    sim = sim.sort_values(ascending=False)[:n]
    return sim
