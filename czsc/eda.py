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
