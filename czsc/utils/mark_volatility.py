"""标记时序/截面波动率最大/最小的时间段（后验工具，不可用于实盘）。

2026-05-17 PR-B 起，本函数从 ``czsc/eda.py`` 拆分为独立文件，承袭原有
DataFrame 输入输出约定，行为完全不变。
"""

from __future__ import annotations

import loguru
import numpy as np
import pandas as pd


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
