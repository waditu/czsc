# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/7 13:17
describe: 用于探索性分析的函数
"""
import pandas as pd
import numpy as np


def vwap(price: np.array, volume: np.array, **kwargs) -> float:
    """计算成交量加权平均价

    :param price: 价格序列
    :param volume: 成交量序列
    :return: 平均价
    """
    return np.average(price, weights=volume)


def twap(price: np.array, **kwargs) -> float:
    """计算时间加权平均价

    :param price: 价格序列
    :return: 平均价
    """
    return np.average(price)


def remove_beta_effects(df, **kwargs):
    """去除 beta 对因子的影响

    :param df: DataFrame, 数据, 必须包含 dt、symbol、factor 和 betas 列
    :param kwargs:

        - factor: str, 因子列名
        - betas: list, beta 列名列表
        - linear_model: str, 线性模型，可选 ridge、linear 或 lasso

    :return: DataFrame
    """
    from sklearn.linear_model import Ridge, LinearRegression, Lasso

    linear_model = kwargs.get("linear_model", "ridge")
    linear = {
        "ridge": Ridge(),
        "linear": LinearRegression(),
        "lasso": Lasso(),
    }
    assert linear_model in linear.keys(), "linear_model 参数必须为 ridge、linear 或 lasso"
    Model = linear[linear_model]

    factor = kwargs.get("factor")
    betas = kwargs.get("betas")
    assert factor is not None and betas is not None, "factor 和 betas 参数必须指定"
    assert isinstance(betas, list), "betas 参数必须为列表"
    assert factor in df.columns, f"数据中不包含因子 {factor}"
    assert all([x in df.columns for x in betas]), f"数据中不包含全部 beta {betas}"

    rows = []
    for dt, dfg in df.groupby("dt"):
        dfg = dfg.copy().dropna(subset=[factor] + betas)
        if dfg.empty:
            continue

        x = dfg[betas].values
        y = dfg[factor].values
        model = Model().fit(x, y)
        dfg[factor] = y - model.predict(x)
        rows.append(dfg)

    dfr = pd.concat(rows, ignore_index=True)
    return dfr
