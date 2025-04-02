# 飞书文档：https://s0cqcxuy3p.feishu.cn/wiki/AATuw5vN7iN9XbkVPuwcE186n9f

# import czsc
import hashlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from deprecated import deprecated
from typing import Optional


def __stats_style(stats):
    columns = [
        "绝对收益", "年化", "夏普", "最大回撤", "卡玛", "日胜率",
        "日盈亏比", "日赢面", "年化波动率", "下行波动率", "非零覆盖",
        "盈亏平衡点", "新高间隔", "新高占比", "回撤风险"
    ]
    stats = stats[columns]
    stats = stats.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年化"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["绝对收益"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["夏普"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["最大回撤"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["卡玛"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["年化波动率"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["下行波动率"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["盈亏平衡点"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日胜率"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日盈亏比"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日赢面"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["非零覆盖"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["新高间隔"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["回撤风险"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["新高占比"])
    stats = stats.format(
        {
            "盈亏平衡点": "{:.2f}",
            "年化波动率": "{:.2%}",
            "下行波动率": "{:.2%}",
            "最大回撤": "{:.2%}",
            "卡玛": "{:.2f}",
            "年化": "{:.2%}",
            "夏普": "{:.2f}",
            "非零覆盖": "{:.2%}",
            "绝对收益": "{:.2%}",
            "日胜率": "{:.2%}",
            "日盈亏比": "{:.2f}",
            "日赢面": "{:.2%}",
            "新高间隔": "{:.2f}",
            "回撤风险": "{:.2f}",
            "新高占比": "{:.2%}",
        }
    )
    return stats


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
    from czsc import daily_performance

    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    yearly_days = kwargs.get("yearly_days", 252)

    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    def _stats(df_, type_="持有日"):
        df_ = df_.copy()
        stats = []
        for _col in df_.columns:
            if type_ == "持有日":
                col_stats = daily_performance([x for x in df_[_col] if x != 0], yearly_days=yearly_days)
            else:
                assert type_ == "交易日", "type_ 参数必须是 持有日 或 交易日"
                col_stats = daily_performance(df_[_col], yearly_days=yearly_days)
            col_stats["日收益名称"] = _col
            stats.append(col_stats)

        stats = pd.DataFrame(stats).set_index("日收益名称")
        stats = __stats_style(stats)
        return stats

    use_st_table = kwargs.get("use_st_table", False)
    stat_hold_days = kwargs.get("stat_hold_days", True)
    plot_cumsum = kwargs.get("plot_cumsum", True)

    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)
    
    if kwargs.get("show_dailys", False):
        with st.expander("日收益数据详情", expanded=False):
            st.dataframe(df, use_container_width=True)
    
    if stat_hold_days:
        with st.expander("交易日绩效指标", expanded=True):
            if use_st_table:
                st.table(_stats(df, type_="交易日"))
            else:
                st.dataframe(_stats(df, type_="交易日"), use_container_width=True)
            st.caption("交易日：交易所指定的交易日，或者有收益发生变化的日期")
    else:
        if use_st_table:
            st.table(_stats(df, type_="交易日"))
        else:
            st.dataframe(_stats(df, type_="交易日"), use_container_width=True)

    if stat_hold_days:
        with st.expander("持有日绩效指标", expanded=False):
            st.dataframe(_stats(df, type_="持有日"), use_container_width=True)
            st.caption("持有日：在交易日的基础上，将收益率为0的日期删除")

    if plot_cumsum:
        df = df.cumsum()
        fig = px.line(df, y=df.columns.to_list(), title="日收益累计曲线")
        fig.update_xaxes(title="")

        # 添加每年的开始第一个日期的竖线
        for year in range(df.index.year.min(), df.index.year.max() + 1):
            first_date = df[df.index.year == year].index.min()
            fig.add_vline(x=first_date, line_dash="dash", line_color="red")

        for col in kwargs.get("legend_only_cols", []):
            fig.update_traces(visible="legendonly", selector=dict(name=col))
        # fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
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
    import plotly.express as px

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    assert df.index.is_unique, "df 的索引必须唯一"
    assert df.index.is_monotonic_increasing, "df 的索引必须单调递增"

    display_legend = kwargs.get("display_legend", True)

    fig_title = kwargs.get("fig_title", "累计收益")
    df = df.cumsum()
    fig = px.line(df, y=df.columns.to_list(), title=fig_title)
    fig.update_xaxes(title="")

    # 添加每年的开始第一个日期的竖线
    for year in range(df.index.year.min(), df.index.year.max() + 1):
        first_date = df[df.index.year == year].index.min()
        fig.add_vline(x=first_date, line_dash="dash", line_color="red")

    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector=dict(name=col))
    
    if display_legend:
        # 将 legend 移动到图表的底部并水平居中显示
        fig.update_layout(legend=dict(
            orientation="h",
            y=-0.1,
            xanchor="center",
            x=0.5
        ), margin=dict(l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def show_monthly_return(df, ret_col="total", sub_title="月度累计收益", **kwargs):
    """展示指定列的月度累计收益

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param sub_title: str，标题
    :param kwargs:
    """
    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    monthly = df[[ret_col]].resample("ME").sum()
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly = monthly.pivot_table(index="year", columns="month", values=ret_col)
    month_cols = [f"{x}月" for x in monthly.columns]
    monthly.columns = month_cols
    monthly["年收益"] = monthly.sum(axis=1)

    # 计算月度胜率和月度盈亏比
    win_rate = monthly.apply(lambda x: (x > 0).sum() / len(x), axis=0)
    ykb = monthly.apply(lambda x: x[x > 0].sum() / -x[x < 0].sum() if min(x) < 0 else 10, axis=0)
    mean_ret = monthly.mean(axis=0)
    dfy = pd.DataFrame([win_rate, ykb, mean_ret], index=["胜率", "盈亏比", "平均收益"])

    monthly = monthly.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=month_cols)
    monthly = monthly.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年收益"])
    monthly = monthly.format("{:.2%}", na_rep="-")
    st.dataframe(monthly, use_container_width=True)
    dfy = dfy.style.background_gradient(cmap="RdYlGn_r", axis=1).format("{:.2%}", na_rep="-")
    st.dataframe(dfy, use_container_width=True)
    st.caption(
        "注：月度收益为累计收益，胜率为月度收益大于0的占比，盈亏比为月度盈利总额与月度亏损总额的比值，如果月度亏损总额为0，则盈亏比为10"
    )


def show_correlation(df, cols=None, method="pearson", **kwargs):
    """用 streamlit 展示相关性

    :param df: pd.DataFrame，数据源
    :param cols: list，分析相关性的字段
    :param method: str，计算相关性的方法，可选 pearson 和 spearman
    :param kwargs:

        - use_st_table: bool，是否使用 st.table 展示相关性，默认为 False
        - use_container_width: bool，是否使用容器宽度，默认为 True

    """
    cols = cols or df.columns.to_list()
    dfr = df[cols].corr(method=method)
    dfr = dfr.copy().where(~np.eye(dfr.shape[0], dtype=bool))

    dfr["average"] = dfr.sum(axis=1) / (len(cols) - 1)
    dfr = dfr.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.4f}", na_rep="MISS")

    if kwargs.get("use_st_table", False):
        st.table(dfr)
    else:
        st.dataframe(dfr, use_container_width=kwargs.get("use_container_width", True))


