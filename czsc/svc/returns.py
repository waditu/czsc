"""
收益相关的 Streamlit 可视化组件

本模块面向"日收益序列"这一核心数据结构，提供以下交互式组件：

1. :func:`show_daily_return`：日收益数据的整体展示，包括交易日 / 持有日两套绩效指标，
   以及累计收益曲线（含年度分隔线）；
2. :func:`show_cumulative_returns`：纯粹的累计收益曲线绘制，不带绩效统计；
3. :func:`show_monthly_return`：月度收益矩阵 + 胜率 / 盈亏比 / 平均收益统计；
4. :func:`show_drawdowns`：最大回撤曲线、Top N 回撤详情；
5. :func:`show_rolling_daily_performance`：滚动窗口下的日收益绩效曲线。

约定：
- ``df`` 的索引必须为 ``datetime64[ns]``；如不是则可借助 :func:`ensure_datetime_index`
  从 ``dt`` 列设置；
- 收益列默认是百分比变化值（如 0.01 表示 1%）。
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from wbt import daily_performance

from czsc import top_drawdowns

from .base import apply_stats_style, ensure_datetime_index, generate_component_key


def show_daily_return(df: pd.DataFrame, key=None, **kwargs):
    """用 streamlit 展示日收益

    支持同时展示交易日与持有日两套绩效指标，并绘制累计收益曲线。可通过 ``kwargs``
    控制是否显示明细表格、是否仅在图例中保留某些列、自定义年化天数等。

    :param df: pd.DataFrame，数据源；索引为日期，每列代表一条日收益序列
    :param key: str，可选；组件唯一标识符
    :param kwargs: 其他参数
        - sub_title: str，标题
        - stat_hold_days: bool，是否展示持有日绩效指标，默认 True
        - legend_only_cols: list，仅在图例中显示（默认隐藏曲线）的列名
        - use_st_table: bool，是否使用 ``st.table`` 展示绩效指标，默认 False
        - plot_cumsum: bool，是否绘制累计收益曲线，默认 True
        - yearly_days: int，年交易天数，默认 252
        - show_dailys: bool，是否展示日收益数据明细，默认 False
    :return: None
    """
    df = ensure_datetime_index(df)
    yearly_days = kwargs.get("yearly_days", 252)
    df = df.copy().fillna(0).sort_index(ascending=True)

    def _stats(df_, type_="持有日"):
        """计算每列的日收益绩效，并以 Styler 形式返回"""
        stats = []
        for _col in df_.columns:
            if type_ == "持有日":
                # 持有日：剔除收益为 0 的日期
                col_stats = daily_performance([x for x in df_[_col] if x != 0], yearly_days=yearly_days)
            else:
                # 交易日：包含所有交易日
                col_stats = daily_performance(df_[_col], yearly_days=yearly_days)
            col_stats["日收益名称"] = _col
            stats.append(col_stats)

        stats_df = pd.DataFrame(stats).set_index("日收益名称")
        return apply_stats_style(stats_df)

    # 解析展示相关参数
    use_st_table = kwargs.get("use_st_table", False)
    stat_hold_days = kwargs.get("stat_hold_days", True)
    plot_cumsum = kwargs.get("plot_cumsum", True)

    # 标题
    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    # 可选展开详情：原始日收益矩阵
    if kwargs.get("show_dailys", False):
        with st.expander("日收益数据详情", expanded=False):
            st.dataframe(df, width="stretch")

    # 交易日绩效
    if stat_hold_days:
        with st.expander("交易日绩效指标", expanded=True):
            stats = _stats(df, type_="交易日")
            if use_st_table:
                st.table(stats)
            else:
                st.dataframe(stats, width="stretch")
            st.caption("交易日：交易所指定的交易日，或者有收益发生变化的日期")
    else:
        stats = _stats(df, type_="交易日")
        if use_st_table:
            st.table(stats)
        else:
            st.dataframe(stats, width="stretch")

    # 持有日绩效
    if stat_hold_days:
        with st.expander("持有日绩效指标", expanded=False):
            st.dataframe(_stats(df, type_="持有日"), width="stretch")
            st.caption("持有日：在交易日的基础上，将收益率为0的日期删除")

    # 累计收益曲线
    if plot_cumsum:
        df_cumsum = df.cumsum()
        fig = px.line(df_cumsum, y=df_cumsum.columns.to_list(), title="日收益累计曲线")
        fig.update_xaxes(title="")

        # 给每个自然年的开始位置画一条红色虚线，方便对比
        years = df_cumsum.index.year.unique()
        for year in years:
            first_date = df_cumsum[df_cumsum.index.year == year].index.min()
            fig.add_vline(x=first_date, line_dash="dash", line_color="red")

        # 将指定列设置为"仅图例可见"，默认不展示曲线
        for col in kwargs.get("legend_only_cols", []):
            fig.update_traces(visible="legendonly", selector={"name": col})

        fig.update_layout(margin={"l": 0, "r": 0, "b": 0})

        # 自动生成组件 key
        if key is None:
            key = generate_component_key(
                df, prefix="daily_ret", plot_cumsum=plot_cumsum, legend_only_cols=kwargs.get("legend_only_cols", [])
            )

        st.plotly_chart(fig, key=key, width="stretch")


def show_cumulative_returns(df, key=None, **kwargs):
    """展示累计收益曲线

    本函数不计算绩效，只对输入的日收益做 ``cumsum`` 后绘制折线图，并加上年度
    分隔线。适合作为"组合""多策略对比"等场景的轻量绘图工具。

    :param df: pd.DataFrame，数据源；索引为日期（必须 datetime64[ns] 且单调递增、唯一），
        每列代表一条策略的日收益
    :param key: str，可选；组件唯一标识符
    :param kwargs: 其他参数
        - fig_title: str，图表标题，默认 ``"累计收益"``
        - legend_only_cols: list，仅在图例中显示的列名
        - display_legend: bool，是否展示图例，默认 True
    :return: None
    """
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    assert df.index.is_unique, "df 的索引必须唯一"
    assert df.index.is_monotonic_increasing, "df 的索引必须单调递增"

    display_legend = kwargs.get("display_legend", True)
    fig_title = kwargs.get("fig_title", "累计收益")

    df_cumsum = df.fillna(0).cumsum()
    fig = px.line(df_cumsum, y=df_cumsum.columns.to_list(), title=fig_title)
    fig.update_xaxes(title="")

    # 年度分隔线
    years = df_cumsum.index.year.unique()
    for year in years:
        first_date = df_cumsum[df_cumsum.index.year == year].index.min()
        fig.add_vline(x=first_date, line_dash="dash", line_color="red")

    # 设置图例显示
    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector={"name": col})

    if display_legend:
        # 将图例放到图表下方水平居中
        fig.update_layout(
            legend={"orientation": "h", "y": -0.1, "xanchor": "center", "x": 0.5}, margin={"l": 0, "r": 0, "b": 0}
        )

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df, prefix="cum_ret", fig_title=fig_title, legend_only_cols=kwargs.get("legend_only_cols", [])
        )

    st.plotly_chart(fig, key=key, width="stretch", config={"displayModeBar": not display_legend})


def show_monthly_return(df, ret_col="total", sub_title="月度累计收益", **kwargs):
    """展示指定列的月度累计收益

    将日收益数据按月汇总成"年 × 月"的二维矩阵，并附加年度合计、胜率、盈亏比、
    平均收益等汇总指标，配以统一的红黄绿配色。

    :param df: pd.DataFrame，数据源；索引或 dt 列为日期
    :param ret_col: str，收益列名
    :param sub_title: str，标题
    :return: None
    """
    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    df = ensure_datetime_index(df)
    df = df.copy().fillna(0).sort_index(ascending=True)

    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    # 月度求和并构造透视表
    monthly = df[[ret_col]].resample("ME").sum()
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly = monthly.pivot_table(index="year", columns="month", values=ret_col)

    # 将列名改为"X月"，并补充年收益列
    month_cols = [f"{x}月" for x in monthly.columns]
    monthly.columns = month_cols
    monthly["年收益"] = monthly.sum(axis=1)

    # 月度胜率、盈亏比、平均收益
    win_rate = monthly.apply(lambda x: (x > 0).sum() / len(x), axis=0)
    # 月度亏损总额为 0 时，盈亏比记为 10（一个表示"非常好"的占位值）
    ykb = monthly.apply(lambda x: x[x > 0].sum() / -x[x < 0].sum() if min(x) < 0 else 10, axis=0)
    mean_ret = monthly.mean(axis=0)

    # 月度矩阵着色
    monthly_styled = monthly.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=month_cols)
    monthly_styled = monthly_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年收益"])
    monthly_styled = monthly_styled.format("{:.2%}", na_rep="-")

    st.dataframe(monthly_styled, width="stretch")

    # 月度统计指标
    dfy = pd.DataFrame([win_rate, ykb, mean_ret], index=["胜率", "盈亏比", "平均收益"])
    dfy_styled = dfy.style.background_gradient(cmap="RdYlGn_r", axis=1).format("{:.2%}", na_rep="-")
    st.dataframe(dfy_styled, width="stretch")

    st.caption(
        "注：月度收益为累计收益，胜率为月度收益大于0的占比，盈亏比为月度盈利总额与月度亏损总额的比值，如果月度亏损总额为0，则盈亏比为10"
    )


def show_drawdowns(df: pd.DataFrame, ret_col, key=None, **kwargs):
    """展示最大回撤分析

    根据日收益重建累计收益与累计最高，绘制回撤曲线（双 Y 轴叠加累计收益），并
    给出 10% / 30% / 50% 三个分位数辅助线。同时通过 :func:`top_drawdowns` 展示
    Top N 回撤的详细信息（开始时间、结束时间、回撤天数等）。

    :param df: pd.DataFrame，列包含 ``ret_col``，索引为日期
    :param ret_col: str，回报率列名称
    :param key: str，可选；组件唯一标识符
    :param kwargs: 其他参数
        - sub_title: str，子标题
        - top: int，返回最大回撤的数量，默认 10
    :return: None
    """
    df = ensure_datetime_index(df)
    df = df[[ret_col]].copy().fillna(0).sort_index(ascending=True)

    # 计算累计收益、累计最高与回撤
    df["cum_ret"] = df[ret_col].cumsum()
    df["cum_max"] = df["cum_ret"].cummax()
    df["drawdown"] = df["cum_ret"] - df["cum_max"]

    sub_title = kwargs.get("sub_title", "最大回撤分析")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 双轴绘图：左轴回撤填充，右轴累计收益曲线
    fig = go.Figure()

    # 回撤曲线（向下填充）
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["drawdown"],
            fillcolor="salmon",
            line={"color": "salmon"},
            fill="tozeroy",
            mode="lines",
            name="回撤曲线",
            opacity=0.5,
        )
    )

    # 累计收益曲线（右 Y 轴）
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["cum_ret"], mode="lines", name="累计收益", yaxis="y2", opacity=0.8, line={"color": "red"}
        )
    )

    fig.update_layout(yaxis2={"title": "累计收益", "overlaying": "y", "side": "right"})

    # 加上 10%、30%、50% 三个分位数辅助线
    for q in [0.1, 0.3, 0.5]:
        y1 = df["drawdown"].quantile(q)
        fig.add_hline(y=y1, line_dash="dot", line_color="green", line_width=1)
        fig.add_annotation(x=df.index[5], y=y1, text=f"{q:.1%} (DD: {y1:.2%})", showarrow=False, yshift=10)

    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        title="",
        xaxis_title="",
        yaxis_title="净值回撤",
        legend_title="回撤分析",
        height=300,
    )

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(df, prefix="dd", ret_col=ret_col, top=kwargs.get("top", 10))

    st.plotly_chart(fig, key=key, width="stretch")

    # Top N 回撤详情
    top = kwargs.get("top", 10)
    if top is not None:
        with st.expander(f"TOP{top} 最大回撤详情", expanded=False):
            dft = top_drawdowns(df[ret_col].copy(), top=top)
            dft_styled = dft.style.background_gradient(cmap="RdYlGn_r", subset=["净值回撤"])
            dft_styled = dft_styled.background_gradient(cmap="RdYlGn", subset=["回撤天数", "恢复天数", "新高间隔"])
            dft_styled = dft_styled.format(
                {"净值回撤": "{:.2%}", "回撤天数": "{:.0f}", "恢复天数": "{:.0f}", "新高间隔": "{:.0f}"}
            )
            st.dataframe(dft_styled, width="stretch")


def show_rolling_daily_performance(df, ret_col, key=None, **kwargs):
    """展示滚动统计数据

    在指定窗口（自然日）下，计算日收益的滚动绩效指标（如年化、夏普、最大回撤等），
    并以面积图展示用户选择的指标随时间的变化。

    :param df: pd.DataFrame，日收益数据；索引为日期，包含 ``ret_col`` 列
    :param ret_col: str，收益列名
    :param key: str，可选；组件唯一标识符
    :param kwargs: 其他参数
        - sub_title: str，子标题
    :return: None
    """
    from czsc.utils.analysis.stats import rolling_daily_performance

    df = ensure_datetime_index(df)
    df = df[[ret_col]].copy().fillna(0).sort_index(ascending=True)

    sub_title = kwargs.get("sub_title", "滚动日收益绩效")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    # 用户参数：滚动窗口、最小样本数、绩效指标
    c1, c2, c3 = st.columns(3)
    window = c1.number_input("滚动窗口（自然日）", value=365 * 3, min_value=365, max_value=3650)
    min_periods = c2.number_input("最小样本数", value=365, min_value=100, max_value=3650)

    # 计算滚动绩效，并补充一个"年化波动率/最大回撤"派生指标
    dfr = rolling_daily_performance(df, ret_col, window=window, min_periods=min_periods)
    dfr["年化波动率/最大回撤"] = dfr["年化波动率"] / dfr["最大回撤"]

    # 用户挑选要展示的指标
    cols = [x for x in dfr.columns if x not in ["sdt", "edt"]]
    col = c3.selectbox("选择指标", cols, index=cols.index("夏普") if "夏普" in cols else 0)

    # 用面积图展示该指标随时间的变化
    fig = px.area(dfr, x="edt", y=col, labels={"edt": "", col: col})

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df, prefix="roll_perf", ret_col=ret_col, col=col, window=window, min_periods=min_periods
        )

    st.plotly_chart(fig, key=key, width="stretch")
