"""
收益相关的可视化组件

包含日收益、累计收益、月度收益、回撤分析等可视化功能
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from .base import safe_import_daily_performance, safe_import_top_drawdowns, apply_stats_style, ensure_datetime_index


def show_daily_return(df: pd.DataFrame, **kwargs):
    """用 streamlit 展示日收益

    :param df: pd.DataFrame，数据源
    :param kwargs:
        - sub_title: str，标题
        - stat_hold_days: bool，是否展示持有日绩效指标，默认为 True
        - legend_only_cols: list，仅在图例中展示的列名
        - use_st_table: bool，是否使用 st.table 展示绩效指标，默认为 False
        - plot_cumsum: bool，是否展示日收益累计曲线，默认为 True
        - yearly_days: int，年交易天数，默认为 252
        - show_dailys: bool，是否展示日收益数据详情，默认为 False
    """
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    df = ensure_datetime_index(df)
    yearly_days = kwargs.get("yearly_days", 252)
    df = df.copy().fillna(0).sort_index(ascending=True)

    def _stats(df_, type_="持有日"):
        stats = []
        for _col in df_.columns:
            if type_ == "持有日":
                col_stats = daily_performance([x for x in df_[_col] if x != 0], yearly_days=yearly_days)
            else:
                col_stats = daily_performance(df_[_col], yearly_days=yearly_days)
            col_stats["日收益名称"] = _col
            stats.append(col_stats)

        stats_df = pd.DataFrame(stats).set_index("日收益名称")
        return apply_stats_style(stats_df)

    # 参数处理
    use_st_table = kwargs.get("use_st_table", False)
    stat_hold_days = kwargs.get("stat_hold_days", True)
    plot_cumsum = kwargs.get("plot_cumsum", True)

    # 显示标题
    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)
    
    # 显示数据详情
    if kwargs.get("show_dailys", False):
        with st.expander("日收益数据详情", expanded=False):
            st.dataframe(df, use_container_width=True)
    
    # 显示交易日绩效
    if stat_hold_days:
        with st.expander("交易日绩效指标", expanded=True):
            stats = _stats(df, type_="交易日")
            if use_st_table:
                st.table(stats)
            else:
                st.dataframe(stats, use_container_width=True)
            st.caption("交易日：交易所指定的交易日，或者有收益发生变化的日期")
    else:
        stats = _stats(df, type_="交易日")
        if use_st_table:
            st.table(stats)
        else:
            st.dataframe(stats, use_container_width=True)

    # 显示持有日绩效
    if stat_hold_days:
        with st.expander("持有日绩效指标", expanded=False):
            st.dataframe(_stats(df, type_="持有日"), use_container_width=True)
            st.caption("持有日：在交易日的基础上，将收益率为0的日期删除")

    # 显示累计收益曲线
    if plot_cumsum:
        df_cumsum = df.cumsum()
        fig = px.line(df_cumsum, y=df_cumsum.columns.to_list(), title="日收益累计曲线")
        fig.update_xaxes(title="")

        # 添加年度分隔线
        years = df_cumsum.index.year.unique()
        for year in years:
            first_date = df_cumsum[df_cumsum.index.year == year].index.min()
            fig.add_vline(x=first_date, line_dash="dash", line_color="red")

        # 设置图例显示
        for col in kwargs.get("legend_only_cols", []):
            fig.update_traces(visible="legendonly", selector=dict(name=col))
        
        fig.update_layout(margin=dict(l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)


def show_cumulative_returns(df, **kwargs):
    """展示累计收益曲线
    
    :param df: pd.DataFrame, 数据源，index 为日期，columns 为对应策略上一个日期至当前日期的收益
    :param kwargs: dict, 可选参数
        - fig_title: str, 图表标题，默认为 "累计收益"
        - legend_only_cols: list, 仅在图例中展示的列名
        - display_legend: bool, 是否展示图例，默认为 True
    """
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    assert df.index.is_unique, "df 的索引必须唯一"
    assert df.index.is_monotonic_increasing, "df 的索引必须单调递增"

    display_legend = kwargs.get("display_legend", True)
    fig_title = kwargs.get("fig_title", "累计收益")
    
    df_cumsum = df.cumsum()
    fig = px.line(df_cumsum, y=df_cumsum.columns.to_list(), title=fig_title)
    fig.update_xaxes(title="")

    # 添加年度分隔线
    years = df_cumsum.index.year.unique()
    for year in years:
        first_date = df_cumsum[df_cumsum.index.year == year].index.min()
        fig.add_vline(x=first_date, line_dash="dash", line_color="red")

    # 设置图例显示
    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector=dict(name=col))
    
    if display_legend:
        fig.update_layout(legend=dict(
            orientation="h", y=-0.1, xanchor="center", x=0.5
        ), margin=dict(l=0, r=0, b=0))
        
    st.plotly_chart(fig, use_container_width=True, 
                   config={"displayModeBar": not display_legend})


def show_monthly_return(df, ret_col="total", sub_title="月度累计收益", **kwargs):
    """展示指定列的月度累计收益

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param sub_title: str，标题
    """
    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    df = ensure_datetime_index(df)
    df = df.copy().fillna(0).sort_index(ascending=True)

    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    # 计算月度收益
    monthly = df[[ret_col]].resample("ME").sum()
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly = monthly.pivot_table(index="year", columns="month", values=ret_col)
    
    # 设置列名
    month_cols = [f"{x}月" for x in monthly.columns]
    monthly.columns = month_cols
    monthly["年收益"] = monthly.sum(axis=1)

    # 计算统计指标
    win_rate = monthly.apply(lambda x: (x > 0).sum() / len(x), axis=0)
    ykb = monthly.apply(lambda x: x[x > 0].sum() / -x[x < 0].sum() if min(x) < 0 else 10, axis=0)
    mean_ret = monthly.mean(axis=0)
    
    # 应用样式
    monthly_styled = monthly.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=month_cols)
    monthly_styled = monthly_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年收益"])
    monthly_styled = monthly_styled.format("{:.2%}", na_rep="-")
    
    st.dataframe(monthly_styled, use_container_width=True)
    
    # 显示统计信息
    dfy = pd.DataFrame([win_rate, ykb, mean_ret], index=["胜率", "盈亏比", "平均收益"])
    dfy_styled = dfy.style.background_gradient(cmap="RdYlGn_r", axis=1).format("{:.2%}", na_rep="-")
    st.dataframe(dfy_styled, use_container_width=True)
    
    st.caption("注：月度收益为累计收益，胜率为月度收益大于0的占比，盈亏比为月度盈利总额与月度亏损总额的比值，如果月度亏损总额为0，则盈亏比为10")


def show_drawdowns(df: pd.DataFrame, ret_col, **kwargs):
    """展示最大回撤分析

    :param df: pd.DataFrame, columns: cells, index: dates
    :param ret_col: str, 回报率列名称
    :param kwargs:
        - sub_title: str, optional, 子标题
        - top: int, optional, 默认10, 返回最大回撤的数量
    """
    top_drawdowns = safe_import_top_drawdowns()
    if top_drawdowns is None:
        return
        
    df = ensure_datetime_index(df)
    df = df[[ret_col]].copy().fillna(0).sort_index(ascending=True)
    
    # 计算回撤数据
    df["cum_ret"] = df[ret_col].cumsum()
    df["cum_max"] = df["cum_ret"].cummax()
    df["drawdown"] = df["cum_ret"] - df["cum_max"]

    sub_title = kwargs.get("sub_title", "最大回撤分析")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 绘制回撤图
    fig = go.Figure()
    
    # 回撤曲线
    fig.add_trace(go.Scatter(
        x=df.index, y=df["drawdown"], fillcolor="salmon", line=dict(color="salmon"),
        fill="tozeroy", mode="lines", name="回撤曲线", opacity=0.5
    ))
    
    # 累计收益曲线（右轴）
    fig.add_trace(go.Scatter(
        x=df.index, y=df["cum_ret"], mode="lines", name="累计收益", 
        yaxis="y2", opacity=0.8, line=dict(color="red")
    ))
    
    fig.update_layout(yaxis2=dict(title="累计收益", overlaying="y", side="right"))

    # 添加分位数线
    for q in [0.1, 0.3, 0.5]:
        y1 = df["drawdown"].quantile(q)
        fig.add_hline(y=y1, line_dash="dot", line_color="green", line_width=1)
        fig.add_annotation(
            x=df.index[5], y=y1, text=f"{q:.1%} (DD: {y1:.2%})",
            showarrow=False, yshift=10
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), title="", 
        xaxis_title="", yaxis_title="净值回撤", 
        legend_title="回撤分析", height=300
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示回撤详情
    top = kwargs.get("top", 10)
    if top is not None:
        with st.expander(f"TOP{top} 最大回撤详情", expanded=False):
            dft = top_drawdowns(df[ret_col].copy(), top=top)
            dft_styled = dft.style.background_gradient(cmap="RdYlGn_r", subset=["净值回撤"])
            dft_styled = dft_styled.background_gradient(cmap="RdYlGn", subset=["回撤天数", "恢复天数", "新高间隔"])
            dft_styled = dft_styled.format({
                "净值回撤": "{:.2%}", "回撤天数": "{:.0f}", 
                "恢复天数": "{:.0f}", "新高间隔": "{:.0f}"
            })
            st.dataframe(dft_styled, use_container_width=True)


def show_rolling_daily_performance(df, ret_col, **kwargs):
    """展示滚动统计数据

    :param df: pd.DataFrame, 日收益数据，columns=['dt', ret_col]
    :param ret_col: str, 收益列名
    """
    from czsc.utils.stats import rolling_daily_performance

    df = ensure_datetime_index(df)
    df = df[[ret_col]].copy().fillna(0).sort_index(ascending=True)

    sub_title = kwargs.get("sub_title", "滚动日收益绩效")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    # 参数设置
    c1, c2, c3 = st.columns(3)
    window = c1.number_input("滚动窗口（自然日）", value=365 * 3, min_value=365, max_value=3650)
    min_periods = c2.number_input("最小样本数", value=365, min_value=100, max_value=3650)

    # 计算滚动绩效
    dfr = rolling_daily_performance(df, ret_col, window=window, min_periods=min_periods)
    dfr["年化波动率/最大回撤"] = dfr["年化波动率"] / dfr["最大回撤"]
    
    # 选择指标
    cols = [x for x in dfr.columns if x not in ["sdt", "edt"]]
    col = c3.selectbox("选择指标", cols, index=cols.index("夏普") if "夏普" in cols else 0)
    
    # 绘图
    fig = px.area(dfr, x="edt", y=col, labels={"edt": "", col: col})
    st.plotly_chart(fig, use_container_width=True) 