# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:04
describe: 交易相关的工具函数
"""
import pandas as pd
from deprecated import deprecated
from typing import List, Union
from czsc.objects import RawBar


def risk_free_returns(start_date="20180101", end_date="20210101", year_returns=0.03):
    """创建无风险收益率序列

    创建一个 Pandas DataFrame，包含两列："date" 和 "returns"。"date" 列包含从 trade_dates 获取的所有交易日期，
    "returns" 列包含无风险收益率序列，计算方法是将年化收益率（year_returns）除以 252（一年的交易日数量，假设为每周 5 天）

    :param start_date: 起始日期
    :param end_date: 截止日期
    :param year_returns: 年化收益率
    :return: pd.DataFrame
    """
    from czsc.utils.calendar import get_trading_dates

    trade_dates = get_trading_dates(start_date, end_date)  # type: ignore
    df = pd.DataFrame({"date": trade_dates, "returns": year_returns / 252})
    return df


def update_nxb(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """在给定的 df 上计算并添加后面 n 根 bar 的累计收益列

    收益计量单位：BP；1倍涨幅 = 10000BP

    :param df: 数据，DataFrame结构，必须包含 dt, symbol, price 列
    :param kwargs: 参数字典

        - nseq: 考察的bar的数目的列表，默认为 (1, 2, 3, 5, 8, 10, 13)
        - bp: 是否将收益转换为BP，默认为 False

    :return: pd.DataFrame
    """
    if kwargs.get("copy", False):
        df = df.copy()

    assert "dt" in df.columns, "必须包含 dt 列，标记K线结束时刻"
    assert "symbol" in df.columns, "必须包含 symbol 列，标记K线所属的品种"
    assert "price" in df.columns, "必须包含 price 列，标记K线结束时刻的可交易价格"

    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)

    nseq = kwargs.get("nseq", (1, 2, 3, 5, 8, 10, 13))
    for symbol, dfg in df.groupby("symbol"):

        for n in nseq:
            dfg[f"n{n}b"] = dfg["price"].shift(-n) / dfg["price"] - 1
            df.loc[dfg.index, f"n{n}b"] = dfg[f"n{n}b"].fillna(0)

            if kwargs.get("bp", False) is True:
                df[f"n{n}b"] = df[f"n{n}b"] * 10000
    return df


def update_bbars(da, price_col="close", numbers=(1, 2, 5, 10, 20, 30)) -> None:
    """在给定的 da 数据上计算并添加前面 n 根 bar 的累计收益列

    函数的逻辑如下：

    1. 首先，检查 price_col 是否在输入的 DataFrame（da）的列名中。如果不在，抛出 ValueError。
    2. 使用 for 循环遍历 numbers 列表中的每个整数 n，对于每个整数 n，计算 n 根 bar 的累计收益。
    3. 返回 None，表示这个函数会直接修改输入的 da，而不返回新的 DataFrame。

    :param da: K线数据，DataFrame结构
    :param price_col: 价格列
    :param numbers: 考察的bar的数目的列表
    :return: bbars_cols: 后面n根bar的bp值列名
    """
    if price_col not in da.columns:
        raise ValueError(f"price_col {price_col} not in da.columns")

    for n in numbers:
        # 收益计量单位：BP；1倍涨幅 = 10000BP
        da[f"b{n}b"] = (da[price_col] / da[price_col].shift(n) - 1) * 10000


def update_tbars(da: pd.DataFrame, event_col: str) -> None:
    """计算带 Event 方向信息的未来收益

    函数的逻辑如下：

    1. 从输入的 da的列名中提取所有以 'n' 开头，以 'b' 结尾的列名，这些列名表示未来 n 根 bar 的累计收益。将这些列名存储在 n_seq 列表中。
    2. 使用 for 循环遍历 n_seq 列表中的每个整数 n。
    3. 对于每个整数 n，计算带有 Event 方向信息的未来收益。
        计算方法是：将前面 n 根 bar 的累计收益（列名 f'n{n}b'）与事件信号列（event_col）的值相乘。
        将计算结果存储在一个新的列中，列名为 f't{n}b'。
    4. 返回 None，表示这个函数会直接修改输入的 da，而不返回新的 DataFrame。

    :param da: K线数据，DataFrame结构
    :param event_col: 事件信号列名，含有 0, 1, -1 三种值，0 表示无事件，1 表示看多事件，-1 表示看空事件
    :return: None
    """
    n_seq = [int(x.strip("nb")) for x in da.columns if x[0] == "n" and x[-1] == "b"]
    for n in n_seq:
        da[f"t{n}b"] = da[f"n{n}b"] * da[event_col]


def resample_to_daily(df: pd.DataFrame, sdt=None, edt=None, only_trade_date=True):
    """将非日线数据转换为日线数据，以便进行日线级别的分析

    使用场景：

    1. 将周频选股结果转换为日线级别，以便进行日线级别的分析

    函数执行逻辑：

    1. 首先，函数接收一个数据框`df`，以及可选的开始日期`sdt`，结束日期`edt`，和一个布尔值`only_trade_date`。
    2. 函数将`df`中的`dt`列转换为日期时间格式。如果没有提供`sdt`或`edt`，则使用`df`中的最小和最大日期作为开始和结束日期。
    3. 创建一个日期序列。如果`only_trade_date`为真，则只包含交易日期；否则，包含`sdt`和`edt`之间的所有日期。
    4. 使用`merge_asof`函数，找到每个日期在原始`df`中对应的最近一个日期。
    5. 创建一个映射，将每个日期映射到原始`df`中的对应行。
    6. 对于日期序列中的每个日期，复制映射中对应的数据行，并将日期设置为当前日期。
    7. 最后，将所有复制的数据行合并成一个新的数据框，并返回。

    :param df: 日线以上周期的数据，必须包含 dt 列
    :param sdt: 开始日期
    :param edt: 结束日期
    :param only_trade_date: 是否只保留交易日数据
    :return: pd.DataFrame
    """
    from czsc.utils.calendar import get_trading_dates

    df["dt"] = pd.to_datetime(df["dt"])
    sdt = df["dt"].min() if not sdt else pd.to_datetime(sdt)
    edt = df["dt"].max() if not edt else pd.to_datetime(edt)

    # 创建日期序列
    if only_trade_date:
        trade_dates = get_trading_dates(sdt=sdt, edt=edt)
    else:
        trade_dates = pd.date_range(sdt, edt, freq="D").tolist()
    trade_dates = pd.DataFrame({"date": trade_dates})
    trade_dates = trade_dates.sort_values("date", ascending=True).reset_index(drop=True)

    # 通过 merge_asof 找到每个日期对应原始 df 中最近一个日期
    vdt = pd.DataFrame({"dt": df["dt"].unique()})
    trade_dates = pd.merge_asof(trade_dates, vdt, left_on="date", right_on="dt")
    trade_dates = trade_dates.dropna(subset=["dt"]).reset_index(drop=True)

    dt_map = {dt: dfg for dt, dfg in df.groupby("dt")}
    results = []
    for row in trade_dates.to_dict("records"):
        # 注意：这里必须进行 copy，否则默认浅拷贝导致数据异常
        df_ = dt_map[row["dt"]].copy()
        df_["dt"] = row["date"]
        results.append(df_)

    dfr = pd.concat(results, ignore_index=True)
    return dfr


def adjust_holding_weights(df, hold_periods=1, **kwargs):
    """根据 hold_periods 调整截面数据的 weight 列，固定间隔调仓

    使用场景：

    1. 截面选品种，固定持仓周期为 hold_periods，每隔 hold_periods 个周期调整一次仓位

    :param df: pd.DataFrame, 截面数据, 至少包含 dt, symbol, weight, n1b 列

        **注意：** df 中必须有原始交易中每个时刻的持仓数据，不要求时间等间隔拆分，但是 n1b 要能代表两个交易时刻之间的收益率

    :param hold_periods: int, 固定持仓周期，大于等于1；1 表示每个交易周期调整一次仓位
    :return: pd.DataFrame
    """
    assert hold_periods >= 1, "hold_periods 必须大于等于1"
    if hold_periods == 1:
        return df.copy()

    df = df.copy()

    # 每隔 hold_periods 个交易日调整一次仓位，获取调整期的时间列表 adjust_dts
    dts = sorted(df["dt"].unique().tolist())
    adjust_dts = dts[::hold_periods]

    # 在 adjust_dts 上获取每个品种的权重，并且在 dts 上进行前向填充
    dfs = pd.pivot_table(df, index="dt", columns="symbol", values="weight").fillna(0)
    dfs = dfs[dfs.index.isin(adjust_dts)]
    dfs = dfs.reindex(dts, method="ffill").fillna(0).reset_index()

    # 从原始数据中获取 n1b 列，然后将 weight 列与 n1b 列进行合并
    dfw1 = pd.melt(dfs, id_vars="dt", value_vars=dfs.columns.to_list(), var_name="symbol", value_name="weight")
    dfw1 = pd.merge(df[["dt", "symbol", "n1b"]], dfw1, on=["dt", "symbol"], how="left")
    return dfw1
