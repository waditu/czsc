import czsc
import hashlib
import optuna
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import statsmodels.api as sm
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression


def show_daily_return(df: pd.DataFrame, **kwargs):
    """用 streamlit 展示日收益

    :param df: pd.DataFrame，数据源
    :param kwargs:

        - sub_title: str，标题
        - stat_hold_days: bool，是否展示持有日绩效指标，默认为 True
        - legend_only_cols: list，仅在图例中展示的列名
        - use_st_table: bool，是否使用 st.table 展示绩效指标，默认为 False
        - plot_cumsum: bool，是否展示日收益累计曲线，默认为 True

    """
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"

    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    def _stats(df_, type_="持有日"):
        df_ = df_.copy()
        stats = []
        for col in df_.columns:
            if type_ == "持有日":
                col_stats = czsc.daily_performance([x for x in df_[col] if x != 0])
            else:
                assert type_ == "交易日", "type_ 参数必须是 持有日 或 交易日"
                col_stats = czsc.daily_performance(df_[col])
            col_stats["日收益名称"] = col
            stats.append(col_stats)

        stats = pd.DataFrame(stats).set_index("日收益名称")
        stats = stats.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年化"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["绝对收益"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["夏普"])
        stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["最大回撤"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["卡玛"])
        stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["年化波动率"])
        stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["盈亏平衡点"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日胜率"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["非零覆盖"])
        stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["新高间隔"])
        stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["新高占比"])
        stats = stats.format(
            {
                "盈亏平衡点": "{:.2f}",
                "年化波动率": "{:.2%}",
                "最大回撤": "{:.2%}",
                "卡玛": "{:.2f}",
                "年化": "{:.2%}",
                "夏普": "{:.2f}",
                "非零覆盖": "{:.2%}",
                "绝对收益": "{:.2%}",
                "日胜率": "{:.2%}",
                "新高间隔": "{:.2f}",
                "新高占比": "{:.2%}",
            }
        )
        return stats

    use_st_table = kwargs.get("use_st_table", False)

    with st.container():
        sub_title = kwargs.get("sub_title", "")
        if sub_title:
            st.subheader(sub_title, divider="rainbow")

        with st.expander("交易日绩效指标", expanded=True):
            if use_st_table:
                st.table(_stats(df, type_="交易日"))
            else:
                st.dataframe(_stats(df, type_="交易日"), use_container_width=True)

        if kwargs.get("stat_hold_days", True):
            with st.expander("持有日绩效指标", expanded=False):
                st.dataframe(_stats(df, type_="持有日"), use_container_width=True)

        if kwargs.get("plot_cumsum", True):
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


def show_monthly_return(df, ret_col="total", sub_title="月度累计收益", **kwargs):
    """展示指定列的月度累计收益

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param title: str，标题
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
        st.subheader(sub_title, divider="rainbow")

    monthly = df[[ret_col]].resample("ME").sum()
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly = monthly.pivot_table(index="year", columns="month", values=ret_col)
    month_cols = [f"{x}月" for x in monthly.columns]
    monthly.columns = month_cols
    monthly["年收益"] = monthly.sum(axis=1)

    monthly = monthly.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=month_cols)
    monthly = monthly.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年收益"])
    monthly = monthly.format("{:.2%}", na_rep="-")

    st.dataframe(monthly, use_container_width=True)


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
    dfr["average"] = (dfr.sum(axis=1) - 1) / (len(cols) - 1)
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
    """
    dfc, res = czsc.cross_sectional_ic(df, x_col=x_col, y_col=y_col, dt_col="dt", method=method)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
    col1.metric("IC均值", res["IC均值"])
    col1.metric("IC标准差", res["IC标准差"])
    col2.metric("ICIR", res["ICIR"])
    col2.metric("IC胜率", res["IC胜率"])
    col3.metric("IC绝对值>2%占比", res["IC绝对值>2%占比"])
    col3.metric("品种数量", df["symbol"].nunique())

    dfc[["year", "month"]] = dfc.dt.apply(lambda x: pd.Series([x.year, x.month]))
    dfm = dfc.groupby(["year", "month"]).agg({"ic": "mean"}).reset_index()
    dfm = pd.pivot_table(dfm, index="year", columns="month", values="ic")

    col4.write("月度IC分析结果：")
    col4.dataframe(
        dfm.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.4f}", na_rep="MISS"),
        use_container_width=True,
    )

    if kwargs.get("show_factor_histgram", False):
        fig = px.histogram(df, x=x_col, marginal="box", title="因子数据分布图")
        st.plotly_chart(fig, use_container_width=True)


