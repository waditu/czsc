"""
回测相关的可视化组件

包含权重分布、权重回测、持仓回测、止损分析等回测功能
"""

import numpy as np
import pandas as pd
import streamlit as st
from .base import safe_import_weight_backtest, safe_import_daily_performance


def show_weight_distribution(dfw, abs_weight=True, **kwargs):
    """展示权重分布

    :param dfw: pd.DataFrame, 包含 symbol, dt, price, weight 列
    :param abs_weight: bool, 是否取权重的绝对值
    :param kwargs:
        - percentiles: list, 分位数
    """
    dfw = dfw.copy()
    if abs_weight:
        dfw["weight"] = dfw["weight"].abs()

    default_percentiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    percentiles = kwargs.get("percentiles", default_percentiles)

    dfs = dfw.groupby("symbol").apply(lambda x: x["weight"].describe(percentiles=percentiles)).reset_index()
    
    # 使用 show_df_describe 来显示结果
    from .statistics import show_df_describe
    show_df_describe(dfs)


def show_weight_backtest(dfw, **kwargs):
    """展示权重回测结果

    :param dfw: 回测数据，任何字段都不允许有空值；数据样例：
        ===================  ========  ========  =======
        dt                   symbol      weight    price
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs:
        - fee: 单边手续费，单位为BP，默认为2BP
        - digits: 权重小数位数，默认为2
        - show_drawdowns: bool，是否展示最大回撤，默认为 False
        - show_daily_detail: bool，是否展示每日收益详情，默认为 False
        - show_backtest_detail: bool，是否展示回测详情，默认为 False
        - show_splited_daily: bool，是否展示分段日收益表现，默认为 False
        - show_yearly_stats: bool，是否展示年度绩效指标，默认为 False
        - show_monthly_return: bool，是否展示月度累计收益，默认为 False
        - n_jobs: int, 并行计算的进程数，默认为 1
    """
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        return

    from czsc.eda import cal_yearly_days

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    n_jobs = kwargs.pop("n_jobs", 1)
    yearly_days = kwargs.pop("yearly_days", None)
    weight_type = kwargs.pop("weight_type", "ts")

    if not yearly_days:
        yearly_days = cal_yearly_days(dts=dfw["dt"].unique())

    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    wb = WeightBacktest(
        dfw=dfw, fee_rate=fee / 10000, digits=digits, n_jobs=n_jobs, 
        yearly_days=yearly_days, weight_type=weight_type
    )
    stat = wb.stats

    st.divider()
    st.markdown(
        f"**回测参数：** 单边手续费 {fee} BP，权重小数位数 {digits} ，"
        f"年交易天数 {yearly_days}，品种数量：{dfw['symbol'].nunique()}"
    )
    
    # 显示核心指标
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    c1.metric("盈亏平衡点", f"{stat['盈亏平衡点']:.2%}")
    c2.metric("单笔收益（BP）", f"{stat['单笔收益']}")
    c3.metric("交易胜率", f"{stat['交易胜率']:.2%}")
    c4.metric("持仓K线数", f"{stat['持仓K线数']}")
    c5.metric("最大回撤", f"{stat['最大回撤']:.2%}")
    c6.metric("年化收益率", f"{stat['年化']:.2%}")
    c7.metric("夏普比率", f"{stat['夏普']:.2f}")
    c8.metric("卡玛比率", f"{stat['卡玛']:.2f}")
    c9.metric("年化波动率", f"{stat['年化波动率']:.2%}")
    c10.metric("多头占比", f"{stat['多头占比']:.2%}")
    c11.metric("空头占比", f"{stat['空头占比']:.2%}")

    # 显示交易方向统计
    with st.popover(label="交易方向统计", help="统计多头、空头交易次数、胜率、盈亏比等信息"):
        dfx = pd.DataFrame([wb.long_stats, wb.short_stats])
        dfx.index = ["多头", "空头"]
        dfx.index.name = "交易方向"
        st.dataframe(dfx.T.astype(str), use_container_width=True)

    # 显示日收益
    dret = wb.daily_return.copy()
    dret["dt"] = pd.to_datetime(dret["date"])
    dret = dret.set_index("dt").drop(columns=["date"])
    
    from .returns import show_daily_return, show_drawdowns, show_monthly_return
    from .statistics import show_splited_daily, show_yearly_stats
    
    show_daily_return(dret, legend_only_cols=dfw["symbol"].unique().tolist(), 
                     yearly_days=yearly_days, **kwargs)

    if kwargs.get("show_drawdowns", False):
        show_drawdowns(dret, ret_col="total", sub_title="")

    if kwargs.get("show_splited_daily", False):
        with st.expander("品种等权日收益分段表现", expanded=False):
            show_splited_daily(dret[["total"]].copy(), ret_col="total", yearly_days=yearly_days)

    if kwargs.get("show_yearly_stats", False):
        with st.expander("年度绩效指标", expanded=False):
            show_yearly_stats(dret, ret_col="total")

    if kwargs.get("show_monthly_return", False):
        with st.expander("月度累计收益", expanded=False):
            show_monthly_return(dret, ret_col="total", sub_title="")

    if kwargs.get("show_weight_distribution", True):
        with st.expander("策略分品种的 weight 分布", expanded=False):
            show_weight_distribution(dfw, abs_weight=True)

    return wb


