"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/7 13:17
describe: 用于探索性分析的函数
"""

import loguru
import numpy as np
import pandas as pd


def monotonicity(sequence):
    """计算序列的单调性

    原理：计算序列与自然数序列的相关系数，系数越接近1，表示单调递增；系数越接近-1，表示单调递减；接近0表示无序

    :param sequence: list, tuple 序列
    :return: float, 单调性系数
    """
    from scipy.stats import spearmanr

    return spearmanr(sequence, range(len(sequence)))[0]


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
    yearly_days = dts.resample("YE").size().max()
    return min(yearly_days, 365)


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

    assert all(x in df.columns for x in weight_cols), (
        f"数据中不包含全部权重列，不包含的列：{set(weight_cols) - set(df.columns)}"
    )
    assert "weight" not in df.columns, "数据中已经包含 weight 列，请先删除，再调用该函数"

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

    :return: 带有标记的K线数据，新增列
        'is_best_period', 'is_best_up_period', 'is_best_down_period', 'is_normal_period'
        'is_worst_period', 'is_worst_up_period', 'is_worst_down_period'
    """
    from czsc import CZSC, Freq, format_standard_kline

    q1 = kwargs.get("q1", 0.15)
    q2 = kwargs.get("q2", 0.4)
    assert 0.3 >= q1 >= 0.0, "q1 必须在 0.3 和 0.0 之间"
    assert 0.5 >= q2 >= 0.0, "q2 必须在 0.5 和 0.0 之间"

    if kwargs.get("copy", True):
        df = df.copy()

    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)

    rows = []
    for symbol, dfg in df.groupby("symbol"):
        if verbose:
            logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

        dfg = dfg.sort_values("dt").copy().reset_index(drop=True)
        bars = format_standard_kline(dfg, freq=Freq.F30)
        c = CZSC(bars, max_bi_num=len(bars))

        bi_stats = []
        for bi in c.bi_list:
            bi_stats.append(
                {
                    "symbol": symbol,
                    "sdt": bi.sdt,
                    "edt": bi.edt,
                    "direction": bi.direction.value,
                    "power_price": abs(bi.change),
                    "length": bi.length,
                    "rsq": bi.rsq,
                    "power_volume": bi.power_volume,
                }
            )
        bi_stats = pd.DataFrame(bi_stats)

        bi_stats["power_price_rank"] = (
            bi_stats["power_price"].rolling(window=100, min_periods=10).rank(method="min", ascending=True, pct=True)
        )
        bi_stats["rsq_rank"] = (
            bi_stats["rsq"].rolling(window=100, min_periods=10).rank(method="min", ascending=True, pct=True)
        )
        bi_stats["power_volume_rank"] = (
            bi_stats["power_volume"].rolling(window=100, min_periods=10).rank(method="min", ascending=True, pct=True)
        )

        bi_stats["score"] = bi_stats["power_price_rank"] + bi_stats["rsq_rank"] + bi_stats["power_volume_rank"]
        bi_stats["rank"] = bi_stats["score"].rank(method="min", ascending=False, pct=True)

        best_periods = bi_stats[bi_stats["rank"] <= q1]
        worst_periods = bi_stats[bi_stats["rank"] > 1 - q2]

        if verbose:
            logger.info(f"symbol: {symbol} 共 {len(bi_stats)} 笔")
            logger.info(
                f"最容易赚钱的笔：{len(best_periods)} 个，样例：\n{best_periods.sort_values('rank', ascending=False).head(10)}"
            )
            logger.info(
                f"最难赚钱的笔：{len(worst_periods)} 个，样例：\n{worst_periods.sort_values('rank', ascending=True).head(10)}"
            )

        # 用 best_periods 的 sdt 和 edt 标记 is_best_period 为 True
        dfg["is_best_period"] = 0
        for _, row in best_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_best_period"] = 1

        best_up_periods = best_periods[best_periods["direction"] == "向上"].copy()
        best_down_periods = best_periods[best_periods["direction"] == "向下"].copy()

        dfg["is_best_up_period"] = 0
        for _, row in best_up_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_best_up_period"] = 1

        dfg["is_best_down_period"] = 0
        for _, row in best_down_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_best_down_period"] = 1

        # 用 worst_periods 的 sdt 和 edt 标记 is_worst_period 为 True`
        dfg["is_worst_period"] = 0
        for _, row in worst_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_worst_period"] = 1

        worst_up_periods = worst_periods[worst_periods["direction"] == "向上"].copy()
        worst_down_periods = worst_periods[worst_periods["direction"] == "向下"].copy()

        dfg["is_worst_up_period"] = 0
        for _, row in worst_up_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_worst_up_period"] = 1

        dfg["is_worst_down_period"] = 0
        for _, row in worst_down_periods.iterrows():
            dfg.loc[(dfg["dt"] > row["sdt"]) & (dfg["dt"] < row["edt"]), "is_worst_down_period"] = 1

        # 将剩余的K线标记为 is_normal_period 为 True
        dfg["is_normal_period"] = np.where((dfg["is_best_period"] == 0) & (dfg["is_worst_period"] == 0), 1, 0)

        rows.append(dfg)

    dfr = pd.concat(rows, ignore_index=True)
    if verbose:
        logger.info(
            f"处理完成，最易赚钱时间覆盖率：{dfr['is_best_period'].value_counts()[1] / len(dfr):.2%}, "
            f"最难赚钱时间覆盖率：{dfr['is_worst_period'].value_counts()[1] / len(dfr):.2%}"
        )

    return dfr