def show_factor_returns(df, x_col, y_col):
    """使用 streamlit 展示因子收益率

    :param df: pd.DataFrame，数据源
    :param x_col: str，因子列名
    :param y_col: str，收益列名
    """
    assert "dt" in df.columns, "时间列必须为 dt"

    res = []
    for dt, dfg in df.groupby("dt"):
        dfg = dfg.copy().dropna(subset=[x_col, y_col])
        X = dfg[x_col].values.reshape(-1, 1)
        y = dfg[y_col].values.reshape(-1, 1)
        model = LinearRegression(fit_intercept=False).fit(X, y)
        res.append([dt, model.coef_[0][0]])

    res = pd.DataFrame(res, columns=["dt", "因子收益率"])
    res["dt"] = pd.to_datetime(res["dt"])

    col1, col2 = st.columns(2)
    fig = px.bar(res, x="dt", y="因子收益率", title="因子逐K收益率")
    col1.plotly_chart(fig, use_container_width=True)

    res["因子累计收益率"] = res["因子收益率"].cumsum()
    fig = px.line(res, x="dt", y="因子累计收益率", title="因子累计收益率")
    col2.plotly_chart(fig, use_container_width=True)


def show_factor_layering(df, x_col, y_col="n1b", **kwargs):
    """使用 streamlit 绘制因子截面分层收益率图

    :param df: 因子数据
    :param x_col: 因子列名
    :param y_col: 收益列名
    :param kwargs:

        - n: 分层数量，默认为10
        - long: 多头组合，例如 "第10层"
        - short: 空头组合，例如 "第01层"

    """
    n = kwargs.get("n", 10)
    if df[y_col].max() > 100:  # 收益率单位为BP, 转换为万分之一
        df[y_col] = df[y_col] / 10000

    df = czsc.feture_cross_layering(df, x_col, n=n)

    mr = df.groupby(["dt", f"{x_col}分层"])[y_col].mean().reset_index()
    mrr = mr.pivot(index="dt", columns=f"{x_col}分层", values=y_col).fillna(0)

    tabs = st.tabs(["分层收益率", "多空组合"])
    with tabs[0]:
        czsc.show_daily_return(mrr)

    with tabs[1]:
        layering_cols = mrr.columns.to_list()
        with st.form(key="factor_form"):
            col1, col2 = st.columns(2)
            long = col1.multiselect("多头组合", layering_cols, default=[], key="factor_long")
            short = col2.multiselect("空头组合", layering_cols, default=[], key="factor_short")
            submit = st.form_submit_button("多空组合快速测试")

        if not submit:
            st.warning("请设置多空组合")
            st.stop()

        dfr = mrr.copy()
        dfr["多头"] = dfr[long].mean(axis=1)
        dfr["空头"] = -dfr[short].mean(axis=1)
        dfr["多空"] = (dfr["多头"] + dfr["空头"]) / 2
        czsc.show_daily_return(dfr[["多头", "空头", "多空"]])