def show_holds_backtest(df, **kwargs):
    """分析持仓组合的回测结果

    :param df: 回测数据，任何字段都不允许有空值；建议 weight 列在截面的和为 1；数据样例：
        ===================  ========  ========  =======
        dt                   symbol      weight    n1b
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs:
        - fee: 单边手续费，单位为BP，默认为2BP
        - digits: 权重小数位数，默认为2
        - show_drawdowns: 是否展示最大回撤分析，默认为True
        - show_splited_daily: 是否展示分段收益表现，默认为False
        - show_yearly_stats: 是否展示年度绩效指标，默认为True
        - show_monthly_return: 是否展示月度累计收益，默认为True
    """
    from czsc.utils.stats import holds_performance
    
    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    
    if (df.isnull().sum().sum() > 0) or (df.isna().sum().sum() > 0):
        st.warning("数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(df[df.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    # 计算每日收益、交易成本、净收益
    sdt = df["dt"].min().strftime("%Y-%m-%d")
    edt = df["dt"].max().strftime("%Y-%m-%d")
    dfr = holds_performance(df, fee=fee, digits=digits)
    st.write(f"回测时间：{sdt} ~ {edt}; 单边年换手率：{dfr['change'].mean() * 252:.2f} 倍; 单边费率：{fee}BP")
    
    daily = dfr[["date", "edge_post_fee"]].copy()
    daily.columns = ["dt", "return"]
    daily["dt"] = pd.to_datetime(daily["dt"])
    daily = daily.sort_values("dt").reset_index(drop=True)

    from .returns import show_daily_return, show_drawdowns, show_monthly_return
    from .statistics import show_splited_daily, show_yearly_stats
    
    show_daily_return(daily, stat_hold_days=False)
    
    if kwargs.get("show_drawdowns", True):
        st.write("最大回撤分析")
        show_drawdowns(daily, ret_col="return", sub_title="")

    if kwargs.get("show_splited_daily", False):
        st.write("分段收益表现")
        show_splited_daily(daily, ret_col="return")

    if kwargs.get("show_yearly_stats", True):
        st.write("年度绩效指标")
        show_yearly_stats(daily, ret_col="return", sub_title="")

    if kwargs.get("show_monthly_return", True):
        st.write("月度累计收益")
        show_monthly_return(daily, ret_col="return", sub_title="")


def show_stoploss_by_direction(dfw, **kwargs):
    """按方向止损分析的展示

    :param dfw: pd.DataFrame, 包含权重数据
    :param kwargs: dict, 其他参数
        - stoploss: float, 止损比例
        - show_detail: bool, 是否展示详细信息
        - digits: int, 价格小数位数, 默认2
        - fee_rate: float, 手续费率, 默认0.0002
    """
    from czsc.traders.weight_backtest import stoploss_by_direction
    
    dfw = dfw.copy()
    stoploss = kwargs.pop("stoploss", 0.08)
    dfw1 = stoploss_by_direction(dfw, stoploss=stoploss)

    # 找出逐笔止损点
    rows = []
    for symbol, dfg in dfw1.groupby("symbol"):
        for order_id, dfg1 in dfg.groupby("order_id"):
            if dfg1["is_stop"].any():
                row = {
                    "symbol": symbol,
                    "order_id": order_id,
                    "交易方向": "多头" if dfg1["weight"].iloc[0] > 0 else "空头",
                    "开仓时间": dfg1["dt"].iloc[0],
                    "平仓时间": dfg1["dt"].iloc[-1],
                    "平仓收益": dfg1["hold_returns"].iloc[-1],
                    "止损时间": dfg1[dfg1["is_stop"]]["dt"].iloc[0],
                    "止损收益": dfg1[dfg1["is_stop"]]["hold_returns"].iloc[0],
                }
                rows.append(row)
    
    dfr = pd.DataFrame(rows)
    with st.expander("逐笔止损点", expanded=False):
        st.dataframe(dfr, use_container_width=True)

    if kwargs.pop("show_detail", False):
        cols = [
            "dt", "symbol", "raw_weight", "weight", "price", "hold_returns",
            "min_hold_returns", "returns", "order_id", "is_stop",
        ]
        dfs = dfw1[dfw1["is_stop"]][cols].copy()
        with st.expander("止损点详情", expanded=False):
            st.dataframe(dfs, use_container_width=True)

    show_weight_backtest(dfw1[["dt", "symbol", "weight", "price"]].copy(), **kwargs) 