def mark_volatility(df: pd.DataFrame, kind="ts", **kwargs):
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
    q1 = kwargs.get("q1", 0.3)
    q2 = kwargs.get("q2", 0.3)
    assert 0.4 >= q1 >= 0.0, "q1 必须在 0.4 和 0.0 之间"
    assert 0.4 >= q2 >= 0.0, "q2 必须在 0.4 和 0.0 之间"
    assert kind in ["ts", "cs"], "kind 必须是 'ts' 或 'cs'"

    if kwargs.get("copy", True):
        df = df.copy()

    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)

    # 计算波动率
    if kind == "ts":
        # 时序波动率：每个股票单独计算时间序列上的波动率
        rows = []
        for symbol, dfg in df.groupby("symbol"):
            if verbose:
                logger.info(
                    f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}"
                )

            dfg = dfg.sort_values("dt").copy().reset_index(drop=True)
            # 计算波动率，使用未来window个周期的数据
            dfg["volatility"] = dfg["close"].pct_change().rolling(window=window).std().shift(-window)

            # 计算波动率的历史分位数，使用300个周期的滚动窗口
            dfg["volatility_rank"] = (
                dfg["volatility"].rolling(window=300, min_periods=100).rank(method="min", ascending=False, pct=True)
            )

            # 标记高波动区间：波动率排名在前q1%的区间
            dfg["is_max_volatility"] = np.where(dfg["volatility_rank"] <= q1, 1, 0)

            # 标记低波动区间：波动率排名在后q2%的区间
            dfg["is_min_volatility"] = np.where(dfg["volatility_rank"] >= (1 - q2), 1, 0)

            # 如果 is_max_volatility 和 is_min_volatility 都为 0，则标记为 is_mid_volatility
            dfg["is_mid_volatility"] = np.where((dfg["is_max_volatility"] == 0) & (dfg["is_min_volatility"] == 0), 1, 0)

            rows.append(dfg)

        dfr = pd.concat(rows, ignore_index=True)

    elif kind == "cs":
        if df["symbol"].nunique() < 2:
            raise ValueError(f"品种数量太少(仅 {df['symbol'].nunique()})，无法计算截面波动率")
        # 截面波动率：在每个时间点比较不同股票之间的波动率
        # 首先计算各个股票的波动率
        df = df.sort_values(["dt", "symbol"]).copy()
        df["volatility"] = df.groupby("symbol")["close"].pct_change().rolling(window=window).std().shift(-window)

        # 对每个时间点的不同股票进行排序
        df["volatility_rank"] = df.groupby("dt")["volatility"].rank(method="min", ascending=False, pct=True)
        df["is_max_volatility"] = np.where(df["volatility_rank"] <= q1, 1, 0)
        df["is_min_volatility"] = np.where(df["volatility_rank"] > 1 - q2, 1, 0)

        if df["is_max_volatility"].sum() == 0:
            df["is_max_volatility"] = np.where(df["volatility_rank"] == df["volatility_rank"].max(), 1, 0)

        if df["is_min_volatility"].sum() == 0:
            df["is_min_volatility"] = np.where(df["volatility_rank"] == df["volatility_rank"].min(), 1, 0)

        # 如果 is_max_volatility 和 is_min_volatility 都为 0，则标记为 is_mid_volatility
        df["is_mid_volatility"] = np.where((df["is_max_volatility"] == 0) & (df["is_min_volatility"] == 0), 1, 0)

        dfr = df

    else:
        raise ValueError(f"kind 必须是 'ts' 或 'cs'，当前值为 {kind}")

    if verbose:
        # 计算波动率最大和最小的占比
        max_volatility_pct = dfr["is_max_volatility"].sum() / len(dfr)
        mid_volatility_pct = dfr["is_mid_volatility"].sum() / len(dfr)
        min_volatility_pct = dfr["is_min_volatility"].sum() / len(dfr)
        logger.info(
            f"处理完成，波动率计算方式：{kind}，高波动覆盖率：{max_volatility_pct:.2%}, "
            f"中波动覆盖率：{mid_volatility_pct:.2%}, "
            f"低波动覆盖率：{min_volatility_pct:.2%}"
        )

    dfr.drop(columns=["volatility", "volatility_rank"], inplace=True)
    return dfr


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

    df["dt"] = pd.to_datetime(df["dt"])

    if df["weight"].dtype != "float64":
        raise TypeError("weight 列必须包含数值数据")

    if verbose:
        logger.info(
            f"正在处理 {df['symbol'].nunique()} 个品种，共 {len(df)} 条数据; "
            f"时间范围：{df['dt'].min()} - {df['dt'].max()}"
        )

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
        "日换手详情": df_daily,
    }

    return res