def show_symbol_factor_layering(df, x_col, y_col="n1b", **kwargs):
    """使用 streamlit 绘制单个标的上的因子分层收益率图

    :param df: 因子数据，必须包含 dt, x_col, y_col 列，其中 dt 为日期，x_col 为因子值，y_col 为收益率，数据样例：

        ===================  ============  ============
        dt                      intercept     n1b
        ===================  ============  ============
        2017-01-03 00:00:00   0             0.00716081
        2017-01-04 00:00:00  -0.00154541    0.000250816
        2017-01-05 00:00:00   0.000628884  -0.0062695
        2017-01-06 00:00:00  -0.00681021    0.00334212
        2017-01-09 00:00:00   0.00301077   -0.00182963
        ===================  ============  ============

    :param x_col: 因子列名
    :param y_col: 收益列名
    :param kwargs:

        - n: 分层数量，默认为10

    """
    df = df.copy()
    n = kwargs.get("n", 10)
    if df[y_col].max() > 100:  # 如果收益率单位为BP, 转换为万分之一
        df[y_col] = df[y_col] / 10000
    if df[x_col].nunique() < n * 2:
        st.error(f"因子值数量小于{n*2}，无法进行分层")

    if f"{x_col}分层" not in df.columns:
        czsc.normalize_ts_feature(df, x_col, n=n)

    for i in range(n):
        df[f"第{str(i+1).zfill(2)}层"] = np.where(df[f"{x_col}分层"] == f"第{str(i+1).zfill(2)}层", df[y_col], 0)

    layering_cols = [f"第{str(i).zfill(2)}层" for i in range(1, n + 1)]
    mrr = df[["dt"] + layering_cols].copy()
    mrr.set_index("dt", inplace=True)

    tabs = st.tabs(["分层收益率", "多空组合"])

    with tabs[0]:
        show_daily_return(mrr, stat_hold_days=False)

    with tabs[1]:
        col1, col2 = st.columns(2)
        long = col1.multiselect("多头组合", layering_cols, default=["第02层"], key="symbol_factor_long")
        short = col2.multiselect("空头组合", layering_cols, default=["第01层"], key="symbol_factor_short")
        dfr = mrr.copy()
        dfr["多头"] = dfr[long].sum(axis=1)
        dfr["空头"] = -dfr[short].sum(axis=1)
        dfr["多空"] = dfr["多头"] + dfr["空头"]
        show_daily_return(dfr[["多头", "空头", "多空"]])


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

    """
    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("show_weight_backtest :: 持仓权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    wb = czsc.WeightBacktest(dfw, fee_rate=fee / 10000, digits=digits)
    stat = wb.results["绩效评价"]

    st.divider()
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
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
    st.divider()

    dret = wb.results["品种等权日收益"].copy()
    dret.index = pd.to_datetime(dret.index)
    show_daily_return(dret, legend_only_cols=dfw["symbol"].unique().tolist(), **kwargs)

    if kwargs.get("show_drawdowns", False):
        show_drawdowns(dret, ret_col="total", sub_title="")

    if kwargs.get("show_backtest_detail", False):
        c1, c2 = st.columns([1, 1])
        with c1.expander("品种等权日收益", expanded=False):
            df_ = wb.results["品种等权日收益"].copy()
            st.dataframe(df_.style.background_gradient(cmap="RdYlGn_r").format("{:.2%}"), use_container_width=True)

        with c2.expander("查看开平交易对", expanded=False):
            dfp = pd.concat([v["pairs"] for k, v in wb.results.items() if k in wb.symbols], ignore_index=True)
            st.dataframe(dfp, use_container_width=True)

    if kwargs.get("show_splited_daily", False):
        with st.expander("品种等权日收益分段表现", expanded=False):
            show_splited_daily(dret[["total"]].copy(), ret_col="total")

    if kwargs.get("show_yearly_stats", False):
        with st.expander("年度绩效指标", expanded=False):
            show_yearly_stats(dret, ret_col="total")

    if kwargs.get("show_monthly_return", False):
        with st.expander("月度累计收益", expanded=False):
            show_monthly_return(dret, ret_col="total", sub_title="")

    return wb


def show_splited_daily(df, ret_col, **kwargs):
    """展示分段日收益表现

    :param df: pd.DataFrame
    :param ret_col: str, df 中的列名，指定收益列
    :param kwargs:

        sub_title: str, 子标题

    """
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

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
        row = czsc.daily_performance(df1[ret_col])
        row["开始日期"] = sdt.strftime("%Y-%m-%d")
        row["结束日期"] = last_dt.strftime("%Y-%m-%d")
        row["收益名称"] = name
        # row['绝对收益'] = df1[ret_col].sum()
        rows.append(row)
    dfv = pd.DataFrame(rows).set_index("收益名称")
    cols = [
        "开始日期",
        "结束日期",
        "绝对收益",
        "年化",
        "夏普",
        "最大回撤",
        "卡玛",
        "年化波动率",
        "非零覆盖",
        "日胜率",
        "盈亏平衡点",
    ]
    dfv = dfv[cols].copy()

    dfv = dfv.style.background_gradient(cmap="RdYlGn_r", subset=["绝对收益"])
    dfv = dfv.background_gradient(cmap="RdYlGn_r", subset=["年化"])
    dfv = dfv.background_gradient(cmap="RdYlGn_r", subset=["夏普"])
    dfv = dfv.background_gradient(cmap="RdYlGn", subset=["最大回撤"])
    dfv = dfv.background_gradient(cmap="RdYlGn_r", subset=["卡玛"])
    dfv = dfv.background_gradient(cmap="RdYlGn", subset=["年化波动率"])
    dfv = dfv.background_gradient(cmap="RdYlGn", subset=["盈亏平衡点"])
    dfv = dfv.background_gradient(cmap="RdYlGn_r", subset=["日胜率"])
    dfv = dfv.background_gradient(cmap="RdYlGn_r", subset=["非零覆盖"])
    dfv = dfv.format(
        {
            "盈亏平衡点": "{:.2f}",
            "年化波动率": "{:.2%}",
            "最大回撤": "{:.2%}",
            "卡玛": "{:.2f}",
            "年化": "{:.2%}",
            "夏普": "{:.2f}",
            "非零覆盖": "{:.2%}",
            "日胜率": "{:.2%}",
            "绝对收益": "{:.2%}",
        }
    )
    st.dataframe(dfv, use_container_width=True)


def show_yearly_stats(df, ret_col, **kwargs):
    """按年计算日收益表现

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param kwargs:

        - sub_title: str, 子标题
    """
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    df["年份"] = df.index.year

    _stats = []
    for year, df_ in df.groupby("年份"):
        _yst = czsc.daily_performance(df_[ret_col].to_list())
        _yst["年份"] = year
        _stats.append(_yst)

    stats = pd.DataFrame(_stats).set_index("年份")

    stats = stats.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["年化"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["夏普"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["绝对收益"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["最大回撤"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["卡玛"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["年化波动率"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["盈亏平衡点"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["日胜率"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["非零覆盖"])
    stats = stats.background_gradient(cmap="RdYlGn", axis=None, subset=["新高间隔"])
    stats = stats.background_gradient(cmap="RdYlGn_r", axis=None, subset=["新高占比"])

    stats = stats.format(
        {
            "盈亏平衡点": "{:.2f}",
            "年化波动率": "{:.2%}",
            "最大回撤": "{:.2%}",
            "卡玛": "{:.2f}",
            "年化": "{:.2%}",
            "夏普": "{:.2f}",
            "非零覆盖": "{:.2%}",
            "绝对收益": "{:.2%}",
            "日胜率": "{:.2%}",
            "新高间隔": "{:.2f}",
            "新高占比": "{:.2%}",
        }
    )

    if kwargs.get("sub_title"):
        st.subheader(kwargs.get("sub_title"), divider="rainbow")
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
    dfw = dfw.copy()
    stoploss = kwargs.pop("stoploss", 0.08)
    dfw1 = czsc.stoploss_by_direction(dfw, stoploss=stoploss)

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

    czsc.show_weight_backtest(dfw1[["dt", "symbol", "weight", "price"]].copy(), **kwargs)


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
    coint_t, pvalue, crit_value = coint(df[col1], df[col2])
    l1.metric("协整检验统计量", str(round(coint_t, 3)), help="单位根检验的T统计量。")
    l2.metric(
        "协整检验P值（不协整的概率）",
        f"{pvalue:.2%}",
        help="两个时间序列不协整的概率，低于5%则可以认为两个时间序列协整。",
    )
    fig = px.line(df, x=df.index, y=[col1, col2])
    fig.update_layout(title=f"{col1} 与 {col2} 的曲线图对比", xaxis_title="", yaxis_title="value")
    st.plotly_chart(fig, use_container_width=True)


def show_out_in_compare(df, ret_col, mid_dt, **kwargs):
    """展示样本内外表现对比"""
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

    stats_i = czsc.daily_performance(dfi[ret_col].to_list())
    stats_i["标记"] = "样本内"
    stats_i["开始日期"] = dfi.index[0].strftime("%Y-%m-%d")
    stats_i["结束日期"] = dfi.index[-1].strftime("%Y-%m-%d")

    stats_o = czsc.daily_performance(dfo[ret_col].to_list())
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
            "新高占比": "{:.2%}",
        }
    )
    st.dataframe(df_stats, use_container_width=True, hide_index=True)


def show_optuna_study(study: optuna.Study, **kwargs):
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
    if top is not None:
        with st.expander(f"TOP{top} 最大回撤详情", expanded=False):
            dft = czsc.top_drawdowns(df[ret_col].copy(), top=10)
            dft = dft.style.background_gradient(cmap="RdYlGn_r", subset=["净值回撤"])
            dft = dft.background_gradient(cmap="RdYlGn", subset=["回撤天数", "恢复天数", "新高间隔"])
            dft = dft.format({"净值回撤": "{:.2%}", "回撤天数": "{:.0f}", "恢复天数": "{:.0f}", "新高间隔": "{:.0f}"})
            st.dataframe(dft, use_container_width=True)

    # 画图: 净值回撤
    # 颜色表：https://www.codeeeee.com/color/rgb.html
    drawdown = go.Scatter(
        x=df.index,
        y=df["drawdown"],
        fillcolor="salmon",
        line=dict(color="salmon"),
        fill="tozeroy",
        mode="lines",
        name="回测曲线",
    )
    fig = go.Figure(drawdown)

    # 增加 10% 分位数线，30% 分位数线，50% 分位数线，同时增加文本标记
    for q in [0.1, 0.3, 0.5]:
        y1 = df["drawdown"].quantile(q)
        fig.add_hline(y=y1, line_dash="dot", line_color="green", line_width=2)
        fig.add_annotation(x=df.index[-1], y=y1, text=f"{q:.1%} (DD: {y1:.2%})", showarrow=False, yshift=10)

    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    fig.update_layout(title="", xaxis_title="", yaxis_title="净值回撤", legend_title="回撤曲线")
    # 限制 绘制高度
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)


def show_rolling_daily_performance(df, ret_col, **kwargs):
    """展示滚动统计数据

    :param df: pd.DataFrame, 日收益数据，columns=['dt', ret_col]
    :param ret_col: str, 收益列名
    :param kwargs:
    """
    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df[[ret_col]].copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    sub_title = kwargs.get("sub_title", "滚动日收益绩效")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    c1, c2, c3 = st.columns(3)
    window = c1.number_input("滚动窗口（自然日）", value=365 * 3, min_value=365, max_value=3650)
    min_periods = c2.number_input("最小样本数", value=365, min_value=100, max_value=3650)

    dfr = czsc.rolling_daily_performance(df, ret_col, window=window, min_periods=min_periods)
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

        - sub_title: str, 子标题
        - max_overlap: int, 事件最大重叠次数

    """
    sub_title = kwargs.get("sub_title", "事件收益率特征")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    if df[factor].nunique() > 20:
        st.warning(f"因子分布过于离散，无法进行分析，请检查！！！因子独立值数量：{df[factor].nunique()}")
        return

    df = df.copy()

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    agg_method = c1.selectbox(
        "聚合方法",
        ["平均收益率", "收益中位数", "最小收益率", "盈亏比", "交易胜率"],
        index=0,
        key=f"agg_method_{factor}",
    )
    sdt = pd.to_datetime(c2.date_input("开始时间", value=df["dt"].min()))
    edt = pd.to_datetime(c3.date_input("结束时间", value=df["dt"].max()))
    max_overlap = c4.number_input("最大重叠次数", value=5, min_value=1, max_value=20)

    df[factor] = df[factor].astype(str)
    df = czsc.overlap(df, factor, new_col="overlap", max_overlap=max_overlap)
    df = df[(df["dt"] >= sdt) & (df["dt"] <= edt)].copy()

    st.write(
        f"时间范围：{df['dt'].min().strftime('%Y%m%d')} ~ {df['dt'].max().strftime('%Y%m%d')}；聚合方法：{agg_method}"
    )
    nb_cols = [x for x in df.columns.to_list() if x.startswith("n") and x.endswith("b")]

    if agg_method == "平均收益率":
        agg_method = lambda x: np.mean(x)

    if agg_method == "收益中位数":
        agg_method = lambda x: np.median(x)

    if agg_method == "最小收益率":
        agg_method = lambda x: np.min(x)

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

    if len(df["symbol"].unique()) > 1:
        with st.expander("查看品种详细数据", expanded=False):
            symbol = st.selectbox("选择品种", df["symbol"].unique().tolist(), index=0, key=f"ms1_{agg_method}")
            dfx = __markout(df[df["symbol"] == symbol].copy(), ["symbol", factor, "overlap"])
            st.dataframe(dfx, use_container_width=True)


