# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/7 13:17
describe: 用于探索性分析的函数
"""
import loguru
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, LinearRegression, Lasso


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
    logger = kwargs.get("logger", loguru.logger)

    assert factor is not None and betas is not None, "factor 和 betas 参数必须指定"
    assert isinstance(betas, list), "betas 参数必须为列表"
    assert factor in df.columns, f"数据中不包含因子 {factor}"
    assert all([x in df.columns for x in betas]), f"数据中不包含全部 beta {betas}"

    logger.info(f"去除 beta 对因子 {factor} 的影响, 使用 {linear_model} 模型, betas: {betas}")

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


def cross_sectional_strategy(df, factor, **kwargs):
    """根据截面因子值构建多空组合

    :param df: pd.DataFrame, 包含因子列的数据, 必须包含 dt, symbol, factor 列
    :param factor: str, 因子列名称
    :param kwargs:

        - factor_direction: str, 因子方向，positive 或 negative
        - long_num: int, 多头持仓数量
        - short_num: int, 空头持仓数量
        - logger: loguru.logger, 日志记录器

    :return: pd.DataFrame, 包含 weight 列的数据
    """
    factor_direction = kwargs.get("factor_direction", "positive")
    long_num = kwargs.get("long_num", 5)
    short_num = kwargs.get("short_num", 5)
    logger = kwargs.get("logger", loguru.logger)

    assert factor in df.columns, f"{factor} 不在 df 中"
    assert factor_direction in ["positive", "negative"], f"factor_direction 参数错误"

    df = df.copy()
    if factor_direction == "negative":
        df[factor] = -df[factor]

    df['weight'] = 0
    for dt, dfg in df.groupby("dt"):
        if len(dfg) < long_num + short_num:
            logger.warning(f"{dt} 截面数据量过小，跳过；仅有 {len(dfg)} 条数据，需要 {long_num + short_num} 条数据")
            continue

        dfa = dfg.sort_values(factor, ascending=False).head(long_num)
        dfb = dfg.sort_values(factor, ascending=True).head(short_num)
        df.loc[dfa.index, "weight"] = 1 / long_num
        df.loc[dfb.index, "weight"] = -1 / short_num

    return df
