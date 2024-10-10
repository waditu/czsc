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
from typing import Callable
from tqdm import tqdm
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


def min_max_limit(x, min_val, max_val, digits=4):
    """限制 x 的取值范围在 min_val 和 max_val 之间

    :param x: float, 输入值
    :param min_val: float, 最小值
    :param max_val: float, 最大值
    :param digits: int, 保留小数位数
    :return: float
    """
    return round(max(min_val, min(max_val, x)), digits)


def rolling_layers(df, factor, n=5, **kwargs):
    """对时间序列数据进行分层

    :param df: 因子数据，必须包含 dt, factor 列，其中 dt 为日期，factor 为因子值
    :param factor: 因子列名
    :param n: 分层数量，默认为10
    :param kwargs:

        - window: 窗口大小，默认为2000
        - min_periods: 最小样本数量，默认为300
        - mode: str, {'loose', 'strict'}, 分层模式，默认为 'loose'；
            loose 表示使用 rolling + rank 的方式分层，有一点点未来信息，存在一定的数据穿越问题；
            strict 表示使用 rolling + qcut 的方式分层，无未来信息，但是执行速度较慢。

    :return: df, 添加了 factor分层 列
    """
    assert df[factor].nunique() > n * 2, "因子值的取值数量必须大于分层数量"
    assert df[factor].isna().sum() == 0, "因子有缺失值，缺失数量为：{}".format(df[factor].isna().sum())
    assert df['dt'].duplicated().sum() == 0, f"dt 列不能有重复值，存在重复值数量：{df['dt'].duplicated().sum()}"

    window = kwargs.get("window", 600)
    min_periods = kwargs.get("min_periods", 300)

    # 不能有 inf 和 -inf
    if df.loc[df[factor].isin([float("inf"), float("-inf")]), factor].shape[0] > 0:
        raise ValueError(f"存在 {factor} 为 inf / -inf 的数据")

    if kwargs.get('mode', 'loose') == 'loose':
        # loose 模式，可能存在一点点未来信息
        df['pct_rank'] = df[factor].rolling(window=window, min_periods=min_periods).rank(pct=True, ascending=True)
        bins = [i/n for i in range(n+1)]
        df['pct_rank_cut'] = pd.cut(df['pct_rank'], bins=bins, labels=False)
        df['pct_rank_cut'] = df['pct_rank_cut'].fillna(-1)
        # 第00层表示缺失值
        df[f"{factor}分层"] = df['pct_rank_cut'].apply(lambda x: f"第{str(int(x+1)).zfill(2)}层")
        df.drop(['pct_rank', 'pct_rank_cut'], axis=1, inplace=True)

    else:
        assert kwargs.get('mode', 'strict') == 'strict'
        df[f"{factor}_qcut"] = (
            df[factor].rolling(window=window, min_periods=min_periods)
            .apply(lambda x: pd.qcut(x, q=n, labels=False, duplicates="drop", retbins=False).values[-1], raw=False)
        )
        df[f"{factor}_qcut"] = df[f"{factor}_qcut"].fillna(-1)
        # 第00层表示缺失值
        df[f"{factor}分层"] = df[f"{factor}_qcut"].apply(lambda x: f"第{str(int(x+1)).zfill(2)}层")
        df.drop([f"{factor}_qcut"], axis=1, inplace=True)

    return df


def cal_yearly_days(dts: list, **kwargs):
    """计算年度交易日数量

    :param dts: list, datetime 列表
    :param kwargs:
    :return: int, 年度交易日数量
    """
    logger = kwargs.get("logger", loguru.logger)

    assert len(dts) > 0, "输入的日期数量必须大于0"

    # 将日期列表转换为 DataFrame
    dts = pd.DataFrame(dts, columns=["dt"])
    dts["dt"] = pd.to_datetime(dts["dt"]).dt.date
    dts = dts.drop_duplicates()

    # 时间跨度小于一年，直接返回252，并警告
    if (dts["dt"].max() - dts["dt"].min()).days < 365:
        logger.warning("时间跨度小于一年，直接返回 252")
        return 252

    # 设置索引为日期，并确保索引为 DatetimeIndex
    dts.set_index(pd.to_datetime(dts["dt"]), inplace=True)
    dts.drop(columns=["dt"], inplace=True)

    # 按年重采样并计算每年的交易日数量，取最大值
    yearly_days = dts.resample('YE').size().max()
    return yearly_days