def show_psi(df, factor, segment, **kwargs):
    """PSI分布稳定性

    :param df: pd.DataFrame, 数据源
    :param factor: str, 分组因子
    :param segment: str, 分段字段
    :param kwargs:

        - sub_title: str, 子标题
    """
    sub_title = kwargs.get("sub_title", "PSI分布稳定性")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=f"{factor}_{segment}_PSI")

    dfi = czsc.psi(df, factor, segment)
    segs = df[segment].unique().tolist()
    segs_psi = [x for x in dfi.columns if x.endswith("_PSI")]
    dfi = dfi.style.background_gradient(cmap="RdYlGn_r", subset=segs_psi, axis=None)
    dfi = dfi.background_gradient(cmap="RdYlGn_r", subset=segs, axis=None)
    dfi = dfi.background_gradient(cmap="RdYlGn_r", subset=["PSI"], axis=None)
    dfi = dfi.format("{:.2%}", na_rep="MISS")
    st.table(dfi)


def show_strategies_dailys(df, **kwargs):
    """展示多策略多品种日收益率数据：按策略等权日收益

    :param df: N策略M品种日收益率数据，columns=['dt', 'strategy', 'symbol', 'returns']，样例如下：

            ===================  ==========  ========  ============
            dt                   strategy    symbol    returns
            ===================  ==========  ========  ============
            2021-01-04 00:00:00  FUT001      SFT9001   -0.00240078
            2021-01-05 00:00:00  FUT001      SFT9001   -0.00107012
            2021-01-06 00:00:00  FUT001      SFT9001    0.00122168
            2021-01-07 00:00:00  FUT001      SFT9001    0.0020896
            2021-01-08 00:00:00  FUT001      SFT9001    0.000510725
            ===================  ==========  ========  ============

    :param kwargs:

        - sub_title: str, 子标题
    """
    sub_title = kwargs.get("sub_title", "按策略等权日收益")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    strategies = sorted(df["strategy"].unique().tolist())
    strategies = st.multiselect("选择策略", strategies, default=strategies)
    # st.write(f"策略：{strategies}")
    df = df[df["strategy"].isin(strategies)].copy().reset_index(drop=True)

    symbols = sorted(df["symbol"].unique().tolist())
    symbols = st.multiselect("选择品种", symbols, default=symbols)
    df = df[df["symbol"].isin(symbols)].copy().reset_index(drop=True)

    with st.expander("每个品种的策略覆盖情况", expanded=False):
        dfc_ = df.groupby("symbol")["strategy"].unique().to_frame().reset_index()
        dfc_["count"] = dfc_["strategy"].apply(lambda x: len(x))
        st.dataframe(dfc_[["symbol", "count", "strategy"]], use_container_width=True)

    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame"
    df["dt"] = pd.to_datetime(df["dt"])

    df1 = (
        df.groupby(["dt", "strategy"])
        .apply(lambda x: x["returns"].mean(), include_groups=False)
        .to_frame("returns")
        .reset_index()
    )
    df1 = df1.pivot(index="dt", columns="strategy", values="returns").fillna(0)
    df1["等权组合"] = df1.mean(axis=1)
    czsc.show_daily_return(df1, stat_hold_days=False, legend_only_cols=strategies)

    st.write("策略最近表现")
    czsc.show_splited_daily(df1, ret_col="等权组合", sub_title="")

    st.write("年度绩效统计")
    czsc.show_yearly_stats(df1.copy(), ret_col="等权组合", sub_title="")

    st.write("策略相关性")
    czsc.show_correlation(df1)

    st.write("月度收益率")
    czsc.show_monthly_return(df1.copy(), ret_col="等权组合", sub_title="")

    mid_dt = kwargs.get("mid_dt")
    if mid_dt:
        st.write("样本内外对比")
        mid_dt = pd.to_datetime(mid_dt).strftime("%Y%m%d")
        czsc.show_out_in_compare(df1.copy(), ret_col="等权组合", sub_title="", mid_dt=mid_dt)