def show_sectional_ic(df, x_col, y_col, method="pearson", **kwargs):
    """使用 streamlit 展示截面IC

    :param df: pd.DataFrame，数据源
    :param x_col: str，因子列名
    :param y_col: str，收益列名
    :param method: str，计算IC的方法，可选 pearson 和 spearman
    :param kwargs:

        - show_cumsum_ic: bool，是否展示累计IC曲线，默认为 True
        - show_factor_histgram: bool，是否展示因子数据分布图，默认为 False

    """
    from czsc.utils.corr import cross_sectional_ic

    dfc, res = cross_sectional_ic(df, x_col=x_col, y_col=y_col, dt_col="dt", method=method)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
    col1.metric("IC均值", res["IC均值"])
    col1.metric("IC标准差", res["IC标准差"])
    col1.metric("累计IC回归R2", res["累计IC回归R2"])
    col2.metric("ICIR", res["ICIR"])
    col2.metric("IC胜率", res["IC胜率"])
    col2.metric("累计IC回归斜率", res["累计IC回归斜率"])
    col3.metric("IC绝对值>2%占比", res["IC绝对值>2%占比"])
    col3.metric("品种数量", df["symbol"].nunique())
    col3.metric("交易日数量", df["dt"].nunique())

    dfc[["year", "month"]] = dfc.dt.apply(lambda x: pd.Series([x.year, x.month]))
    dfc["month"] = dfc["month"].apply(lambda x: f"{x:02d}月")
    dfm = dfc.groupby(["year", "month"]).agg({"ic": "mean"}).reset_index()
    dfm = pd.pivot_table(dfm, index="year", columns="month", values="ic")
    # 在 dfm 上增加一列，用于计算每年的平均IC
    dfm["年度"] = dfc.groupby("year").agg({"ic": "mean"})

    col4.write("月度IC分析结果：")
    col4.dataframe(
        dfm.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.4f}", na_rep="MISS"),
        use_container_width=True,
    )

    if kwargs.get("show_factor_histgram", False):
        fig = px.histogram(df, x=x_col, marginal="box", title="因子数据分布图")
        st.plotly_chart(fig, use_container_width=True)

    if kwargs.get("show_cumsum_ic", True):
        dfc["ic_cumsum"] = dfc["ic"].cumsum()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dfc["dt"], y=dfc["ic"], name="IC", yaxis="y"))
        fig.add_trace(
            go.Scatter(x=dfc["dt"], y=dfc["ic_cumsum"], mode="lines", name="累计IC", yaxis="y2", line=dict(color="red"))
        )
        fig.update_layout(
            yaxis=dict(title="IC"),
            yaxis2=dict(title="累计IC", overlaying="y", side="right"),
            title="截面IC曲线",
            margin=dict(l=0, r=0, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)


def show_feature_returns(df, factor, target="n1b", **kwargs):
    """使用 streamlit 展示因子收益率

    :param df: pd.DataFrame, 必须包含 dt、symbol、factor, target 列
    :param factor: str, 因子列名
    :param target: str, 预测目标收益率列名
    :param kwargs:

        - fit_intercept: bool, 是否拟合截距，默认为 False
        - fig_title: str, 图表标题，默认为 "因子收益率分析"

    """
    assert "dt" in df.columns, "时间列必须为 dt"
    assert "symbol" in df.columns, "标的列必须为 symbol"
    assert factor in df.columns, f"因子列 {factor} 不存在"
    assert target in df.columns, f"目标列 {target} 不存在"
    from czsc.features.utils import feature_returns

    fit_intercept = kwargs.get("fit_intercept", False)

    dft = feature_returns(df, factor, target, fit_intercept=fit_intercept)
    dft.columns = ["dt", "因子收益率"]
    dft["累计收益率"] = dft["因子收益率"].cumsum()

    fig_title = kwargs.get("fig_title", "因子截面收益率分析")

    # 将因子逐K收益率 和 因子累计收益率 分左右轴，绘制在一张图上
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dft["dt"], y=dft["因子收益率"], name="因子收益率", yaxis="y"))
    fig.add_trace(
        go.Scatter(
            x=dft["dt"], y=dft["累计收益率"], mode="lines", name="累计收益率", yaxis="y2", line=dict(color="red")
        )
    )
    fig.update_layout(
        yaxis=dict(title="因子收益率"),
        yaxis2=dict(title="累计收益率", overlaying="y", side="right"),
        title=fig_title,
        margin=dict(l=0, r=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_factor_layering(df, factor, target="n1b", **kwargs):
    """使用 streamlit 绘制因子分层收益率图

    :param df: 因子数据
    :param factor: 因子列名
    :param target: 收益列名
    :param kwargs:

        - n: 分层数量，默认为10
    """
    from czsc.eda import monotonicity
    from czsc.utils.features import feature_cross_layering

    n = kwargs.get("n", 10)
    df = feature_cross_layering(df, factor, n=n)

    mr = df.groupby(["dt", f"{factor}分层"])[target].mean().reset_index()
    mrr = mr.pivot(index="dt", columns=f"{factor}分层", values=target).fillna(0)
    if "第00层" in mrr.columns:
        mrr.drop(columns=["第00层"], inplace=True)

    # 计算每层的累计收益率
    dfc = mrr.sum(axis=0).to_frame("绝对收益")

    dfc["text"] = dfc["绝对收益"].apply(lambda x: f"{x:.2%}")
    fig = px.bar(
        dfc,
        y="绝对收益",
        title="因子分层绝对收益 | 单调性：{:.2%}".format(monotonicity(dfc["绝对收益"])),
        color="绝对收益",
        color_continuous_scale="RdYlGn_r",
        text="text",
    )
    st.plotly_chart(fig, use_container_width=True)

    show_daily_return(
        mrr,
        stat_hold_days=False,
        yearly_days=kwargs.get("yearly_days", 252),
        show_dailys=kwargs.get("show_dailys", False),
    )


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
    try:
        from rs_czsc import WeightBacktest
    except ImportError:
        from czsc.traders.weight_backtest import WeightBacktest

    from czsc.eda import cal_yearly_days

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    n_jobs = kwargs.pop("n_jobs", 1)
    yearly_days = kwargs.pop("yearly_days", None)
    weight_type = kwargs.pop("weight_type", "ts")

    if not yearly_days:
        yearly_days = cal_yearly_days(dts=dfw["dt"].unique())

    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("show_weight_backtest :: 持仓权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    wb = WeightBacktest(
        dfw=dfw, fee_rate=fee / 10000, digits=digits, n_jobs=n_jobs, yearly_days=yearly_days, weight_type=weight_type
    )
    stat = wb.stats

    st.divider()
    st.markdown(
        f"**回测参数：** 单边手续费 {fee} BP，权重小数位数 {digits} ，"
        f"年交易天数 {yearly_days}，品种数量：{dfw['symbol'].nunique()}"
    )
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

    with st.popover(label="交易方向统计", help="统计多头、空头交易次数、胜率、盈亏比等信息"):
        dfx = pd.DataFrame([wb.long_stats, wb.short_stats])
        dfx.index = ["多头", "空头"]
        dfx.index.name = "交易方向"
        st.dataframe(dfx.T, use_container_width=True)

    dret = wb.daily_return.copy()
    dret["dt"] = pd.to_datetime(dret["date"])
    dret = dret.set_index("dt").drop(columns=["date"])
    show_daily_return(dret, legend_only_cols=dfw["symbol"].unique().tolist(), yearly_days=yearly_days, **kwargs)

    if kwargs.get("show_drawdowns", False):
        show_drawdowns(dret, ret_col="total", sub_title="")

    # if kwargs.get("show_backtest_detail", False):
    #     c1, c2 = st.columns([1, 1])
    #     with c1.expander("品种等权日收益", expanded=False):
    #         df_ = wb.daily_return.copy()
    #         st.dataframe(df_.style.background_gradient(cmap="RdYlGn_r").format("{:.2%}"), use_container_width=True)
    #     # with c2.expander("查看开平交易对", expanded=False):
    #     # dfp = pd.concat([v["pairs"] for k, v in wb.results.items() if k in wb.symbols], ignore_index=True)
    #     # st.dataframe(dfp, use_container_width=True)

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


def show_splited_daily(df, ret_col, **kwargs):
    """展示分段日收益表现

    :param df: pd.DataFrame
    :param ret_col: str, df 中的列名，指定收益列
    :param kwargs:

        sub_title: str, 子标题

    """
    from rs_czsc import daily_performance

    yearly_days = kwargs.get("yearly_days", 252)
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    last_dt = df.index[-1]
    sdt_map = {
        "过去1周": last_dt - pd.Timedelta(days=7),
        "过去2周": last_dt - pd.Timedelta(days=14),
        "过去1月": last_dt - pd.Timedelta(days=30),
        "过去3月": last_dt - pd.Timedelta(days=90),
        "过去6月": last_dt - pd.Timedelta(days=180),
        "过去1年": last_dt - pd.Timedelta(days=365),
        "今年以来": pd.to_datetime(f"{last_dt.year}-01-01"),
        "成立以来": df.index[0],
    }

    rows = []
    for name, sdt in sdt_map.items():
        df1 = df.loc[sdt:last_dt].copy()
        row = {
            "收益名称": name,
            "开始日期": sdt.strftime("%Y-%m-%d"),
            "结束日期": last_dt.strftime("%Y-%m-%d"),
        }
        row_ = daily_performance(df1[ret_col], yearly_days=yearly_days)
        row.update(row_)
        rows.append(row)
    dfv = pd.DataFrame(rows).set_index("收益名称")
    dfv = __stats_style(dfv)
    st.dataframe(dfv, use_container_width=True)


def show_yearly_stats(df, ret_col, **kwargs):
    """按年计算日收益表现

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param kwargs:

        - sub_title: str, 子标题
    """
    from rs_czsc import daily_performance

    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    df["年份"] = df.index.year
    yearly_days = max(len(df_) for year, df_ in df.groupby("年份"))

    _stats = []
    for year, df_ in df.groupby("年份"):
        _yst = daily_performance(df_[ret_col].to_list(), yearly_days=yearly_days)
        _yst["年份"] = year
        _stats.append(_yst)

    stats = pd.DataFrame(_stats).set_index("年份")
    stats = __stats_style(stats)

    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)
    st.dataframe(stats, use_container_width=True)


def show_ts_rolling_corr(df, col1, col2, **kwargs):
    """时序上按 rolling 的方式计算相关系数

    :param df: pd.DataFrame, 必须包含列 dt 和 col1, col2
    :param col1: str, df 中的列名
    :param col2: str, df 中的列名
    :param kwargs:

        - min_periods: int, 最小滑动窗口长度
        - window: int, 滑动窗口长度，0 表示按 expanding 方式滑动
        - corr_method: str, 相关系数计算方法，可选 pearson, kendall, spearman
        - sub_title: str, 子标题
    """
    if col1 not in df.columns or col2 not in df.columns:
        st.error(f"列 {col1} 或 {col2} 不存在，请重新输入")
        return

    if not isinstance(df.index, pd.DatetimeIndex):
        df["dt"] = pd.to_datetime(df["dt"])
        df = df.set_index("dt")

    df = df[[col1, col2]].copy()
    if df.isnull().sum().sum() > 0:
        st.dataframe(df[df.isnull().sum(axis=1) > 0])
        st.error(f"列 {col1} 或 {col2} 中存在缺失值，请先处理缺失值")
        return

    sub_title = kwargs.get("sub_title", None)
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode("utf-8")).hexdigest()[:8])

    min_periods = kwargs.get("min_periods", 300)
    window = kwargs.get("window", 2000)
    corr_method = kwargs.get("corr_method", "pearson")
    corr_result = df[col1].rolling(window=window, min_periods=min_periods).corr(df[col2], pairwise=True)

    corr_result = corr_result.dropna()
    corr_result = corr_result.rename("corr")
    line = go.Scatter(x=corr_result.index, y=corr_result, mode="lines", name="corr")
    layout = go.Layout(
        title="滑动相关系数",
        xaxis=dict(title=""),
        yaxis=dict(title="corr"),
        annotations=[
            dict(
                x=0.0,
                y=1.05,
                showarrow=False,
                xref="paper",
                yref="paper",
                font=dict(size=12),
                text=f"滑动窗口长度：{window}，最小滑动窗口长度：{min_periods}，相关系数计算方法：{corr_method}",
            )
        ],
    )
    fig = go.Figure(data=[line], layout=layout)
    st.plotly_chart(fig, use_container_width=True)


def show_ts_self_corr(df, col, **kwargs):
    """展示时序上单因子的自相关性分析结果，贡献者：guo

    :param df: pd.DataFrame, 必须包含列 dt 和 col
    :param col: str, df 中的列名
    """
    import statsmodels.api as sm

    if not isinstance(df.index, pd.DatetimeIndex):
        df["dt"] = pd.to_datetime(df["dt"])
        df = df.set_index("dt")
    df = df.sort_index(ascending=True)

    if df[col].isnull().sum() > 0:
        st.dataframe(df[df[col].isnull()])
        st.error(f"列 {col} 中存在缺失值，请先处理缺失值")
        return

    col1, col2 = st.columns(2)

    with col1:
        sub_title = f"自相关系数分析（{col}）"
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode("utf-8")).hexdigest()[:8])
        c1, c2, c3 = st.columns([2, 2, 1])
        nlags = int(c1.number_input("最大滞后阶数", value=20, min_value=1, max_value=100, step=1))
        method = c2.selectbox("选择分析方法", ["acf", "pacf"], index=0)

        if method == "acf":
            acf_result, conf_int = sm.tsa.acf(df[[col]].copy(), nlags=nlags, alpha=0.05, missing="raise")
        else:
            acf_result, conf_int = sm.tsa.pacf(df[[col]].copy(), nlags=nlags, alpha=0.05)

        bar = go.Bar(x=list(range(len(acf_result))), y=acf_result, name="自相关系数")
        upper = go.Scatter(x=list(range(len(acf_result))), y=conf_int[:, 1], mode="lines", name="95%置信区间上界")
        lower = go.Scatter(x=list(range(len(acf_result))), y=conf_int[:, 0], mode="lines", name="95%置信区间下界")
        layout = go.Layout(title=method.upper(), xaxis=dict(title="滞后阶数"), yaxis=dict(title="自相关系数"))
        fig = go.Figure(data=[bar, upper, lower], layout=layout)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sub_title = f"滞后N阶滑动相关性（{col}）"
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode("utf-8")).hexdigest()[:8])
        c1, c2, c3, c4 = st.columns(4)
        min_periods = int(c1.number_input("最小滑动窗口长度", value=20, min_value=0, step=1))
        window = int(c2.number_input("滑动窗口长度", value=200, step=1))
        corr_method = c3.selectbox("相关系数计算方法", ["pearson", "kendall", "spearman"])
        n = int(c4.number_input("自相关滞后阶数", value=1, min_value=1, step=1))

        df[f"{col}_lag{n}"] = df[col].shift(-n)
        df.dropna(subset=[f"{col}_lag{n}"], inplace=True)

        show_ts_rolling_corr(df, col, f"{col}_lag{n}", min_periods=min_periods, window=window, corr_method=corr_method)


