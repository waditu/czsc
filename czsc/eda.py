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
        - linear_model_params: dict, 线性模型参数, 默认为空, 需要传入字典，根据模型不同参数不同

    :return: DataFrame
    """

    linear_model = kwargs.get("linear_model", "ridge")
    linear_model_params = kwargs.get("linear_model_params", {})
    linear = {
        "ridge": Ridge,
        "linear": LinearRegression,
        "lasso": Lasso,
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
        model = Model(**linear_model_params).fit(x, y)
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
        if long_num > 0:
            df.loc[dfa.index, "weight"] = 1 / long_num
        if short_num > 0:
            df.loc[dfb.index, "weight"] = -1 / short_num

    return df


def judge_factor_direction(df: pd.DataFrame, factor, target='n1b', by='symbol', **kwargs):
    """判断因子的方向，正向还是反向

    :param df: pd.DataFrame, 数据源，必须包含 symbol, dt, target, factor 列
    :param factor: str, 因子名称
    :param target: str, 目标名称，默认为 n1b，表示下一根K线的涨跌幅
    :param by: str, 分组字段，默认为 symbol，表示按品种分组（时序）；也可以按 dt 分组，表示按时间分组（截面）
    :param kwargs: dict, 其他参数
        - method: str, 相关系数计算方法，默认为 pearson，可选 pearson, kendall, spearman
    :return: str, positive or negative
    """
    assert by in df.columns, f"数据中不存在 {by} 字段"
    assert factor in df.columns, f"数据中不存在 {factor} 字段"
    assert target in df.columns, f"数据中不存在 {target} 字段"

    if by == "dt" and df['symbol'].nunique() < 2:
        raise ValueError("品种数量过少，无法在时间截面上计算因子有效性方向")

    if by == "symbol" and df['dt'].nunique() < 2:
        raise ValueError("时间序列数据量过少，无法在品种上计算因子有效性方向")

    method = kwargs.get("method", "pearson")
    dfc = df.groupby(by)[[factor, target]].corr(method=method).unstack().iloc[:, 1].reset_index()
    return "positive" if dfc[factor].mean().iloc[0] >= 0 else "negative"


def monotonicity(sequence):
    """计算序列的单调性

    原理：计算序列与自然数序列的相关系数，系数越接近1，表示单调递增；系数越接近-1，表示单调递减；接近0表示无序

    :param sequence: list, tuple 序列
    :return: float, 单调性系数
    """
    from scipy.stats import spearmanr
    return spearmanr(sequence, range(len(sequence)))[0]
