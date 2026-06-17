"""标记 CTA 最容易/最难赚钱的时间段（后验工具，不可用于实盘）。

2026-05-17 PR-B 起，本函数从 ``czsc/eda.py`` 拆分为独立文件，承袭原有
DataFrame 输入输出约定，行为完全不变。

为什么放在 ``czsc/utils/`` 而非 ``czsc/eda.py``：

- 与 ``mark_volatility`` 一起属于"对 K 线序列做后验区间标注"的工具函数，
  在职责上更贴近 ``czsc.utils`` 而非"探索性数据分析"；
- 拆分成独立文件后，调用方按需 import，不再被 ``czsc.eda`` 顶层
  ``loguru / numpy / pandas`` 的 module-level import 牵连。
"""

from __future__ import annotations

import loguru
import numpy as np
import pandas as pd


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
    # CZSC / Freq / format_standard_kline 留在函数体内 import，避免与 czsc 顶层
    # __init__ 形成 partially-initialized 循环 import。
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