def show_strategies_symbol(df, **kwargs):
    """展示多策略多品种日收益率数据：按品种等权日收益

    :param df: N策略M品种日收益率数据，columns=['dt', 'strategy', 'symbol', 'returns']，样例如下：

            ===================  ==========  ========  ============
            dt                   strategy    symbol    returns
            ===================  ==========  ========  ============
            2021-01-04 00:00:00  FUT001      SFT9001   -0.00240078
            2021-01-05 00:00:00  FUT001      SFT9001   -0.00107012
            2021-01-06 00:00:00  FUT001      SFT9001    0.00122168
            2021-01-07 00:00:00  FUT001      SFT9001    0.0020896
            2021-01-08 00:00:00  FUT001      SFT9001    0.000510725
            ===================  ==========  ========  ============

    :param kwargs:
    """
    sub_title = kwargs.get("sub_title", "按品种等权日收益")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    strategies = sorted(df["strategy"].unique().tolist())
    strategies = st.multiselect("选择策略", strategies, default=strategies, key="strategies_symbol")
    df = df[df["strategy"].isin(strategies)].copy().reset_index(drop=True)
    symbols = sorted(df["symbol"].unique().tolist())
    symbols = st.multiselect("选择品种", symbols, default=symbols, key="strategies_symbol_x")
    df = df[df["symbol"].isin(symbols)].copy().reset_index(drop=True)

    with st.expander("每个品种的策略覆盖情况", expanded=False):
        dfc_ = df.groupby("symbol")["strategy"].unique().to_frame().reset_index()
        dfc_["count"] = dfc_["strategy"].apply(lambda x: len(x))
        st.dataframe(dfc_[["symbol", "count", "strategy"]], use_container_width=True)

    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame"
    df["dt"] = pd.to_datetime(df["dt"])

    df2 = (
        df.groupby(["dt", "symbol"])
        .apply(lambda x: x["returns"].mean(), include_groups=False)
        .to_frame("returns")
        .reset_index()
    )
    df2 = df2.pivot(index="dt", columns="symbol", values="returns").fillna(0)
    df2["等权组合"] = df2.mean(axis=1)
    show_daily_return(df2, stat_hold_days=False, legend_only_cols=symbols)

    st.write("策略最近表现")
    show_splited_daily(df2, ret_col="等权组合", sub_title="")

    st.write("年度绩效统计")
    show_yearly_stats(df2.copy(), ret_col="等权组合", sub_title="")

    st.write("品种相关性")
    show_correlation(df2)

    st.write("月度收益率")
    show_monthly_return(df2.copy(), ret_col="等权组合", sub_title="")

    mid_dt = kwargs.get("mid_dt")
    if mid_dt:
        st.write("样本内外对比")
        mid_dt = pd.to_datetime(mid_dt).strftime("%Y%m%d")
        show_out_in_compare(df2.copy(), ret_col="等权组合", sub_title="", mid_dt=mid_dt)
