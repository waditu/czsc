# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/11 17:53
describe:
"""
import pandas as pd


def cross_sectional_ranker(df, x_cols, y_col, **kwargs):
    """截面打分排序

    :param df: 因子数据，必须包含日期、品种、因子值、预测列，且按日期升序排列，样例数据如下：
    :param x_cols: 因子列名
    :param y_col: 预测列名
    :param kwargs: 其他参数

        - model_params: dict, 模型参数，默认{'n_estimators': 40, 'learning_rate': 0.01}，可调整，参考lightgbm文档
        - n_splits: int, 时间拆分次数，默认5，即5段时间
        - rank_ascending: bool, 打分排序是否升序，默认False-降序
        - copy: bool, 是否拷贝df，True-拷贝，False-不拷贝

    :return: df, 包含预测分数和排序列
    """
    from lightgbm import LGBMRanker
    from sklearn.model_selection import TimeSeriesSplit

    assert "symbol" in df.columns, "df must have column 'symbol'"
    assert "dt" in df.columns, "df must have column 'dt'"

    if kwargs.get("copy", True):
        df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["dt", y_col], ascending=[True, False])

    model_params = kwargs.get("model_params", {"n_estimators": 40, "learning_rate": 0.01})
    model = LGBMRanker(**model_params)

    dfd = pd.DataFrame({"dt": sorted(df["dt"].unique())}).values
    tss = TimeSeriesSplit(n_splits=kwargs.get("n_splits", 5))

    for train_index, test_index in tss.split(dfd):
        train_dts = dfd[train_index][:, 0]
        test_dts = dfd[test_index][:, 0]

        # 拆分训练集和测试集
        train, test = df[df["dt"].isin(train_dts)], df[df["dt"].isin(test_dts)]
        X_train, X_test, y_train = train[x_cols], test[x_cols], train[y_col]
        query_train = train.groupby("dt")["symbol"].count().values

        # 训练模型 & 预测
        model.fit(X_train, y_train, group=query_train)
        df.loc[X_test.index, "score"] = model.predict(X_test)

    df["rank"] = df.groupby("dt")["score"].rank(ascending=kwargs.get("rank_ascending", False))
    return df