def show_stoploss_by_direction(dfw, **kwargs):
    """按方向止损分析的展示

    :param dfw: pd.DataFrame, 包含权重数据
    :param kwargs: dict, 其他参数

        - stoploss: float, 止损比例
        - show_detail: bool, 是否展示详细信息
        - digits: int, 价格小数位数, 默认2
        - fee_rate: float, 手续费率, 默认0.0002

    :return: None
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
            "dt",
            "symbol",
            "raw_weight",
            "weight",
            "price",
            "hold_returns",
            "min_hold_returns",
            "returns",
            "order_id",
            "is_stop",
        ]
        dfs = dfw1[dfw1["is_stop"]][cols].copy()
        with st.expander("止损点详情", expanded=False):
            st.dataframe(dfs, use_container_width=True)

    show_weight_backtest(dfw1[["dt", "symbol", "weight", "price"]].copy(), **kwargs)


def show_cointegration(df, col1, col2, **kwargs):
    """分析两个时间序列协整性，贡献者：珠峰

    :param df: pd.DataFrame, 必须包含列 dt 和 col1, col2
    :param col1: str, df 中的列名
    :param col2: str, df 中的列名
    :param kwargs: dict, 其他参数

        - sub_header: str, default '', 子标题
        - docs: bool, default False, 是否显示协整检验的原理与使用说明
    """
    from statsmodels.tsa.stattools import coint

    if col1 not in df.columns or col2 not in df.columns:
        st.error(f"列 {col1} 或 {col2} 不存在，请重新输入")
        return

    if not isinstance(df.index, pd.DatetimeIndex):
        df["dt"] = pd.to_datetime(df["dt"])
        df = df.set_index("dt")

    df = df[[col1, col2]].copy()
    if df.isnull().sum().sum() > 0:
        st.warning(f"列 {col1} 或 {col2} 中存在缺失值，请先处理缺失值！！！")
        st.dataframe(df[df.isnull().sum(axis=1) > 0], use_container_width=True)
        return

    sub_header = kwargs.get("sub_header", "")
    if sub_header:
        st.subheader(sub_header, divider="rainbow")

    if kwargs.get("docs", False):
        with st.expander("协整检验原理与使用说明", expanded=False):
            st.markdown(
                """
            ##### 协整检验原理
            简而言之：两个不平稳的时间序列，如果它们的线性组合是平稳的，那么它们就是协整的。
            平稳的时间序列是指均值和方差不随时间变化的时间序列。而平稳的时间序列便可以用来进行统计分析。
            举例：两只股票的收盘价满足协整关系，那么它们的线性组合就是平稳的，进而可以进行配对交易等。

            ##### 协整检验使用说明
            教条式地解释：协整检验p值的含义是两个时间序列**不协整**的概率。一般取临界值5%来判断是否协整，低于5%则可以认为两个时间序列协整。

            协整检验原理与使用说明参考链接：[Cointegration](https://en.wikipedia.org/wiki/Cointegration)
            """
            )

    l1, l2, l3 = st.columns(3)
    t, p, crit_value = coint(df[col1], df[col2])
    l1.metric("协整检验统计量", str(round(t, 3)), help="单位根检验的T统计量。")
    l2.metric(
        "协整检验P值（不协整的概率）",
        f"{p:.2%}",
        help="两个时间序列不协整的概率，低于5%则可以认为两个时间序列协整。",
    )
    fig = px.line(df, x=df.index, y=[col1, col2])
    fig.update_layout(title=f"{col1} 与 {col2} 的曲线图对比", xaxis_title="", yaxis_title="value")
    st.plotly_chart(fig, use_container_width=True)


def show_out_in_compare(df, ret_col, mid_dt, **kwargs):
    """展示样本内外表现对比"""
    from rs_czsc import daily_performance
    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df[[ret_col]].copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    mid_dt = pd.to_datetime(mid_dt)
    dfi = df[df.index < mid_dt].copy()
    dfo = df[df.index >= mid_dt].copy()

    stats_i = daily_performance(dfi[ret_col].to_list())
    stats_i["标记"] = "样本内"
    stats_i["开始日期"] = dfi.index[0].strftime("%Y-%m-%d")
    stats_i["结束日期"] = dfi.index[-1].strftime("%Y-%m-%d")

    stats_o = daily_performance(dfo[ret_col].to_list())
    stats_o["标记"] = "样本外"
    stats_o["开始日期"] = dfo.index[0].strftime("%Y-%m-%d")
    stats_o["结束日期"] = dfo.index[-1].strftime("%Y-%m-%d")

    df_stats = pd.DataFrame([stats_i, stats_o])
    df_stats = df_stats[
        [
            "标记",
            "开始日期",
            "结束日期",
            "年化",
            "最大回撤",
            "夏普",
            "卡玛",
            "日胜率",
            "年化波动率",
            "非零覆盖",
            "盈亏平衡点",
            "新高间隔",
            "新高占比",
            "回撤风险",
        ]
    ]

    sub_title = kwargs.get("sub_title", "样本内外表现对比")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    df_stats = df_stats.style.background_gradient(cmap="RdYlGn_r", subset=["年化"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn_r", subset=["夏普"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn", subset=["最大回撤"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn_r", subset=["卡玛"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn", subset=["年化波动率"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn", subset=["盈亏平衡点"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn_r", subset=["日胜率"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn_r", subset=["非零覆盖"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn", subset=["新高间隔"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn", subset=["回撤风险"])
    df_stats = df_stats.background_gradient(cmap="RdYlGn_r", subset=["新高占比"])
    df_stats = df_stats.format(
        {
            "盈亏平衡点": "{:.2f}",
            "年化波动率": "{:.2%}",
            "最大回撤": "{:.2%}",
            "卡玛": "{:.2f}",
            "年化": "{:.2%}",
            "夏普": "{:.2f}",
            "非零覆盖": "{:.2%}",
            "日胜率": "{:.2%}",
            "新高间隔": "{:.2f}",
            "回撤风险": "{:.2f}",
            "新高占比": "{:.2%}",
        }
    )
    st.dataframe(df_stats, use_container_width=True, hide_index=True)


def show_optuna_study(study, **kwargs):
    """展示 Optuna Study 的可视化结果

    :param study: optuna.study.Study, Optuna Study 对象
    :param kwargs: dict, 其他参数

        - sub_title: str, optional, 子标题
        - keep: float, optional, 默认0.2, 保留最佳参数的比例

    :return: optuna.study.Study
    """
    import optuna

    # https://optuna.readthedocs.io/en/stable/reference/visualization/index.html
    # https://zh-cn.optuna.org/reference/visualization.html
    from czsc.utils.optuna import optuna_good_params

    sub_title = kwargs.pop("sub_title", "Optuna Study Visualization")
    if sub_title:
        anchor = hashlib.md5(sub_title.encode("utf-8")).hexdigest().upper()[:6]
        st.subheader(sub_title, divider="rainbow", anchor=anchor)

    fig = optuna.visualization.plot_contour(study)
    st.plotly_chart(fig, use_container_width=True)

    fig = optuna.visualization.plot_slice(study)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("最佳参数列表", expanded=False):
        params = optuna_good_params(study, keep=kwargs.pop("keep", 0.2))
        st.dataframe(params, use_container_width=True)
    return study


def show_drawdowns(df: pd.DataFrame, ret_col, **kwargs):
    """展示最大回撤分析

    :param df: pd.DataFrame, columns: cells, index: dates
    :param ret_col: str, 回报率列名称
    :param kwargs:

        - sub_title: str, optional, 子标题
        - top: int, optional, 默认10, 返回最大回撤的数量

    """
    from rs_czsc import top_drawdowns
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"

    df = df[[ret_col]].copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)
    df["cum_ret"] = df[ret_col].cumsum()
    df["cum_max"] = df["cum_ret"].cummax()
    df["drawdown"] = df["cum_ret"] - df["cum_max"]

    sub_title = kwargs.get("sub_title", "最大回撤分析")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    top = kwargs.get("top", 10)

    # 画图: 净值回撤
    # 颜色表：https://www.codeeeee.com/color/rgb.html
    drawdown = go.Scatter(
        x=df.index,
        y=df["drawdown"],
        fillcolor="salmon",
        line=dict(color="salmon"),
        fill="tozeroy",
        mode="lines",
        name="回撤曲线",
        opacity=0.5,
    )
    fig = go.Figure(drawdown)

    # 增加累计收益曲线，右轴
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["cum_ret"], mode="lines", name="累计收益", yaxis="y2", opacity=0.8, line=dict(color="red")
        )
    )
    fig.update_layout(yaxis2=dict(title="累计收益", overlaying="y", side="right"))

    # 增加 10% 分位数线，30% 分位数线，50% 分位数线，同时增加文本标记
    for q in [0.1, 0.3, 0.5]:
        y1 = df["drawdown"].quantile(q)
        fig.add_hline(y=y1, line_dash="dot", line_color="green", line_width=1)
        fig.add_annotation(
            x=df.index.unique()[5],
            y=y1,
            text=f"{q:.1%} (DD: {y1:.2%})",
            showarrow=False,
            yshift=10,
        )

    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    fig.update_layout(title="", xaxis_title="", yaxis_title="净值回撤", legend_title="回撤分析", height=300)
    st.plotly_chart(fig, use_container_width=True)

    if top is not None:
        with st.expander(f"TOP{top} 最大回撤详情", expanded=False):
            dft = top_drawdowns(df[ret_col].copy(), top=top)
            dft = dft.style.background_gradient(cmap="RdYlGn_r", subset=["净值回撤"])
            dft = dft.background_gradient(cmap="RdYlGn", subset=["回撤天数", "恢复天数", "新高间隔"])
            dft = dft.format(
                {
                    "净值回撤": "{:.2%}",
                    "回撤天数": "{:.0f}",
                    "恢复天数": "{:.0f}",
                    "新高间隔": "{:.0f}",
                }
            )
            st.dataframe(dft, use_container_width=True)


def show_rolling_daily_performance(df, ret_col, **kwargs):
    """展示滚动统计数据

    :param df: pd.DataFrame, 日收益数据，columns=['dt', ret_col]
    :param ret_col: str, 收益列名
    :param kwargs:
    """
    from czsc.utils.stats import rolling_daily_performance

    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df[[ret_col]].copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    sub_title = kwargs.get("sub_title", "滚动日收益绩效")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)

    c1, c2, c3 = st.columns(3)
    window = c1.number_input("滚动窗口（自然日）", value=365 * 3, min_value=365, max_value=3650)
    min_periods = c2.number_input("最小样本数", value=365, min_value=100, max_value=3650)

    dfr = rolling_daily_performance(df, ret_col, window=window, min_periods=min_periods)
    dfr["年化波动率/最大回撤"] = dfr["年化波动率"] / dfr["最大回撤"]
    cols = [x for x in dfr.columns if x not in ["sdt", "edt"]]
    col = c3.selectbox("选择指标", cols, index=cols.index("夏普"))
    fig = px.area(dfr, x="edt", y=col, labels={"edt": "", col: col})
    st.plotly_chart(fig, use_container_width=True)


def show_event_return(df, factor, **kwargs):
    """分析事件因子的收益率特征

    :param df: pd.DataFrame, 数据源
    :param factor: str, 事件因子名称
    :param kwargs: dict, 其他参数

        - max_unique: int, 因子独立值最大数量
        - agg_method: str, 聚合方法，可选值："平均收益率", "收益中位数", "盈亏比", "交易胜率", "前20%平均收益率", "后20%平均收益率"
        - sdt: str, 开始时间
        - edt: str, 结束时间
        - max_overlap: int, 最大重叠次数

    """
    from czsc.utils.events import overlap
    max_unique = kwargs.get("max_unique", 20)

    if df[factor].nunique() > max_unique:
        st.warning(f"因子分布过于离散，无法进行分析，请检查！！！因子独立值数量：{df[factor].nunique()}")
        return

    df = df.copy()
    agg_method = kwargs.get("agg_method", "平均收益率")
    sdt = kwargs.get("sdt", df["dt"].min())
    edt = kwargs.get("edt", df["dt"].max())
    max_overlap = kwargs.get("max_overlap", 3)

    df[factor] = df[factor].astype(str)
    df = overlap(df, factor, new_col="overlap", max_overlap=max_overlap)
    df = df[(df["dt"] >= sdt) & (df["dt"] <= edt)].copy()

    sdt = df["dt"].min().strftime("%Y-%m-%d")
    edt = df["dt"].max().strftime("%Y-%m-%d")
    st.write(f"时间范围：{sdt} ~ {edt}；聚合方法：{agg_method}")
    nb_cols = [x for x in df.columns.to_list() if x.startswith("n") and x.endswith("b")]

    if agg_method == "平均收益率":
        agg_method = lambda x: np.mean(x)

    if agg_method == "收益中位数":
        agg_method = lambda x: np.median(x)

    if agg_method == "前20%平均收益率":
        agg_method = lambda x: np.mean(sorted(x)[int(len(x) * 0.8) :])

    if agg_method == "后20%平均收益率":
        agg_method = lambda x: np.mean(sorted(x)[: int(len(x) * 0.2)])

    if agg_method == "盈亏比":
        agg_method = lambda x: np.mean([y for y in x if y > 0]) / abs(np.mean([y for y in x if y < 0]))

    if agg_method == "交易胜率":
        agg_method = lambda x: len([y for y in x if y > 0]) / len(x)

    def __markout(dfm, cols):
        if isinstance(cols, str):
            cols = [cols]
        dfy = dfm.groupby(cols).agg({x: agg_method for x in nb_cols}).reset_index()
        dfy["出现次数"] = dfm.groupby(cols).size().values
        dfy["覆盖率"] = dfm.groupby(cols).size().values / len(dfm)
        dfy = dfy[cols + ["出现次数", "覆盖率"] + nb_cols]
        dfy = dfy.style.background_gradient(cmap="RdYlGn_r", subset=nb_cols, axis=None)
        dfy = dfy.background_gradient(cmap="RdYlGn_r", subset=["出现次数"], axis=None)
        dfy = dfy.background_gradient(cmap="RdYlGn_r", subset=["覆盖率"], axis=None)
        dfy = dfy.background_gradient(cmap="RdYlGn_r", subset=["overlap"], axis=None)

        format_ = {x: "{:.3%}" for x in nb_cols}
        format_["出现次数"] = "{:.0f}"
        format_["覆盖率"] = "{:.2%}"
        format_["overlap"] = "{:.0f}"

        dfy = dfy.format(format_, na_rep="MISS")
        return dfy

    dfy1 = __markout(df.copy(), [factor, "overlap"])
    st.dataframe(dfy1, use_container_width=True)


def show_psi(df, factor, segment, **kwargs):
    """PSI分布稳定性

    :param df: pd.DataFrame, 数据源
    :param factor: str, 分组因子
    :param segment: str, 分段字段
    :param kwargs:

        - sub_title: str, 子标题
    """
    from czsc.utils.stats import psi
    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=f"{factor}_{segment}_PSI")

    dfi = psi(df, factor, segment)
    segs = df[segment].unique().tolist()
    segs_psi = [x for x in dfi.columns if x.endswith("_PSI")]
    dfi = dfi.style.background_gradient(cmap="RdYlGn_r", subset=segs_psi, axis=None)
    dfi = dfi.background_gradient(cmap="RdYlGn_r", subset=segs, axis=None)
    dfi = dfi.background_gradient(cmap="RdYlGn_r", subset=["PSI"], axis=None)
    dfi = dfi.format("{:.2%}", na_rep="MISS")
    st.table(dfi)


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
        st.warning("show_holds_backtest :: 数据中存在空值，请检查数据后再试；空值数据如下：")
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


def show_symbols_corr(df, factor, target="n1b", method="pearson", **kwargs):
    """展示品种相关性分析

    :param df: pd.DataFrame, 数据源，columns=['dt', 'symbol', factor, target]
    :param factor: str, 因子名称
    :param target: str, 目标列名称
    :param method: str, 相关性计算方法，默认为 pearson
    :param kwargs:

        - fig_title: str, 图表标题
    """
    dfc = df.copy().sort_values(["dt", "symbol"]).reset_index(drop=True)
    dfr = (
        dfc.groupby("symbol")
        .apply(lambda x: x[factor].corr(x[target], method=method), include_groups=False)
        .reset_index()
    )
    dfr.columns = ["symbol", "corr"]
    dfr = dfr.sort_values("corr", ascending=False)
    fig_title = kwargs.get("fig_title", f"{factor} 在品种上的相关性分布")
    fig = px.bar(dfr, x="symbol", y="corr", title=fig_title, orientation="v")
    st.plotly_chart(fig, use_container_width=True)


def show_czsc_trader(trader, max_k_num=300, **kwargs):
    """显示缠中说禅交易员详情

    :param trader: CzscTrader 对象
    :param max_k_num: 最大显示 K 线数量
    :param kwargs: 其他参数
    """
    import czsc
    from czsc.utils.ta import MACD

    sub_title = kwargs.get("sub_title", "缠中说禅交易员详情")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    if not trader.freqs or not trader.kas or not trader.positions:
        st.error("当前 trader 没有回测数据")
        return

    freqs = czsc.freqs_sorted(trader.freqs)
    st.write(f"交易品种: {trader.symbol}")
    tabs = st.tabs(freqs + ["策略详情"])

    for freq, tab in zip(freqs, tabs[:-1]):

        c = trader.kas[freq]
        sdt = c.bars_raw[-max_k_num].dt if len(c.bars_raw) > max_k_num else c.bars_raw[0].dt
        df = pd.DataFrame(c.bars_raw)
        df["DIFF"], df["DEA"], df["MACD"] = MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)

        df = df[df["dt"] >= sdt].copy()
        kline = czsc.KlineChart(n_rows=3, row_heights=(0.5, 0.3, 0.2), title="", width="100%", height=800)
        kline.add_kline(df, name="")

        if len(c.bi_list) > 0:
            bi = pd.DataFrame(
                [{"dt": x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list]
                + [{"dt": c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
            )
            fx = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in c.fx_list])
            fx = fx[fx["dt"] >= sdt]
            bi = bi[bi["dt"] >= sdt]
            kline.add_scatter_indicator(
                fx["dt"],
                fx["fx"],
                name="分型",
                row=1,
                line_width=1.2,
                visible=True,
                mode="lines",
                line_dash="dot",
                marker_color="white",
            )
            kline.add_scatter_indicator(bi["dt"], bi["bi"], name="笔", row=1, line_width=1.5)

        kline.add_sma(df, ma_seq=(5, 20, 60), row=1, visible=False, line_width=1)
        kline.add_vol(df, row=2, line_width=1)
        kline.add_macd(df, row=3, line_width=1)

        # 在基础周期上绘制交易信号
        if freq == trader.base_freq:
            for pos in trader.positions:
                bs_df = pd.DataFrame([x for x in pos.operates if x["dt"] >= sdt])
                if bs_df.empty:
                    continue

                open_ops = [czsc.Operate.LO, czsc.Operate.SO]
                bs_df["tag"] = bs_df["op"].apply(lambda x: "triangle-up" if x in open_ops else "triangle-down")
                bs_df["color"] = bs_df["op"].apply(lambda x: "red" if x in open_ops else "white")

                kline.add_scatter_indicator(
                    bs_df["dt"],
                    bs_df["price"],
                    name=pos.name,
                    text=bs_df["op_desc"],
                    row=1,
                    mode="markers",
                    marker_size=15,
                    marker_symbol=bs_df["tag"],
                    marker_color=bs_df["color"],
                    visible=False,
                    hover_template="价格: %{y:.2f}<br>时间: %{x}<br>操作: %{text}<extra></extra>",
                )

        with tab:
            config = {
                "scrollZoom": True,
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "toggleSpikelines",
                    "select2d",
                    "zoomIn2d",
                    "zoomOut2d",
                    "lasso2d",
                    "autoScale2d",
                    "hoverClosestCartesian",
                    "hoverCompareCartesian",
                ],
            }
            st.plotly_chart(kline.fig, use_container_width=True, config=config)

    with tabs[-1]:
        with st.expander("查看最新信号", expanded=False):
            if len(trader.s):
                s = {k: v for k, v in trader.s.items() if len(k.split("_")) == 3}
                st.write(s)
            else:
                st.warning("当前没有信号配置信息")
        for pos in trader.positions:
            st.divider()
            st.write(pos.name)
            st.json(pos.dump(with_data=False))


def show_strategies_recent(df, **kwargs):
    """展示最近 N 天的策略表现

    :param df: pd.DataFrame, columns=['dt', 'strategy', 'returns'], 样例如下：

        ===================  ==========  ============
        dt                   strategy    returns
        ===================  ==========  ============
        2021-01-04 00:00:00  STK001      -0.00240078
        2021-01-05 00:00:00  STK001      -0.00107012
        2021-01-06 00:00:00  STK001       0.00122168
        2021-01-07 00:00:00  STK001       0.0020896
        2021-01-08 00:00:00  STK001       0.000510725
        ===================  ==========  ============

    :param kwargs: dict

        - nseq: tuple, optional, 默认为 (1, 3, 5, 10, 20, 30, 60, 90, 120, 180, 240, 360)，展示的天数序列
    """
    nseq = kwargs.get("nseq", (1, 3, 5, 10, 20, 30, 60, 90, 120, 180, 240, 360))
    dfr = df.copy()
    dfr = pd.pivot_table(dfr, index="dt", columns="strategy", values="returns", aggfunc="sum").fillna(0)
    rows = []
    for n in nseq:
        for k, v in dfr.iloc[-n:].sum(axis=0).to_dict().items():
            rows.append({"天数": f"近{n}天", "策略": k, "收益": v})

    n_rets = pd.DataFrame(rows).pivot_table(index="策略", columns="天数", values="收益")
    n_rets = n_rets[[f"近{x}天" for x in nseq]]

    st.dataframe(
        n_rets.style.background_gradient(cmap="RdYlGn_r").format("{:.2%}", na_rep="-"),
        use_container_width=True,
        hide_index=False,
    )

    # 计算每个时间段的盈利策略数量
    win_count = n_rets.map(lambda x: 1 if x > 0 else 0).sum(axis=0)
    win_rate = n_rets.map(lambda x: 1 if x > 0 else 0).sum(axis=0) / n_rets.shape[0]
    dfs = pd.DataFrame({"盈利策略数量": win_count, "盈利策略比例": win_rate}).T
    dfs = dfs.style.background_gradient(cmap="RdYlGn_r", axis=1).format("{:.4f}", na_rep="-")
    st.dataframe(dfs, use_container_width=True)
    st.caption(f"统计截止日期：{dfr.index[-1].strftime('%Y-%m-%d')}；策略数量：{dfr.shape[1]}")


def show_factor_value(df, factor, **kwargs):
    """因子值可视化

    :param df: pd.DataFrame, columns=['dt', 'open', 'close', 'high', 'low', 'vol', factor]
    :param factor: str, 因子名称
    :param kwargs: dict, 其他参数

        - height: int, 可视化高度，默认为 600
        - row_heights: list, 默认为 [0.6, 0.1, 0.3]
        - title: str, 默认为 f"{factor} 可视化"

    """
    import czsc
    if factor not in df.columns:
        st.warning(f"因子 {factor} 不存在，请检查")
        return
    
    # dt 列不允许有重复值
    if df["dt"].duplicated().any():
        st.warning("dt 列不允许有重复值，请检查")
        return

    height = kwargs.get("height", 600)
    row_heights = kwargs.get("row_heights", [0.6, 0.1, 0.3])
    title = kwargs.get("title", f"{factor} 可视化")

    chart = czsc.KlineChart(n_rows=3, height=height, row_heights=row_heights, title=title)
    chart.add_kline(df)
    chart.add_sma(df, visible=True, line_width=1)
    chart.add_vol(df, row=2)
    chart.add_scatter_indicator(df["dt"], df[factor], name=factor, row=3, line_width=1.5)

    plotly_config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "toggleSpikelines",
            "select2d",
            "zoomIn2d",
            "zoomOut2d",
            "lasso2d",
            "autoScale2d",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
        ],
    }
    st.plotly_chart(chart.fig, use_container_width=True, config=plotly_config)


def show_code_editor(default: str = "", **kwargs):
    """用户自定义 Python 代码编辑器

    :param default: str, 默认代码
    :param kwargs: dict, 其他参数

        - language: str, 编辑器语言，默认为 "python"
        - use_expander: bool, 是否使用折叠面板，默认为 True
        - expander_title: str, 折叠面板标题，默认为 "PYTHON代码编辑"
        - exec: bool, 是否执行代码，默认为 True
        - theme: str, 编辑器主题，默认为 "gruvbox"
        - keybinding: str, 编辑器快捷键，默认为 "vscode"
        - height: int, 编辑器高度，默认为 550
        - font_size: int, 字体大小，默认为 16
        - show_gutter: bool, 是否显示行号，默认为 True
        - readonly: bool, 是否只读，默认为 False
    """
    if default is None:
        default = """
# 代码示例
import czsc
import pandas as pd
import numpy as np
"""
    try:
        from streamlit_ace import st_ace, THEMES, KEYBINDINGS, LANGUAGES
    except ImportError:
        st.error("请先安装 streamlit-ace 库，执行命令：pip install streamlit-ace")
        return

    default_language = kwargs.get("language", "python")
    default_theme = kwargs.get("theme", "gruvbox")
    default_keybinding = kwargs.get("keybinding", "vscode")

    def __editor():
        c1, c2 = st.columns([10, 1])
        with c2:
            language = c2.selectbox("语言", LANGUAGES, index=LANGUAGES.index(default_language))
            height = c2.number_input("编辑器高度", value=550, min_value=100, max_value=2000, step=50)
            font_size = c2.number_input("字体大小", value=16, min_value=8, max_value=32)
            theme = c2.selectbox("主题", THEMES, index=THEMES.index(default_theme))
            keybinding = c2.selectbox("快捷键", KEYBINDINGS, index=KEYBINDINGS.index(default_keybinding))
            wrap = c2.checkbox("自动换行", value=True)
            show_gutter = c2.checkbox("显示行号", value=True)
            readonly = c2.checkbox("只读模式", value=False)

        with c1:
            _code = st_ace(
                language=language,
                value=default,
                height=height,
                font_size=font_size,
                theme=theme,
                show_gutter=show_gutter,
                keybinding=keybinding,
                markers=None,
                tab_size=4,
                wrap=wrap,
                show_print_margin=False,
                readonly=readonly,
                key="python_editor",
            )
        return _code

    use_expander = kwargs.get("use_expander", True)
    expander_title = kwargs.get("expander_title", "代码编辑器")
    if not use_expander:
        code = __editor()
    else:
        with st.expander(expander_title, expanded=True):
            code = __editor()
    return code


def show_classify(df, col1, col2, n=10, method="cut", **kwargs):
    """显示 col1 对 col2 的分类作用

    :param df: 数据，pd.DataFrame
    :param col1: 分层列
    :param col2: 统计列
    :param n: 分层数量
    :param method: 分层方法，cut 或 qcut
    :param kwargs:

        - show_bar: bool, 是否展示柱状图，默认为 False

    """
    import czsc

    df = df[[col1, col2]].copy()
    if method == "cut":
        df[f"{col1}_分层"] = pd.cut(df[col1], bins=n, duplicates="drop")
    elif method == "qcut":
        df[f"{col1}_分层"] = pd.qcut(df[col1], q=n, duplicates="drop")
    else:
        raise ValueError("method must be 'cut' or 'qcut'")

    dfg = df.groupby(f"{col1}_分层", observed=True)[col2].describe().reset_index()
    dfx = dfg.copy()
    info = (
        f"{col1} 分层对应 {col2} 的均值单调性：:red[{czsc.monotonicity(dfx['mean']):.2%}]； "
        f"最后一层的均值：:red[{dfx['mean'].iloc[-1]:.4f}]；"
        f"第一层的均值：:red[{dfx['mean'].iloc[0]:.4f}]"
    )
    st.markdown(info)

    if kwargs.get("show_bar", False):
        dfx["标记"] = dfx[f"{col1}_分层"].astype(str)
        dfx["text"] = dfx["mean"].apply(lambda x: f"{x:.4f}")
        fig = px.bar(dfx, x="标记", y="mean", text="text", color="mean", color_continuous_scale="RdYlGn_r")
        fig.update_xaxes(title=None)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    dfg = dfg.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    dfg = dfg.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    dfg = dfg.background_gradient(cmap="RdYlGn_r", axis=None, subset=["min", "25%", "50%", "75%", "max"])
    dfg = dfg.format(
        {
            "count": "{:.0f}",
            "mean": "{:.4f}",
            "std": "{:.2%}",
            "min": "{:.4f}",
            "25%": "{:.4f}",
            "50%": "{:.4f}",
            "75%": "{:.4f}",
            "max": "{:.4f}",
        }
    )
    st.dataframe(dfg, use_container_width=True)


def show_corr_graph(df, columns=None, threshold=0.2, **kwargs):
    """显示相关性矩阵的图形

    :param df: pd.DataFrame, 需要计算相关性的数据
    :param columns: list, 需要显示的列名
    :param threshold: float, 相关性阈值
    :param kwargs:

        - method: str, 相关性计算方法，默认为 pearson, 可选 pearson, kendall, spearman
    """
    import networkx as nx
    from czsc.utils.plotly_plot import plot_nx_graph

    method = kwargs.get("method", "pearson")

    if columns is None:
        columns = df.columns

    dfr = df[columns].corr(method=method).round(4)

    # 创建一个无向图
    G = nx.Graph()

    # 添加节点，使用列名作为节点名称
    G.add_nodes_from(dfr.columns)

    # 添加边，只有当相关性超过阈值时
    for i, col1 in enumerate(dfr.columns):
        for j, col2 in enumerate(dfr.columns):
            if i < j:  # 避免重复和自环
                if abs(dfr.iat[i, j]) > threshold:
                    G.add_edge(col1, col2, weight=dfr.iat[i, j])

    fig = plot_nx_graph(G, node_marker_size=15)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("相关性矩阵"):
        # 将 dfr 对角线上的 1 填充为 0
        dfr = dfr.copy().where(~np.eye(dfr.shape[0], dtype=bool))
        dfr["average"] = dfr.sum(axis=1) / (len(columns) - 1)

        dfr = dfr.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.4f}", na_rep="MISS")
        st.dataframe(dfr, use_container_width=True)


def show_df_describe(df: pd.DataFrame):
    """展示 DataFrame 的描述性统计信息

    :param df: pd.DataFrame，必须是 df.describe() 的结果
    """
    quantiles = [x for x in df.columns if "%" in x]
    df = df.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["max", "min"] + quantiles)

    format_dict = {
        "count": "{:.0f}",
        "mean": "{:.4f}",
        "std": "{:.4f}",
        "min": "{:.4f}",
        "max": "{:.4f}",
    }
    for q in quantiles:
        format_dict[q] = "{:.4f}"

    df = df.format(format_dict)
    st.dataframe(df, use_container_width=True)


def show_date_effect(df: pd.DataFrame, ret_col: str, **kwargs):
    """分析日收益数据的日历效应

    :param df: pd.DataFrame, 包含日期的日收益数据
    :param ret_col: str, 收益列名称
    :param kwargs: dict, 其他参数

        - show_weekday: bool, 是否展示星期效应，默认为 True
        - show_month: bool, 是否展示月份效应，默认为 True
        - percentiles: list, 分位数，默认为 [0.1, 0.25, 0.5, 0.75, 0.9]

    """
    show_weekday = kwargs.get("show_weekday", True)
    show_month = kwargs.get("show_month", True)
    percentiles = kwargs.get("percentiles", [0.1, 0.25, 0.5, 0.75, 0.9])

    assert ret_col in df.columns, f"ret_col 必须是 {df.columns} 中的一个"
    assert show_month or show_weekday, "show_month 和 show_weekday 不能同时为 False"

    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy()

    st.write(
        f"交易区间 {df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')}；总天数：{len(df)}"
    )

    if show_weekday:
        st.write("##### 星期效应")
        df["weekday"] = df.index.weekday
        sorted_weekday = sorted(df["weekday"].unique().tolist())
        weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        df["weekday"] = df["weekday"].map(weekday_map)
        sorted_rows = [weekday_map[i] for i in sorted_weekday]

        weekday_effect = df.groupby("weekday")[ret_col].describe(percentiles=percentiles)
        weekday_effect = weekday_effect.loc[sorted_rows]
        show_df_describe(weekday_effect)

    if show_month:
        st.write("##### 月份效应")
        df["month"] = df.index.month
        month_map = {i: f"{i}月" for i in range(1, 13)}
        sorted_month = sorted(df["month"].unique().tolist())
        sorted_rows = [month_map[i] for i in sorted_month]

        df["month"] = df["month"].map(month_map)
        month_effect = df.groupby("month")[ret_col].describe(percentiles=percentiles)
        month_effect = month_effect.loc[sorted_rows]
        show_df_describe(month_effect)

    st.caption("数据说明：count 为样本数量，mean 为均值，std 为标准差，min 为最小值，n% 为分位数，max 为最大值")


def show_normality_check(data: pd.Series, alpha=0.05):
    """展示正态性检验结果
    
    :param data: pd.Series, 需要检验的数据
    :param alpha: float, 显著性水平，默认为 0.05
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    from scipy.stats import shapiro, jarque_bera, kstest
    from scipy.stats import norm
    import statsmodels.api as sm

    clean_data = data.dropna()

    def __metric(s, p):
        m1, m2, m3 = st.columns(3)
        m1.metric(label="统计量", value=f"{s:.3f}", border=False)
        m2.metric(label="P值", value=f"{p:.1%}", border=False)
        m3.metric(label="拒绝原假设", value="True" if p < alpha else "False", border=False)

    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.write("##### :red[Shapiro-Wilk 检验]")
        stat, p_sw = shapiro(clean_data)
        __metric(stat, p_sw)

    with c2.container(border=True):
        st.write("##### :red[Jarque Bera 检验]")
        stat, p_jb = jarque_bera(clean_data)
        __metric(stat, p_jb)

    with c3.container(border=True):
        st.write("##### :red[Kolmogorov-Smirnov 检验]")
        mu, std = np.mean(clean_data), np.std(clean_data)
        stat, p_ks = kstest(clean_data, "norm", args=(mu, std))
        __metric(stat, p_ks)

    plt.rcParams["axes.unicode_minus"] = False
    plt.style.use("ggplot")

    plt.figure(figsize=(20, 5))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

    sns.histplot(clean_data, kde=True, stat="density", ax=ax1)
    x = np.linspace(mu - 4 * std, mu + 4 * std, 100)
    ax1.plot(x, norm.pdf(x, mu, std), "r", lw=2)
    ax1.set_title(f"Histogram => SKEW: {clean_data.skew():.2f}, KURT: {clean_data.kurt():.2f}")
    ax1.legend(["Normal PDF", "Data"])

    sm.qqplot(clean_data, line="45", fit=True, ax=ax2)
    ax2.set_title("Q-Q")
    st.pyplot(fig)
    st.divider()


def show_outsample_by_dailys(df, outsample_sdt1, outsample_sdt2=None):
    """根据日收益数据展示样本内外对比

    :param df: 日收益数据，包含列 ['dt', 'returns']
    :param outsample_sdt1: 样本外开始日期
    :param outsample_sdt2: 实盘开始跟踪的日期，如果为 None，则只展示样本内和样本外两个阶段
    :return: None
    """
    from czsc.eda import cal_yearly_days
    from rs_czsc import daily_performance

    if not ("dt" in df.columns and "returns" in df.columns):
        st.error(f"show_outsample_by_dailys -> 数据格式错误，必须包含列 ['dt', 'returns']; 当前列：{df.columns}")
        return

    df["dt"] = pd.to_datetime(df["dt"])
    yearly_days = cal_yearly_days(df["dt"])
    outsample_sdt1 = pd.to_datetime(outsample_sdt1).strftime("%Y-%m-%d")

    def __show_returns(dfx):
        dfx = dfx.copy()
        stats = daily_performance(dfx["returns"], yearly_days=yearly_days)
        sc1, sc2, sc3 = st.columns(3)

        # 绘制收益指标
        sc1.metric("年化收益率", f"{stats['年化']:.2%}")
        sc1.metric("夏普比率", f"{stats['夏普']:.2f}")
        sc1.metric("新高占比", f"{stats['新高占比']:.2%}")

        sc2.metric("最大回撤", f"{stats['最大回撤']:.2%}")
        sc2.metric("新高间隔", f"{stats['新高间隔']:.0f}")
        sc2.metric("回撤风险", f"{stats['回撤风险']:.3f}")

        sc3.metric("年化波动率", f"{stats['年化波动率']:.2%}")
        sc3.metric("下行波动率", f"{stats['下行波动率']:.2%}")
        sc3.metric("非零覆盖", f"{stats['非零覆盖']:.2%}")

        st.divider()
        dfd = dfx[["dt", "returns"]].copy()
        dfd.set_index("dt", inplace=True)
        st.line_chart(dfd["returns"].cumsum(), color="#B22222", use_container_width=True)

    if outsample_sdt2 is not None:
        outsample_sdt2 = pd.to_datetime(outsample_sdt2).strftime("%Y-%m-%d")

        if outsample_sdt1 >= outsample_sdt2:
            st.error("show_outsample_by_dailys -> 样本外开始日期必须小于实盘开始日期")
            return

        df1 = df[df["dt"] < outsample_sdt1].copy()  # 样本内
        df2 = df[
            (df["dt"] >= outsample_sdt1) & (df["dt"] < outsample_sdt2)
        ].copy()  # 第一段样本外：研究员认为的样本外开始日期
        df3 = df[df["dt"] >= outsample_sdt2].copy()  # 第二段样本外：首次开始实盘跟踪的日期

        c1, c2, c3 = st.columns(3)

        with c1.container(border=True):
            st.caption(f"研究阶段样本内: {df1['dt'].min().strftime('%Y-%m-%d')} ~ {outsample_sdt1}")
            __show_returns(df1)

        with c2.container(border=True):
            st.caption(f"研究阶段样本外: {outsample_sdt1} ~ {df2['dt'].max().strftime('%Y-%m-%d')}")
            __show_returns(df2)

        with c3.container(border=True):
            st.caption(f"系统跟踪样本外: {outsample_sdt2} ~ {df3['dt'].max().strftime('%Y-%m-%d')}")
            __show_returns(df3)

    else:
        df1 = df[df["dt"] < outsample_sdt1].copy()  # 样本内
        df2 = df[df["dt"] >= outsample_sdt1].copy()  # 样本外

        c1, c2 = st.columns(2)
        with c1.container(border=True):
            st.caption(f"样本内: {df1['dt'].min().strftime('%Y-%m-%d')} ~ {outsample_sdt1}")
            __show_returns(df1)

        with c2.container(border=True):
            st.caption(f"样本外: {outsample_sdt1} ~ {df2['dt'].max().strftime('%Y-%m-%d')}")
            __show_returns(df2)


def show_returns_contribution(df, returns=None, max_returns=100):
    """分析子策略对总收益的贡献
    
    :param df: pd.DataFrame, 子策略日收益数据，index 为 datetime, columns 为 子策略名称
    :param returns: list, 子策略名称列表
    :param max_returns: int, 最大展示策略数量
    """
    df = df.copy()
    for dt_col in ['date', 'dt']:
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col])
            df.set_index(dt_col, inplace=True)
    
    if returns is None:
        returns = df.columns.to_list()

    if len(returns) == 1 or len(returns) > max_returns:
        st.warning(f"请选择多个策略进行对比，或者选择少于{max_returns} 个策略; 当前选择 {len(returns)} 个策略")
        return 

    # 计算每个策略的总收益贡献
    total_returns = df[returns].sum(axis=0)
    
    # 创建用于绘图的数据框
    plot_df = pd.DataFrame({
        '策略': total_returns.index,
        '收益贡献': total_returns.values
    })
    plot_df = plot_df.sort_values(by='收益贡献', ascending=False)

    # 创建两列布局
    col1, col2 = st.columns([3, 2])
    
    with col1.container(border=True):
        # 绘制柱状图
        fig_bar = px.bar(plot_df, x='策略', y='收益贡献', 
                        title='收益贡献分析（柱状图）',
                        color='收益贡献',
                        color_continuous_scale='RdYlGn_r',
                        width=600, height=400)
        fig_bar.update_layout(yaxis_title='绝对收益', xaxis_title='策略')
        st.plotly_chart(fig_bar)
        st.caption("柱状图展示每个策略的收益贡献, Y轴为绝对收益大小，X轴为策略名称")
        
    with col2.container(border=True):
        # 绘制饼图，如果收益贡献为负，删除
        plot_df = plot_df[plot_df['收益贡献'] > 0]
        fig_pie = px.pie(plot_df, values='收益贡献', names='策略', 
                        title='盈利贡献分析（饼图）',
                        width=600, height=400)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie)
        st.caption("饼图只展示盈利贡献为正的策略，分析子策略对盈利部分的贡献占比")


