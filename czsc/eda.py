# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/7 13:17
describe: 用于探索性分析的函数
"""
import time
import loguru
import pandas as pd
import numpy as np
from typing import Callable
from tqdm import tqdm


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
    from sklearn.linear_model import Ridge, LinearRegression, Lasso

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


def cross_sectional_strategy(df, factor, weight="weight", long=0.3, short=0.3, **kwargs):
    """根据截面因子值构建多空组合

    :param df: pd.DataFrame, 包含多个品种的因子数据, 必须包含 dt, symbol, factor 列
    :param factor: str, 因子列名称
    :param weight: str, 权重列名称，默认为 weight
    :param long: float, 多头持仓比例/数量，默认为 0.3, 取值范围为 [0, n_symbols], 0~1 表示比例，大于等于1表示数量
    :param short: float, 空头持仓比例/数量，默认为 0.3, 取值范围为 [0, n_symbols], 0~1 表示比例，大于等于1表示数量
    :param kwargs:

        - factor_direction: str, 因子方向，positive 或 negative
        - logger: loguru.logger, 日志记录器
        - norm: bool, 是否对 weight 进行截面持仓标准化，默认为 True

    :return: pd.DataFrame, 包含 weight 列的数据
    """
    factor_direction = kwargs.get("factor_direction", "positive")
    logger = kwargs.get("logger", loguru.logger)
    norm = kwargs.get("norm", True)

    assert long >= 0 and short >= 0, "long 和 short 参数必须大于等于0"
    assert factor in df.columns, f"{factor} 不在 df 中"
    assert factor_direction in ["positive", "negative"], f"factor_direction 参数错误"

    df = df.copy()
    if factor_direction == "negative":
        df[factor] = -df[factor]

    df[weight] = 0.0
    rows = []

    for dt, dfg in df.groupby("dt"):
        long_num = int(long) if long >= 1 else int(len(dfg) * long)
        short_num = int(short) if short >= 1 else int(len(dfg) * short)

        if long_num == 0 and short_num == 0:
            logger.warning(f"{dt} 多空目前持仓数量都为0; long: {long}, short: {short}")
            rows.append(dfg)
            continue

        long_symbols = dfg.sort_values(factor, ascending=False).head(long_num)['symbol'].tolist()
        short_symbols = dfg.sort_values(factor, ascending=True).head(short_num)['symbol'].tolist()

        union_symbols = set(long_symbols) & set(short_symbols)
        if union_symbols:
            logger.warning(f"{dt} 存在同时在多头和空头的品种：{union_symbols}")
            long_symbols = list(set(long_symbols) - union_symbols)
            short_symbols = list(set(short_symbols) - union_symbols)

        dfg.loc[dfg['symbol'].isin(long_symbols), weight] = 1 / long_num if norm else 1.0
        dfg.loc[dfg['symbol'].isin(short_symbols), weight] = -1 / short_num if norm else -1.0
        rows.append(dfg)

    dfx = pd.concat(rows, ignore_index=True)
    return dfx


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
    return min(yearly_days, 365)


def cal_symbols_factor(dfk: pd.DataFrame, factor_function: Callable, **kwargs):
    """计算多个品种的标准量价因子

    :param dfk: 行情数据，N 个品种的行情数据
    :param factor_function: 因子文件，py文件
    :param kwargs:

        - logger: loguru.logger, 默认为 loguru.logger
        - factor_params: dict, 因子计算参数
        - min_klines: int, 最小K线数据量，默认为 300
        - price_type: str, 交易价格类型，默认为 close，可选值为 close 或 next_open
        - strict: bool, 是否严格模式，默认为 True, 严格模式下，计算因子出错会抛出异常

    :return: dff, pd.DataFrame, 计算后的因子数据
    """
    logger = kwargs.get("logger", loguru.logger)
    min_klines = kwargs.get("min_klines", 300)
    factor_params = kwargs.get("factor_params", {})
    price_type = kwargs.get("price_type", "close")
    strict = kwargs.get("strict", True)
    max_seconds = kwargs.get("max_seconds", 800)

    start_time = time.time()

    symbols = dfk["symbol"].unique().tolist()
    factor_name = factor_function.__name__

    def __one_symbol(symbol):
        df = dfk[(dfk["symbol"] == symbol)].copy()
        df = df.sort_values("dt", ascending=True).reset_index(drop=True)
        if len(df) < min_klines:
            logger.warning(f"{symbol} 数据量过小，跳过；仅有 {len(df)} 条数据，需要 {min_klines} 条数据")
            return None

        df = factor_function(df, **factor_params)
        if price_type == 'next_open':
            df["price"] = df["open"].shift(-1).fillna(df["close"])
        elif price_type == 'close':
            df["price"] = df["close"]
        else:
            raise ValueError("price_type 参数错误, 可选值为 close 或 next_open")

        df["n1b"] = (df["price"].shift(-1) / df["price"] - 1).fillna(0)
        factor = [x for x in df.columns if x.startswith("F#")][0]

        # df[factor] = df[factor].replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
        # factor 中不能有 inf 和 -inf 值，也不能有 nan 值
        assert df[factor].isna().sum() == 0, f"{symbol} {factor} 存在 nan 值"
        assert df[factor].isin([np.inf, -np.inf]).sum() == 0, f"{symbol} {factor} 存在 inf 值"
        assert df[factor].var() != 0 and not np.isnan(df[factor].var()), f"{symbol} {factor} var is 0 or nan"
        return df

    rows = []
    for _symbol in tqdm(symbols, desc=f"{factor_name} 因子计算"):
        if strict:
            dfx = __one_symbol(_symbol)
        else:
            try:
                dfx = __one_symbol(_symbol)
            except Exception as e:
                logger.error(f"{factor_name} - {_symbol} - 计算因子出错：{e}")
                continue
        rows.append(dfx)
        if time.time() - start_time > max_seconds:
            logger.warning(f"{factor_name} - {_symbol} - 计算因子超时，返回空值")
            return pd.DataFrame()

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


def unify_weights(dfw: pd.DataFrame, **kwargs):
    """按策略统一权重进行大盘择时交易

    在任意时刻 dt，将所有品种的权重通过某种算法合并，然后所有品种都按照这个权重进行操作

    :param dfw: pd.DataFrame，columns=['symbol', 'weight', 'dt', 'price']，数据样例如下

        ========  ===================  ========  =======
        symbol    dt                     weight    price
        ========  ===================  ========  =======
        IC9001    2017-01-03 00:00:00     -0.82  11113.8
        IC9001    2017-01-04 00:00:00     -0.83  11275.3
        IC9001    2017-01-05 00:00:00     -0.84  11261.1
        ========  ===================  ========  =======

    :param kwargs: dict，其他参数

        - method: str，权重合并方法，支持 'mean' 和 'sum_clip'，默认 'sum_clip'
        - copy: bool，是否复制输入数据，默认 True
        - clip_min: float，权重合并方法为 'sum_clip' 时，clip 的最小值，默认 -1
        - clip_max: float，权重合并方法为 'sum_clip' 时，clip 的最大值，默认 1

    :return: pd.DataFrame，columns=['symbol', 'weight', 'dt', 'price']

    example:
    ================
        dfw = ...
        wb = czsc.WeightBacktest(dfw, fee_rate=0.0002)
        print(wb.stats)

        dfw1 = unify_weights(dfw.copy(), method='mean')
        wb1 = czsc.WeightBacktest(dfw1, fee_rate=0.0002)
        print(wb1.stats)

        dfw2 = unify_weights(dfw.copy(), method='sum_clip')
        wb2 = czsc.WeightBacktest(dfw2, fee_rate=0.0002)
        print(wb2.stats)

        # 合并 daily_return，看看是否一致
        dfd1 = wb.daily_return.copy()
        dfd2 = wb1.daily_return.copy()
        dfd3 = wb2.daily_return.copy()

        dfd = pd.merge(dfd1, dfd2, on='date', how='left', suffixes=('', '_mean'))
        dfd = pd.merge(dfd, dfd3, on='date', how='left', suffixes=('', '_sum_clip'))
        print(dfd[['total', 'total_mean', 'total_sum_clip']].corr())
    ================
    """
    method = kwargs.get('method', 'sum_clip')
    if kwargs.get("copy", True):
        dfw = dfw.copy()

    if method == 'mean':
        uw = dfw.groupby('dt')['weight'].mean().reset_index()

    elif method == 'sum_clip':
        clip_min = kwargs.get('clip_min', -1)
        clip_max = kwargs.get('clip_max', 1)
        assert clip_min < clip_max, "clip_min should be less than clip_max"

        uw = dfw.groupby('dt')['weight'].sum().reset_index()
        uw['weight'] = uw['weight'].clip(clip_min, clip_max)

    else:
        raise ValueError(f"method {method} not supported")

    dfw = pd.merge(dfw, uw, on='dt', how='left', suffixes=('_raw', '_unified'))
    dfw['weight'] = dfw['weight_unified'].copy()
    return dfw


def sma_long_bear(df: pd.DataFrame, **kwargs):
    """均线牛熊分界指标过滤持仓，close 在长期均线上方为牛市，下方为熊市

    牛市只做多，熊市只做空。

    :param df: DataFrame, 必须包含 dt, close, symbol, weight 列
    :return: DataFrame
    """
    assert df["symbol"].nunique() == 1, "数据中包含多个品种，必须单品种"
    assert df["dt"].is_monotonic_increasing, "数据未按日期排序，必须升序排列"
    assert df["dt"].is_unique, "数据中存在重复dt，必须唯一"

    window = kwargs.get("window", 200)

    if kwargs.get("copy", True):
        df = df.copy()

    df['SMA_LB'] = df['close'].rolling(window).mean()
    df['raw_weight'] = df['weight']
    df['weight'] = np.where(np.sign(df['close'] - df['SMA_LB']) == np.sign(df['weight']), df['weight'], 0)
    return df


def dif_long_bear(df: pd.DataFrame, **kwargs):
    """DIF牛熊分界指标过滤持仓，DIF 在0上方为牛市，下方为熊市

    牛市只做多，熊市只做空。

    :param df: DataFrame, 必须包含 dt, close, symbol, weight 列
    :return: DataFrame
    """
    from czsc.utils.ta import MACD

    assert df["symbol"].nunique() == 1, "数据中包含多个品种，必须单品种"
    assert df["dt"].is_monotonic_increasing, "数据未按日期排序，必须升序排列"
    assert df["dt"].is_unique, "数据中存在重复dt，必须唯一"

    if kwargs.get("copy", True):
        df = df.copy()

    df['DIF_LB'], _, _ = MACD(df['close'])
    df['raw_weight'] = df['weight']
    df['weight'] = np.where(np.sign(df['DIF_LB']) == np.sign(df['weight']), df['weight'], 0)
    return df


def tsf_type(df: pd.DataFrame, factor, n=5, **kwargs):
    """时序因子的类型定性分析

    tsf 是 time series factor 的缩写，时序因子的类型定性分析，是指对某个时序因子进行分层，然后计算每个分层的平均收益，

    :param df: pd.DataFrame, 必须包含 dt, symbol, factor 列，其中 dt 为日期，symbol 为标的代码，factor 为因子值
    :param factor: str, 因子列名
    :param n: int, 分层数量
    :param kwargs:

        - window: int, 窗口大小，默认为600
        - min_periods: int, 最小样本数量，默认为300
        - target: str, 目标列名，默认为 n1b

    :return: str, 返回分层收益排序（从大到小）结果，例如：第01层->第02层->第03层->第04层->第05层
    """
    logger = kwargs.get("logger", loguru.logger)
    window = kwargs.get("window", 600)
    min_periods = kwargs.get("min_periods", 300)
    target = kwargs.get("target", "n1b")

    if target == 'n1b' and 'n1b' not in df.columns:
        from czsc.utils.trade import update_nxb
        df = update_nxb(df, nseq=(1,))

    assert target in df.columns, f"数据中不存在 {target} 列"
    assert factor in df.columns, f"数据中不存在 {factor} 列"

    rows = []
    for symbol, dfg in df.groupby("symbol"):
        try:
            dfg = dfg.copy().reset_index(drop=True)
            dfg = rolling_layers(dfg, factor, n=n, window=window, min_periods=min_periods)
            rows.append(dfg)
        except Exception as e:
            logger.warning(f"{symbol} 计算分层失败: {e}")

    df = pd.concat(rows, ignore_index=True)
    layers = [x for x in df[f"{factor}分层"].unique() if x != "第00层" and str(x).endswith("层")]

    # 计算每个分层的平均收益
    layer_returns = {}
    for layer in layers:
        dfg = df[df[f"{factor}分层"] == layer].copy()
        dfg = dfg.groupby("dt")[target].mean().reset_index()
        layer_returns[layer] = dfg[target].sum()

    sorted_layers = sorted(layer_returns.items(), key=lambda x: x[1], reverse=True)
    return "->".join([f"{x[0]}" for x in sorted_layers])


def limit_leverage(df: pd.DataFrame, leverage: float = 1.0, **kwargs):
    """限制杠杆比例

    原理描述：

    1. 计算滚动窗口内权重的绝对均值 abs_mean，初始窗口内权重的绝对均值设为 leverage
    2. 用 leverage 除以 abs_mean，得到调整比例 adjust_ratio
    3. 将原始权重乘以 adjust_ratio，再限制在 -leverage 和 leverage 之间

    :param df: DataFrame, columns=['dt', 'symbol', 'weight']
    :param leverage: float, 杠杆倍数
    :param kwargs:

        - copy: bool, 是否复制 DataFrame
        - window: int, 滚动窗口，默认为 300
        - min_periods: int, 最小样本数，小于该值的窗口不计算均值，默认为 50
        - weight: str, 权重列名，默认为 'weight'
        - method: str, 计算均值的方法，'abs_mean' 或 'abs_max'，默认为 'abs_mean'
            abs_mean: 计算绝对均值作为调整杠杆的标准
            abs_max: 计算绝对最大值作为调整杠杆的标准

    :return: DataFrame
    """
    window = kwargs.get("window", 300)
    min_periods = kwargs.get("min_periods", 50)
    weight = kwargs.get("weight", "weight")
    method = kwargs.get("method", "abs_mean")

    assert weight in df.columns, f"数据中不包含权重列 {weight}"

    if kwargs.get("copy", False):
        df = df.copy()

    df = df.sort_values(["dt", "symbol"], ascending=True).reset_index(drop=True)

    for symbol in df['symbol'].unique():
        dfx = df[df['symbol'] == symbol].copy()
        # assert dfx['dt'].is_monotonic_increasing, f"{symbol} 数据未按日期排序，必须升序排列"
        assert dfx['dt'].is_unique, f"{symbol} 数据中存在重复dt，必须唯一"

        if method == "abs_mean":
            bench = dfx[weight].abs().rolling(window=window, min_periods=min_periods).mean().fillna(leverage)
        elif method == "abs_max":
            bench = dfx[weight].abs().rolling(window=window, min_periods=min_periods).max().fillna(leverage)
        else:
            raise ValueError(f"不支持的 method: {method}")

        adjust_ratio = leverage / bench
        df.loc[df['symbol'] == symbol, weight] = (dfx[weight] * adjust_ratio).clip(-leverage, leverage)

    return df


def cal_trade_price(df: pd.DataFrame, digits=None, **kwargs):
    """计算给定品种基础周期K线数据的交易价格表

    :param df: 基础周期K线数据，一般是1分钟周期的K线，支持多个品种
    :param digits: 保留小数位数，默认值为None，用每个品种的 close 列的小数位数
    :param kwargs:

        - windows: 计算TWAP和VWAP的窗口列表，默认值为(5, 10, 15, 20, 30, 60)
        - copy: 是否复制数据，默认值为True

    :return: 交易价格表，包含多个品种的交易价格
    """
    assert "symbol" in df.columns, "数据中必须包含 symbol 列"
    for col in ["dt", "open", "close", "vol"]:
        assert col in df.columns, f"数据中必须包含 {col} 列"

    if kwargs.get("copy", True):
        df = df.copy()

    # 获取所有唯一的品种
    symbols = df["symbol"].unique().tolist()
    
    # 为每个品种分别计算交易价格
    dfs = []
    for symbol in symbols:
        df_symbol = df[df["symbol"] == symbol].copy()
        df_symbol = df_symbol.sort_values("dt").reset_index(drop=True)
        
        # 如果没有指定digits，则使用该品种的close列的小数位数
        symbol_digits = digits
        if symbol_digits is None:
            symbol_digits = df_symbol["close"].astype(str).str.split(".").str[1].str.len().max()

        # 下根K线开盘、收盘
        df_symbol["TP_CLOSE"] = df_symbol["close"]
        df_symbol["TP_NEXT_OPEN"] = df_symbol["open"].shift(-1)
        df_symbol["TP_NEXT_CLOSE"] = df_symbol["close"].shift(-1)
        price_cols = ["TP_CLOSE", "TP_NEXT_OPEN", "TP_NEXT_CLOSE"]

        # TWAP / VWAP 价格
        df_symbol["vol_close_prod"] = df_symbol["vol"] * df_symbol["close"]
        for t in kwargs.get("windows", (5, 10, 15, 20, 30, 60)):
            
            df_symbol[f"TP_TWAP{t}"] = df_symbol["close"].rolling(t).mean().shift(-t)

            df_symbol[f"sum_vol_{t}"] = df_symbol["vol"].rolling(t).sum()
            df_symbol[f"sum_vcp_{t}"] = df_symbol["vol_close_prod"].rolling(t).sum()
            df_symbol[f"TP_VWAP{t}"] = (df_symbol[f"sum_vcp_{t}"] / df_symbol[f"sum_vol_{t}"]).shift(-t)
            
            price_cols.extend([f"TP_TWAP{t}", f"TP_VWAP{t}"])
            df_symbol.drop(columns=[f"sum_vol_{t}", f"sum_vcp_{t}"], inplace=True)

        df_symbol.drop(columns=["vol_close_prod"], inplace=True)

        # 用当前K线的收盘价填充交易价中的 nan 值
        for price_col in price_cols:
            df_symbol[price_col] = df_symbol[price_col].fillna(df_symbol["close"])

        df_symbol[price_cols] = df_symbol[price_cols].round(symbol_digits)
        dfs.append(df_symbol)

    # 合并所有品种的交易价格数据
    dfk = pd.concat(dfs, ignore_index=True)
    return dfk


def mark_cta_periods(df: pd.DataFrame, **kwargs):
    """【后验，有未来信息，不能用于实盘】标记CTA最容易/最难赚钱的N个时间段

    最容易赚钱：笔走势的绝对收益、R平方、波动率排序，取这三个指标的均值，保留 top n 个均值最大的笔，在标准K线上新增一列，标记这些笔的起止时间
    最难赚钱：笔走势的绝对收益、R平方、波动率排序，取这三个指标的均值，保留 bottom n 个均值最小的笔，在标准K线上新增一列，标记这些笔的起止时间

    :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
    :param kwargs: 

        - copy: 是否复制数据
        - verbose: 是否打印日志
        - logger: 日志记录器
        - q1: 最容易赚钱的笔的占比
        - q2: 最难赚钱的笔的占比

    :return: 带有标记的K线数据，新增列 'is_best_period', 'is_worst_period'
    """
    from czsc.analyze import CZSC
    from czsc.utils.bar_generator import format_standard_kline

    q1 = kwargs.get("q1", 0.15)
    q2 = kwargs.get("q2", 0.4)
    assert 0.3 >= q1 >= 0.0, "q1 必须在 0.3 和 0.0 之间"
    assert 0.5 >= q2 >= 0.0, "q2 必须在 0.5 和 0.0 之间"

    if kwargs.get("copy", True):
        df = df.copy()
    
    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)

    rows = []
    for symbol, dfg in df.groupby('symbol'):
        if verbose:
            logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

        dfg = dfg.sort_values('dt').copy().reset_index(drop=True)
        bars = format_standard_kline(dfg, freq='30分钟')
        c = CZSC(bars, max_bi_num=len(bars))

        bi_stats = []
        for bi in c.bi_list:
            bi_stats.append({
                'symbol': symbol,
                'sdt': bi.sdt,
                'edt': bi.edt,
                'direction': bi.direction.value,
                'power_price': abs(bi.change),
                'length': bi.length,
                'rsq': bi.rsq,
                'power_volume': bi.power_volume,
            })
        bi_stats = pd.DataFrame(bi_stats)
        bi_stats['power_price_rank'] = bi_stats['power_price'].rank(method='min', ascending=True, pct=True)
        bi_stats['rsq_rank'] = bi_stats['rsq'].rank(method='min', ascending=True, pct=True)
        bi_stats['power_volume_rank'] = bi_stats['power_volume'].rank(method='min', ascending=True, pct=True)
        bi_stats['score'] = bi_stats['power_price_rank'] + bi_stats['rsq_rank'] + bi_stats['power_volume_rank']
        bi_stats['rank'] = bi_stats['score'].rank(method='min', ascending=False, pct=True)

        best_periods = bi_stats[bi_stats['rank'] <= q1]
        worst_periods = bi_stats[bi_stats['rank'] > 1 - q2]

        if verbose:
            logger.info(f"最容易赚钱的笔：{len(best_periods)} 个，详情：\n{best_periods.sort_values('rank', ascending=False)}")
            logger.info(f"最难赚钱的笔：{len(worst_periods)} 个，详情：\n{worst_periods.sort_values('rank', ascending=True)}")

        # 用 best_periods 的 sdt 和 edt 标记 is_best_period 为 True
        dfg['is_best_period'] = 0
        for _, row in best_periods.iterrows():
            dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_best_period'] = 1

        # 用 worst_periods 的 sdt 和 edt 标记 is_worst_period 为 True`
        dfg['is_worst_period'] = 0
        for _, row in worst_periods.iterrows():
            dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_worst_period'] = 1

        rows.append(dfg)

    dfr = pd.concat(rows, ignore_index=True)
    if verbose:
        logger.info(f"处理完成，最易赚钱时间覆盖率：{dfr['is_best_period'].value_counts()[1] / len(dfr):.2%}, "
                    f"最难赚钱时间覆盖率：{dfr['is_worst_period'].value_counts()[1] / len(dfr):.2%}")

    return dfr


def mark_volatility(df: pd.DataFrame, kind='ts', **kwargs):
    """【后验，有未来信息，不能用于实盘】标记时序/截面波动率最大/最小的N个时间段

    :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
    :param kind: 波动率类型，'ts' 表示时序波动率，'cs' 表示截面波动率
    :param kwargs: 

        - copy: 是否复制数据
        - verbose: 是否打印日志
        - logger: 日志记录器
        - window: 计算波动率的窗口
        - q1: 波动率最大的K线数量占比
        - q2: 波动率最小的K线数量占比

    :return: 带有标记的K线数据，新增列 'is_max_volatility', 'is_min_volatility'
    """
    window = kwargs.get("window", 20)
    q1 = kwargs.get("q1", 0.2)
    q2 = kwargs.get("q2", 0.2)
    assert 0.4 >= q1 >= 0.0, "q1 必须在 0.4 和 0.0 之间"
    assert 0.4 >= q2 >= 0.0, "q2 必须在 0.4 和 0.0 之间"
    assert kind in ['ts', 'cs'], "kind 必须是 'ts' 或 'cs'"

    if kwargs.get("copy", True):
        df = df.copy()
    
    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)
    
    # 计算波动率
    if kind == 'ts':
        # 时序波动率：每个股票单独计算时间序列上的波动率
        rows = []
        for symbol, dfg in df.groupby('symbol'):
            if verbose:
                logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

            dfg = dfg.sort_values('dt').copy().reset_index(drop=True)
            dfg['volatility'] = dfg['close'].pct_change().rolling(window=window).std().shift(-window)
            dfg['volatility_rank'] = dfg['volatility'].rank(method='min', ascending=False, pct=True)
            dfg['is_max_volatility'] = np.where(dfg['volatility_rank'] <= q1, 1, 0)
            dfg['is_min_volatility'] = np.where(dfg['volatility_rank'] > 1 - q2, 1, 0)
            rows.append(dfg)

        dfr = pd.concat(rows, ignore_index=True)
    
    elif kind == 'cs':
        if df['symbol'].nunique() < 2:
            raise ValueError(f"品种数量太少(仅 {df['symbol'].nunique()})，无法计算截面波动率")
        # 截面波动率：在每个时间点比较不同股票之间的波动率
        # 首先计算各个股票的波动率
        df = df.sort_values(['dt', 'symbol']).copy()
        df['volatility'] = df.groupby('symbol')['close'].pct_change().rolling(window=window).std().shift(-window)
        
        # 对每个时间点的不同股票进行排序
        df['volatility_rank'] = df.groupby('dt')['volatility'].rank(method='min', ascending=False, pct=True)
        df['is_max_volatility'] = np.where(df['volatility_rank'] <= q1, 1, 0)
        df['is_min_volatility'] = np.where(df['volatility_rank'] > 1 - q2, 1, 0)

        if df['is_max_volatility'].sum() == 0:
            df['is_max_volatility'] = np.where(df['volatility_rank'] == df['volatility_rank'].max(), 1, 0)

        if df['is_min_volatility'].sum() == 0:
            df['is_min_volatility'] = np.where(df['volatility_rank'] == df['volatility_rank'].min(), 1, 0)

        dfr = df

    else:
        raise ValueError(f"kind 必须是 'ts' 或 'cs'，当前值为 {kind}")

    if verbose:
        # 计算波动率最大和最小的占比
        max_volatility_pct = dfr['is_max_volatility'].sum() / len(dfr)
        min_volatility_pct = dfr['is_min_volatility'].sum() / len(dfr)
        logger.info(f"处理完成，波动率计算方式：{kind}，波动率最大时间覆盖率：{max_volatility_pct:.2%}, "
                   f"波动率最小时间覆盖率：{min_volatility_pct:.2%}")
    
    dfr.drop(columns=['volatility', 'volatility_rank'], inplace=True)
    return dfr


def make_price_features(df, price='price', **kwargs):
    """计算某个K线过去(before)/未来(future)的价格走势特征
    
    :param df: 数据框, 包含 dt, symbol, price 列
    :param price: 价格列名, 默认'price'
    :param windows: 窗口列表, 默认(1, 2, 3, 5, 8, 13, 21, 34)
    :return: 数据框, 包含事件发生时间、事件名称、价格、价格走势特征
    """
    df = df.sort_values('dt').reset_index(drop=True)
    windows = kwargs.get('windows', (1, 2, 3, 5, 8, 13, 21, 34))

    rows = []
    for _, dfg in df.groupby('symbol'):
        dfg = dfg.sort_values('dt').reset_index(drop=True)
        for n in windows:
            dfg[f'price_change_{n}'] = (dfg[price].pct_change(n) * 10000).round(2)        # 收益单位：BP
            if n > 5:
                dfg[f'volatility_{n}'] = dfg[price].rolling(n).std() / dfg[price]

            n_str = str(n).zfill(2)
            # 过去 N 根K线的特征（Before）
            dfg[f"B{n_str}收益"] = dfg[f"price_change_{n}"]

            # 未来 N 根K线的特征（Future）
            dfg[f"F{n_str}收益"] = dfg[f"price_change_{n}"].shift(-n)

            if n > 5:
                dfg[f"B{n_str}波动"] = dfg[f"volatility_{n}"]
                dfg[f"F{n_str}波动"] = dfg[f"volatility_{n}"].shift(-n)
                dfg.drop(columns=[f"volatility_{n}"], inplace=True)

            dfg.drop(columns=[f"price_change_{n}"], inplace=True)

        rows.append(dfg)

    dfx = pd.concat(rows, ignore_index=True)
    return dfx


def turnover_rate(df: pd.DataFrame, **kwargs):
    """计算持仓变化的单边换手率

    :param df: 标准持仓数据，必须包含 dt, symbol, weight 列
    :param kwargs:

        - copy: 是否复制数据
        - verbose: 是否打印日志
        - logger: 日志记录器

    :return: 单边换手率
    """
    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)

    if kwargs.get("copy", True):
        df = df.copy()

    df['dt'] = pd.to_datetime(df['dt'])

    if df['weight'].dtype != 'float64':
        raise TypeError("weight 列必须包含数值数据")

    if verbose:
        logger.info(f"正在处理 {df['symbol'].nunique()} 个品种，共 {len(df)} 条数据; "
                    f"时间范围：{df['dt'].min()} - {df['dt'].max()}")

    dft = pd.pivot_table(df, index="dt", columns="symbol", values="weight", aggfunc="sum")
    dft = dft.fillna(0)
    df_turns = dft.diff().abs().sum(axis=1).reset_index()
    df_turns.columns = ["dt", "change"]

    # 由于是 diff 计算，第一个时刻的仓位变化被忽视了，修改一下
    sdt = df["dt"].min()
    df_turns.loc[(df_turns["dt"] == sdt), "change"] = df[df["dt"] == sdt]["weight"].abs().sum()

    # 按日期 resample
    df_daily = df_turns.set_index("dt").resample("D").sum().reset_index()

    if verbose:
        logger.info(f"组合换手率：{round(df_turns.change.sum() / 2, 4)}")

    res = {
        "单边换手率": round(df_daily.change.sum(), 4),
        "日均换手率": df_daily.change.mean(),
        "最大单日换手率": df_daily.change.max(),
        "最小单日换手率": df_daily.change.min(),
        "日换手详情": df_daily
    }

    return res