def cal_symbols_factor(dfk: pd.DataFrame, factor_function: Callable, **kwargs):
    """计算多个品种的标准量价因子

    :param dfk: 行情数据，N 个品种的行情数据
    :param factor_function: 因子文件，py文件
    :param kwargs:

        - logger: loguru.logger, 默认为 loguru.logger
        - factor_params: dict, 因子计算参数
        - min_klines: int, 最小K线数据量，默认为 300

    :return: dff, pd.DataFrame, 计算后的因子数据
    """
    logger = kwargs.get("logger", loguru.logger)
    min_klines = kwargs.get("min_klines", 300)
    factor_params = kwargs.get("factor_params", {})
    symbols = dfk["symbol"].unique().tolist()
    factor_name = factor_function.__name__

    rows = []
    for symbol in tqdm(symbols, desc=f"{factor_name} 因子计算"):
        try:
            df = dfk[(dfk["symbol"] == symbol)].copy()
            df = df.sort_values("dt", ascending=True).reset_index(drop=True)
            if len(df) < min_klines:
                logger.warning(f"{symbol} 数据量过小，跳过；仅有 {len(df)} 条数据，需要 {min_klines} 条数据")
                continue

            df = factor_function(df, **factor_params)
            df["price"] = df["close"]
            df["n1b"] = (df["price"].shift(-1) / df["price"] - 1).fillna(0)

            factor = [x for x in df.columns if x.startswith("F#")][0]
            df[factor] = df[factor].replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
            if df[factor].var() == 0 or np.isnan(df[factor].var()):
                logger.warning(f"{symbol} {factor} var is 0 or nan")
            else:
                rows.append(df.copy())
        except Exception as e:
            logger.error(f"{factor_name} - {symbol} - 计算因子出错：{e}")

    dff = pd.concat(rows, ignore_index=True)
    return dff


def weights_simple_ensemble(df, weight_cols, method="mean", only_long=False, **kwargs):
    """用朴素的方法集成多个策略的权重

    :param df: pd.DataFrame, 包含多个策略的权重列
    :param weight_cols: list, 权重列名称列表
    :param method: str, 集成方法，可选 mean, vote, sum_clip

        - mean: 平均值
        - vote: 投票
        - sum_clip: 求和并截断

    :param only_long: bool, 是否只做多
    :param kwargs: dict, 其他参数

        - clip_min: float, 截断最小值
        - clip_max: float, 截断最大值

    :return: pd.DataFrame, 添加了 weight 列的数据
    """
    method = method.lower()

    assert all([x in df.columns for x in weight_cols]), f"数据中不包含全部权重列，不包含的列：{set(weight_cols) - set(df.columns)}"
    assert 'weight' not in df.columns, "数据中已经包含 weight 列，请先删除，再调用该函数"

    if method == "mean":
        df["weight"] = df[weight_cols].mean(axis=1).fillna(0)

    elif method == "vote":
        df["weight"] = np.sign(df[weight_cols].sum(axis=1)).fillna(0)

    elif method == "sum_clip":
        clip_min = kwargs.get("clip_min", -1)
        clip_max = kwargs.get("clip_max", 1)
        df["weight"] = df[weight_cols].sum(axis=1).clip(clip_min, clip_max).fillna(0)

    else:
        raise ValueError("method 参数错误，可选 mean, vote, sum_clip")

    if only_long:
        df["weight"] = np.where(df["weight"] > 0, df["weight"], 0)

    return df