def show_symbols_bench(df: pd.DataFrame, **kwargs):
    """展示多个品种的基准收益相关信息

    :param df: pd.DataFrame, 数据源, 包含symbol, dt, price 字段, 其他字段将被忽略
        symbol: 品种代码
        dt: 时间
        price: 交易价格
    :param kwargs: 其他参数
        - use_st_table: bool, 是否使用 st.table 展示相关性矩阵, 默认为 False
    """
    from rs_czsc import daily_performance
    from czsc.eda import cal_yearly_days

    df = df[["symbol", "dt", "price"]].copy()
    df["pct_change"] = df.groupby("symbol")["price"].pct_change()
    df['date'] = df['dt'].dt.date
    dailys = df.groupby(['symbol', 'date'])['pct_change'].sum().reset_index()
    dailys = dailys.pivot(index='date', columns='symbol', values='pct_change')
    dailys = dailys.sort_values(by="date", ascending=True)
    dailys = dailys.fillna(0)

    with st.container(border=True):
        st.markdown("##### 品种等权累计收益&最大回撤")
        dailys['total'] = dailys.mean(axis=1)
        dailys.index = pd.to_datetime(dailys.index)

        yearly_days = cal_yearly_days(dailys.index.to_list())
        stats = daily_performance(dailys['total'].to_list(), yearly_days=yearly_days)

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        c1.metric("年化收益率", f"{stats['年化']:.2%}", border=True)
        c2.metric("夏普比率", f"{stats['夏普']:.2f}", border=True)
        c3.metric("最大回撤", f"{stats['最大回撤']:.2%}", border=True)
        c4.metric("卡玛比率", f"{stats['卡玛']:.2f}", border=True)
        c5.metric("日胜率", f"{stats['日胜率']:.2%}", border=True)
        c6.metric("年化波动率", f"{stats['年化波动率']:.2%}", border=True)
        c7.metric("新高占比", f"{stats['新高占比']:.2%}", border=True, help="新高占比: 新高日占所有交易日的比例")
        c8.metric("新高间隔", f"{stats['新高间隔']}", border=True, help="新高间隔: 相邻新高日之间的最大交易日间隔")

        show_drawdowns(dailys, ret_col='total', sub_title="")

    with st.container(border=True):
        st.markdown("##### 品种间日收益相关性矩阵")
        show_correlation(dailys, use_st_table=kwargs.get("use_st_table", False))


def show_quarterly_effect(returns: pd.Series):
    """展示策略的季节性收益对比

    :param returns: 日收益率序列，index 为日期
    """
    import plotly.express as px
    from czsc.eda import cal_yearly_days
    from rs_czsc import daily_performance

    returns.index = pd.to_datetime(returns.index)
    yearly_days = cal_yearly_days(returns.index.to_list())

    # 按4个季度划分数据为 s1，s2，s3，s4，分别计算每个季度的统计指标
    s1 = returns[returns.index.quarter == 1]
    s2 = returns[returns.index.quarter == 2]
    s3 = returns[returns.index.quarter == 3]
    s4 = returns[returns.index.quarter == 4]

    def __show_quarter_stats(s: pd.Series):
        stats = daily_performance(s.to_list(), yearly_days=yearly_days)
        st.markdown(f"总交易天数: `{len(s)}天` \
                    | 年化: `{stats['年化']:.2%}` \
                    | 夏普: `{stats['夏普']:.2f}` \
                    | 最大回撤: `{stats['最大回撤']:.2%}` \
                    | 卡玛: `{stats['卡玛']:.2f}` \
                    | 年化波动率: `{stats['年化波动率']:.2%}`")
        
        # 用 plotly 绘制累计收益率曲线, 用 数字作为index，方便对比
        fig = px.line(s.cumsum(), x=list(range(len(s))), y=s.cumsum().values, title="")
        fig.update_layout(xaxis_title="交易天数", yaxis_title="累计收益率", margin=dict(l=0, r=0, t=0, b=0))

        # 按年分组，绘制矩形覆盖
        years = s.index.year.unique()
        colors = ['rgba(102, 255, 178, 0.1)', 'rgba(102, 178, 255, 0.1)']  # 薄荷绿和天蓝色，半透明
        shapes = []
        for i, year in enumerate(years):
            # 获取该年的第一个和最后一个交易日在数字索引中的位置
            year_data = s[s.index.year == year]
            start_idx = s.index.get_indexer([year_data.index[0]])[0]
            end_idx = s.index.get_indexer([year_data.index[-1]])[0]
            
            # 添加矩形
            shapes.append(dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start_idx,
                y0=0,
                x1=end_idx,
                y1=1,
                fillcolor=colors[i % len(colors)],
                opacity=0.5,
                layer="below",
                line_width=0,
            ))
        
        # 更新图表布局，添加矩形
        fig.update_layout(shapes=shapes)
        
        # 添加年份标签
        annotations = []
        for i, year in enumerate(years):
            year_data = s[s.index.year == year]
            mid_idx = s.index.get_indexer([year_data.index[len(year_data)//2]])[0]
            
            annotations.append(dict(
                x=mid_idx,
                y=0.95,
                xref="x",
                yref="paper",
                text=str(year),
                showarrow=False,
                font=dict(size=14)
            ))
            
        fig.update_layout(annotations=annotations)
        
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("##### :red[第一季度]")
        __show_quarter_stats(s1)

    with c2.container(border=True):
        st.markdown("##### :red[第二季度]")
        __show_quarter_stats(s2)

    c3, c4 = st.columns(2)
    with c3.container(border=True):
        st.markdown("##### :red[第三季度]")
        __show_quarter_stats(s3)

    with c4.container(border=True):
        st.markdown("##### :red[第四季度]")
        __show_quarter_stats(s4)


def show_cta_periods_classify(df: pd.DataFrame, **kwargs):
    """展示不同市场环境下的策略表现

    :param df: 标准K线数据，
            必须包含 dt, symbol, open, close, high, low, vol, amount, weight, price 列; 
            如果 price 列不存在，则使用 close 列
    :param kwargs: 

        - fee_rate: 手续费率
        - digits: 小数位数
        - weight_type: 权重类型
        - q1: 最容易赚钱的笔的占比, mark_cta_periods 函数的参数
        - q2: 最难赚钱的笔的占比, mark_cta_periods 函数的参数
    """
    from rs_czsc import WeightBacktest
    from czsc.eda import mark_cta_periods
    # from czsc.utils.st_components import show_daily_return, show_cumulative_returns

    fee_rate = kwargs.get('fee_rate', 0.00)
    digits = kwargs.get('digits', 1)
    weight_type = kwargs.get('weight_type', 'ts')
    q1 = kwargs.get('q1', 0.15)
    q2 = kwargs.get('q2', 0.4)

    dfs = mark_cta_periods(df.copy(), freq='日线', verbose=False, q1=q1, q2=q2)

    if 'price' not in dfs.columns:
        dfs['price'] = dfs['close']

    p1 = dfs['is_best_period'].value_counts()[1] / len(dfs)
    p2 = dfs['is_worst_period'].value_counts()[1] / len(dfs)
    st.markdown(f"趋势行情占比：:red[{p1:.2%}]；震荡行情占比：:blue[{p2:.2%}]")
    st.caption(f"mark_cta_periods 参数：q1={q1}, q2={q2}; WeightBacktest 参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")

    wb = WeightBacktest(dfs[['dt', 'symbol', 'weight', 'price']], fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    df1 = dfs.copy()
    df1['weight'] = np.where(df1['is_best_period'], df1['weight'], 0)
    df1 = df1[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb1 = WeightBacktest(df1, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    df2 = dfs.copy()
    df2['weight'] = np.where(df2['is_worst_period'], df2['weight'], 0)
    df2 = df2[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb2 = WeightBacktest(df2, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    classify = ['原始策略', '趋势行情', '震荡行情']
    # stats = pd.DataFrame([wb.stats, wb1.stats, wb2.stats])
    # stats['classify'] = classify
    # st.dataframe(stats)

    dailys = []
    for wb_, classify_ in zip([wb, wb1, wb2], classify):
        df_daily = wb_.daily_return.copy()
        df_daily = df_daily[['date', 'total']].copy().reset_index(drop=True)
        df_daily['classify'] = classify_
        dailys.append(df_daily)
    dailys = pd.concat(dailys, ignore_index=True)
    dailys['date'] = pd.to_datetime(dailys['date'])
    dailys = pd.pivot_table(dailys, index='date', columns='classify', values='total')
    show_daily_return(dailys, stat_hold_days=False)
    # show_cumulative_returns(dailys, fig_title="")


def show_volatility_classify(df: pd.DataFrame, kind='ts', **kwargs):
    """【后验，有未来信息，不能用于实盘】波动率分类回测

    :param df: 标准K线数据，
            必须包含 dt, symbol, open, close, high, low, vol, amount, weight, price 列; 
            如果 price 列不存在，则使用 close 列
    :param kwargs: 

        - fee_rate: 手续费率，WeightBacktest 的参数
        - digits: 小数位数，WeightBacktest 的参数
        - weight_type: 权重类型，'ts' 表示时序，'cs' 表示截面，WeightBacktest 的参数
        - kind: 波动率分类方式，'ts' 表示时序，'cs' 表示截面，mark_volatility 函数的参数
        - window: 计算波动率的窗口，mark_volatility 函数的参数
        - q1: 波动率最大的K线数量占比，默认 0.2，mark_volatility 函数的参数
        - q2: 波动率最小的K线数量占比，默认 0.2，mark_volatility 函数的参数

    :return: None

    ==============
    example
    ==============
    >>> show_volatility_classify(df, fee_rate=0.00, digits=1, weight_type='ts', 
    >>>                          kind='ts', window=20, q1=0.2, q2=0.2 )
    """
    from rs_czsc import WeightBacktest
    from czsc.eda import mark_volatility

    fee_rate = kwargs.get('fee_rate', 0.00)
    digits = kwargs.get('digits', 1)
    weight_type = kwargs.get('weight_type', 'ts')
    window = kwargs.get('window', 20)
    q1 = kwargs.get('q1', 0.2)
    q2 = kwargs.get('q2', 0.2)

    dfs = mark_volatility(df.copy(), kind=kind, verbose=False, q1=q1, q2=q2, window=window)

    if 'price' not in dfs.columns:
        dfs['price'] = dfs['close']

    p1 = dfs['is_max_volatility'].value_counts()[1] / len(dfs)
    p2 = dfs['is_min_volatility'].value_counts()[1] / len(dfs)
    st.markdown(f"波动率最大行情占比：:red[{p1:.2%}]；波动率最小行情占比：:blue[{p2:.2%}]")
    st.caption(f"mark_volatility 参数：kind={kind}, window={window}, q1={q1}, q2={q2}; WeightBacktest 参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")

    wb = WeightBacktest(dfs[['dt', 'symbol', 'weight', 'price']], fee_rate=fee_rate, digits=digits, 
                        weight_type=weight_type)

    df1 = dfs.copy()
    df1['weight'] = np.where(df1['is_max_volatility'], df1['weight'], 0)
    df1 = df1[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb1 = WeightBacktest(df1, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    df2 = dfs.copy()
    df2['weight'] = np.where(df2['is_min_volatility'], df2['weight'], 0)
    df2 = df2[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb2 = WeightBacktest(df2, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    classify = ['原始策略', '波动率大', '波动率小']

    dailys = []
    for wb_, classify_ in zip([wb, wb1, wb2], classify):
        df_daily = wb_.daily_return.copy()
        df_daily = df_daily[['date', 'total']].copy().reset_index(drop=True)
        df_daily['classify'] = classify_
        dailys.append(df_daily)
    dailys = pd.concat(dailys, ignore_index=True)
    dailys['date'] = pd.to_datetime(dailys['date'])
    dailys = pd.pivot_table(dailys, index='date', columns='classify', values='total')
    show_daily_return(dailys, stat_hold_days=False)


def show_portfolio(df: pd.DataFrame, portfolio: str, benchmark: Optional[str] = None, **kwargs):
    """分析组合日收益绩效

    :param df: 日收益数据，包含 dt, portfolio, benchmark 三列, 其中 dt 为日期, portfolio 为组合收益, benchmark 为基准收益
    :param portfolio: 组合名称
    :param benchmark: 基准名称, 可选
    :param show_detail: 是否展示详情, 可选, 默认展示
    """
    from rs_czsc import daily_performance
    from czsc.eda import cal_yearly_days

    if benchmark is not None:
        df['alpha'] = df[portfolio] - df[benchmark]
        df = df[['dt', portfolio, benchmark, 'alpha']].copy()
    else:
        df = df[['dt', portfolio]].copy()

    stats = daily_performance(df[portfolio].to_list())

    with st.container(border=True):
        st.subheader("组合基础表现", divider="rainbow")
        m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
        m1.metric("年化收益", f"{stats['年化']:.2%}")
        m2.metric("最大回撤", f"{stats['最大回撤']:.2%}")
        m3.metric("夏普比率", f"{stats['夏普']:.2f}")
        m4.metric("卡玛比率", f"{stats['卡玛']:.2f}")
        m5.metric("年化波动率", f"{stats['年化波动率']:.2%}")
        m6.metric("日胜率", f"{stats['日胜率']:.2%}")
        m7.metric("新高间隔", f"{stats['新高间隔']}")
        m8.metric("新高占比", f"{stats['新高占比']:.2%}")
        show_drawdowns(df.copy(), ret_col=portfolio, sub_title="")

    show_detail = kwargs.get("show_detail", True)
    if not show_detail:
        return

    with st.container(border=True):
        st.subheader("组合绩效详情", divider="rainbow")
        if benchmark is not None:
            tabs = st.tabs(["年度绩效", "季度效应", "月度绩效", "超额分析"])
        else:
            tabs = st.tabs(["年度绩效", "季度效应", "月度绩效"])

        daily = df.copy().set_index('dt')
        with tabs[0]:
            show_yearly_stats(daily, ret_col=portfolio, sub_title="")

        with tabs[1]:
            show_quarterly_effect(daily[portfolio])

        with tabs[2]:
            show_monthly_return(daily, ret_col=portfolio, sub_title="")

        if benchmark is not None:
            with tabs[3]:
                yearly_days = cal_yearly_days(daily.index.to_list())
                show_daily_return(daily, stat_hold_days=False, plot_cumsum=True, sub_title="", yearly_days=yearly_days)


def show_turnover_rate(df: pd.DataFrame):
    """显示换手率变化
    
    :param df: 权重数据，必须包含 dt, symbol, weight 三列, 其他列忽略
    """
    import plotly.express as px
    from czsc.eda import turnover_rate

    res = turnover_rate(df, verbose=True)
    dfc = res['日换手详情']  # 两列：dt, change
    dfc['dt'] = pd.to_datetime(dfc['dt'])

    # 最近30天换手率
    _sdt_30 = dfc['dt'].max() - pd.Timedelta(days=30)
    _dfc = dfc[dfc['dt'] >= _sdt_30]

    # 最近一年换手率
    _sdt_year = dfc['dt'].max() - pd.Timedelta(days=365)
    _dfy = dfc[dfc['dt'] >= _sdt_year]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("单边换手率", f"{res['单边换手率']:.2f}")
    m2.metric("日均换手率", f"{res['日均换手率']:.2%}")
    m3.metric("最大单日换手率", f"{res['最大单日换手率']:.2%}")
    m4.metric("最小单日换手率", f"{res['最小单日换手率']:.2%}")
    m5.metric("最近30天换手率", f"{_dfc['change'].sum():.2f}", help=f"最近30天换手率，自{_sdt_30}以来")
    m6.metric("最近一年换手率", f"{_dfy['change'].sum():.2f}", help=f"最近一年换手率，自{_sdt_year}以来")

    p1, p2, p3 = st.columns([2, 3, 1])
    # 日换手的累计变化（X轴不显示）
    df_daily = dfc.copy()
    df_daily['change'] = df_daily['change'].cumsum()
    fig = px.line(df_daily, x='dt', y='change', title='日换手累计曲线')
    fig.update_xaxes(title_text='')
    p1.plotly_chart(fig, use_container_width=True)

    # 月换手的柱状图
    df_monthly = dfc.copy()
    df_monthly = df_monthly.set_index('dt').resample('M').sum().reset_index()
    fig = px.bar(df_monthly, x='dt', y='change', title='月换手变化')
    fig.update_xaxes(title_text='')
    p2.plotly_chart(fig, use_container_width=True)

    # 年换手的柱状图
    df_yearly = dfc.copy()
    df_yearly = df_yearly.set_index('dt').resample('Y').sum().reset_index()
    df_yearly['dt'] = df_yearly['dt'].dt.strftime('%Y')
    df_yearly['change'] = df_yearly['change'].round(0)
    fig = px.bar(df_yearly, x='dt', y='change', title='年换手变化', hover_data=['change'])
    fig.update_xaxes(title_text='')
    p3.plotly_chart(fig, use_container_width=True)

    st.caption("说明：以单边换手率计算")


def show_describe(df: pd.DataFrame, **kwargs):
    """展示 DataFrame 的描述性统计信息

    :param df: pd.DataFrame, 数据框
    """
    columns = kwargs.get('columns', None)
    percentiles = kwargs.get('percentiles', [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
    digits = kwargs.get('digits', 2)

    columns = columns or df.columns
    df_raw = df[columns].copy()

    df = df_raw.describe(percentiles=percentiles).T
    df['偏度'] = df_raw.skew()
    df['峰度'] = df_raw.kurt()

    quantiles = [x for x in df.columns if "%" in x]
    df = df.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["max", "min"] + quantiles)
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["偏度"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["峰度"])

    format_dict = {
        "count": "{:.0f}",
        "mean": f"{{:.{digits}f}}",
        "std": f"{{:.{digits}f}}",
        "min": f"{{:.{digits}f}}",
        "max": f"{{:.{digits}f}}",
        "偏度": f"{{:.{digits}f}}",
        "峰度": f"{{:.{digits}f}}",
    }
    for q in quantiles:
        format_dict[q] = f"{{:.{digits}f}}"
    
    df = df.format(format_dict)
    st.dataframe(df, use_container_width=True)
    st.caption("说明：描述性统计中 count 为非空值的个数，mean 为均值，std 为标准差，min 为最小值，max 为最大值，N% 为分位数。")


def show_event_features(df, event_col, event=None, features=None, **kwargs):
    """分析指定事件发生前后的走势特征统计量
    
    :param df: 数据框, 包含事件发生时间、事件名称、价格
    :param event_col: 事件因子, 如'event'
    :param event: 事件名称, 如'事件1'
    :param features: 特征列表, 如['B13收益', 'B13波动', 'F13收益', 'F13波动']，使用 make_price_features 计算的特征
    :param kwargs: 其他参数
        - percentiles: 百分位数, 默认[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
    """
    import re
    percentiles = kwargs.get('percentiles', [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])

    df = df.copy()
    available_features = [f for f in df.columns if re.match(r'B\d{2}收益|B\d{2}波动|F\d{2}收益|F\d{2}波动', f)]
    features = features or available_features
    features = [f for f in features if f in available_features]

    df[event_col] = df[event_col].astype(str)
    if event == "基准":    # 基准事件，不进行过滤
        df_i = df.copy()
    else:
        df_i = df[df[event_col] == event].copy()
    
    df_i = df_i[features + [event_col]]
    st.divider()
    st.subheader(f"事件：{event}", divider='rainbow')

    ret_future_features = [f for f in features if re.match(r'F\d{2}收益', f)]
    ret_before_features = [f for f in features if re.match(r'B\d{2}收益', f)]
    vol_future_features = [f for f in features if re.match(r'F\d{2}波动', f)]
    vol_before_features = [f for f in features if re.match(r'B\d{2}波动', f)]
    tabs = st.tabs(["BEFORE收益特征", "FUTURE收益特征", "BEFORE波动特征", "FUTURE波动特征"])

    with tabs[0]:
        st.markdown("###### 事件发生前的收益特征")
        show_describe(df_i, columns=ret_before_features, percentiles=percentiles)

    with tabs[1]:
        st.markdown("###### 事件发生后的收益特征")
        show_describe(df_i, columns=ret_future_features, percentiles=percentiles)

    with tabs[2]:
        st.markdown("###### 事件发生前的波动特征")
        show_describe(df_i, columns=vol_before_features, percentiles=percentiles)

    with tabs[3]:
        st.markdown("###### 事件发生后的波动特征")
        show_describe(df_i, columns=vol_future_features, percentiles=percentiles)

    c1, c2 = st.columns([2, 2])
    with c1:
        st.divider()
        st.markdown("###### 特征统计量说明")
        st.caption("偏度指标：衡量数据分布的偏斜程度，正数向右偏，负数向左偏；标准正态分布偏度为0")
        st.caption("峰度指标：衡量数据分布的尖锐程度，正数更尖锐，负数更平缓；标准正态分布峰度为3")

    with c2:
        st.divider()
        st.markdown("###### 特征计算说明")
        st.caption("BX收益：事件发生前N根K线的收益，单位: BP，如：B13收益 = 过去13根K线收益 * 10000")
        st.caption("BX波动：事件发生前N根K线的波动, std / price, 如：B13波动 = 过去13根K线STD波动率 / 最新一根K线收盘价")
        st.caption("FX收益：事件发生后N根K线的收益，单位: BP，如：F13收益 = 未来13根K线收益 * 10000")
        st.caption("FX波动：事件发生后N根K线的波动, std / price, 如：F13波动 = 未来13根K线STD波动率 / 未来第13根K线收盘价")


def show_stats_compare(df: pd.DataFrame, **kwargs):
    """显示多组策略回测的绩效对比

    :param df: 策略回测结果, WeightBacktest 的 stats 数据汇总成的 DataFrame，用 name 列区分不同的策略
    """
    if 'name' in df.columns:
        df.set_index("name", inplace=True)

    # # 收益指标
    # cols_x = ['绝对收益', '年化', '夏普', '单笔收益', '盈亏平衡点', '日胜率', '日盈亏比', '日赢面']
    # # 风险指标
    # cols_y = ['最大回撤', '卡玛', '年化波动率', '下行波动率', '新高间隔', '新高占比', '回撤风险','波动比']
    # # 特质指标
    # cols_z = ["开始日期", "结束日期", '品种数量', '持仓K线数', '多头占比', '空头占比', '交易胜率']

    df = df[['绝对收益', '年化', '夏普', '最大回撤', '卡玛', '年化波动率', '下行波动率', '非零覆盖', '新高间隔', '新高占比', '回撤风险', 
               '交易胜率', '单笔收益', '持仓K线数', '多头占比', '空头占比', '波动比', '盈亏平衡点', '日胜率', '日盈亏比', 
               '日赢面', '品种数量', "开始日期", "结束日期"]].copy()

    df = df.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年化"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["绝对收益"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["盈亏平衡点"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["夏普"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["最大回撤"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["卡玛"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["年化波动率"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["下行波动率"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日胜率"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日盈亏比"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日赢面"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["非零覆盖"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["新高间隔"])
    df = df.background_gradient(cmap="RdYlGn", axis=None, subset=["回撤风险"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["新高占比"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["品种数量"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["波动比"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["多头占比"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["空头占比"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["交易胜率"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["单笔收益"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["持仓K线数"])

    df = df.format(
        {
            "盈亏平衡点": "{:.2f}",
            "年化波动率": "{:.2%}",
            "下行波动率": "{:.2%}",
            "最大回撤": "{:.2%}",
            "卡玛": "{:.2f}",
            "年化": "{:.2%}",
            "夏普": "{:.2f}",
            "非零覆盖": "{:.2%}",
            "绝对收益": "{:.2%}",
            "日胜率": "{:.2%}",
            "日盈亏比": "{:.2f}",
            "日赢面": "{:.2%}",
            "新高间隔": "{:.2f}",
            "回撤风险": "{:.2f}",
            "新高占比": "{:.2%}",
            "品种数量": "{:.0f}",
            "波动比": "{:.2f}",
            "多头占比": "{:.2%}",
            "空头占比": "{:.2%}",
            "交易胜率": "{:.2%}",
            "单笔收益": "{:.2f}",
            "持仓K线数": "{:.2f}",
        }
    )
    st.dataframe(df, use_container_width=True)


def show_symbol_penalty(df: pd.DataFrame, n=3, **kwargs):
    """依次删除策略收益最高的N个品种，对比收益变化

    :param df: 策略权重数据
    :param n: 删除的品种数量
    :return: None 
    """
    from rs_czsc import WeightBacktest

    digits = kwargs.get('digits', 2)
    fee_rate = kwargs.get('fee_rate', 0.0)
    weight_type = kwargs.get('weight_type', 'ts')
    yearly_days = kwargs.get('yearly_days', 252)

    n = min(n, df['symbol'].nunique() - 1)
    dfw = df[['dt', 'symbol', 'weight', 'price']].copy()
    wb_map = {}
    wb1 = WeightBacktest(dfw.copy(), digits=digits, fee_rate=fee_rate, weight_type=weight_type, yearly_days=yearly_days)
    wb_map['原始策略'] = wb1

    for i in list(range(1, n+1)):
        top_symbols = wb1.get_top_symbols(i, kind='profit')
        dfw1 = dfw[~dfw['symbol'].isin(top_symbols)].copy().reset_index(drop=True)
        wb2 = WeightBacktest(dfw1.copy(), digits=digits, fee_rate=fee_rate, weight_type=weight_type, yearly_days=yearly_days)
        wb_map[f"删除：{';'.join(top_symbols)}"] = wb2

    dfs = []
    dailys = []
    for k, wb in wb_map.items():
        s = wb.stats.copy()
        s['name'] = k
        dfs.append(s)

        d = wb.daily_return.copy()
        d = d[['date', 'total']].copy()
        d['name'] = k
        dailys.append(d)
    
    dfd = pd.concat(dailys, ignore_index=True)
    dfd['date'] = pd.to_datetime(dfd['date'])
    dfd = pd.pivot_table(dfd, index='date', columns='name', values='total', aggfunc='sum')
    show_cumulative_returns(dfd, fig_title="删除表现最佳品种后的累计收益对比")

    dfs = pd.DataFrame(dfs)
    show_stats_compare(dfs)

