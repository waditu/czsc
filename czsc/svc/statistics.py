"""
统计分析相关的可视化组件

包含分段收益、年度统计、样本内外对比、PSI分析等功能
"""

import hashlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from .base import safe_import_daily_performance, apply_stats_style, ensure_datetime_index


def show_splited_daily(df, ret_col, **kwargs):
    """展示分段日收益表现

    :param df: pd.DataFrame
    :param ret_col: str, df 中的列名，指定收益列
    :param kwargs:
        sub_title: str, 子标题
    """
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    yearly_days = kwargs.get("yearly_days", 252)
    df = ensure_datetime_index(df)
    df = df.copy().fillna(0).sort_index(ascending=True)

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
    dfv_styled = apply_stats_style(dfv)
    st.dataframe(dfv_styled, use_container_width=True)


def show_yearly_stats(df, ret_col, **kwargs):
    """按年计算日收益表现

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param kwargs:
        - sub_title: str, 子标题
    """
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    df = ensure_datetime_index(df)
    df = df.copy().fillna(0).sort_index(ascending=True)

    df["年份"] = df.index.year
    yearly_days = max(len(df_) for year, df_ in df.groupby("年份"))

    _stats = []
    for year, df_ in df.groupby("年份"):
        _yst = daily_performance(df_[ret_col].to_list(), yearly_days=yearly_days)
        _yst["年份"] = year
        _stats.append(_yst)

    stats = pd.DataFrame(_stats).set_index("年份")
    stats_styled = apply_stats_style(stats)

    sub_title = kwargs.get("sub_title", "")
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=sub_title)
    st.dataframe(stats_styled, use_container_width=True)


def show_out_in_compare(df, ret_col, mid_dt, **kwargs):
    """展示样本内外表现对比"""
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    assert isinstance(df, pd.DataFrame), "df 必须是 pd.DataFrame 类型"
    df = ensure_datetime_index(df)
    df = df[[ret_col]].copy().fillna(0).sort_index(ascending=True)

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
            "标记", "开始日期", "结束日期", "年化", "最大回撤", "夏普", "卡玛",
            "日胜率", "年化波动率", "非零覆盖", "盈亏平衡点", "新高间隔", "新高占比", "回撤风险",
        ]
    ]

    sub_title = kwargs.get("sub_title", "样本内外表现对比")
    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 应用样式
    df_stats_styled = df_stats.style.background_gradient(cmap="RdYlGn_r", subset=["年化"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn_r", subset=["夏普"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn", subset=["最大回撤"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn_r", subset=["卡玛"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn", subset=["年化波动率"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn", subset=["盈亏平衡点"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn_r", subset=["日胜率"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn_r", subset=["非零覆盖"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn", subset=["新高间隔"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn", subset=["回撤风险"])
    df_stats_styled = df_stats_styled.background_gradient(cmap="RdYlGn_r", subset=["新高占比"])
    df_stats_styled = df_stats_styled.format({
        "盈亏平衡点": "{:.2f}", "年化波动率": "{:.2%}", "最大回撤": "{:.2%}",
        "卡玛": "{:.2f}", "年化": "{:.2%}", "夏普": "{:.2f}", "非零覆盖": "{:.2%}",
        "日胜率": "{:.2%}", "新高间隔": "{:.2f}", "回撤风险": "{:.2f}", "新高占比": "{:.2%}",
    })
    st.dataframe(df_stats_styled, use_container_width=True, hide_index=True)


def show_outsample_by_dailys(df, outsample_sdt1, outsample_sdt2=None):
    """根据日收益数据展示样本内外对比

    :param df: 日收益数据，包含列 ['dt', 'returns']
    :param outsample_sdt1: 样本外开始日期
    :param outsample_sdt2: 实盘开始跟踪的日期，如果为 None，则只展示样本内和样本外两个阶段
    """
    from czsc.eda import cal_yearly_days
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    if not ("dt" in df.columns and "returns" in df.columns):
        st.error(f"数据格式错误，必须包含列 ['dt', 'returns']; 当前列：{df.columns}")
        return

    df["dt"] = pd.to_datetime(df["dt"])
    yearly_days = cal_yearly_days(df["dt"])
    outsample_sdt1 = pd.to_datetime(outsample_sdt1).strftime("%Y-%m-%d")

    def __show_returns(dfx):
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
            st.error("样本外开始日期必须小于实盘开始日期")
            return

        df1 = df[df["dt"] < outsample_sdt1].copy()  # 样本内
        df2 = df[(df["dt"] >= outsample_sdt1) & (df["dt"] < outsample_sdt2)].copy()  # 第一段样本外
        df3 = df[df["dt"] >= outsample_sdt2].copy()  # 第二段样本外

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
    dfi_styled = dfi.style.background_gradient(cmap="RdYlGn_r", subset=segs_psi, axis=None)
    dfi_styled = dfi_styled.background_gradient(cmap="RdYlGn_r", subset=segs, axis=None)
    dfi_styled = dfi_styled.background_gradient(cmap="RdYlGn_r", subset=["PSI"], axis=None)
    dfi_styled = dfi_styled.format("{:.2%}", na_rep="MISS")
    st.table(dfi_styled)


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

    dfg_styled = dfg.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    dfg_styled = dfg_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    dfg_styled = dfg_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["min", "25%", "50%", "75%", "max"])
    dfg_styled = dfg_styled.format({
        "count": "{:.0f}", "mean": "{:.4f}", "std": "{:.2%}",
        "min": "{:.4f}", "25%": "{:.4f}", "50%": "{:.4f}", "75%": "{:.4f}", "max": "{:.4f}",
    })
    st.dataframe(dfg_styled, use_container_width=True)


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

    df = ensure_datetime_index(df).copy()

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
    from scipy.stats import shapiro, jarque_bera, kstest, norm
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


def show_describe(df: pd.DataFrame, **kwargs):
    """展示 DataFrame 的描述性统计信息

    :param df: pd.DataFrame, 数据框
    """
    columns = kwargs.get('columns', None)
    percentiles = kwargs.get('percentiles', [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
    digits = kwargs.get('digits', 2)

    columns = columns or df.columns
    df_raw = df[columns].copy()

    df_desc = df_raw.describe(percentiles=percentiles).T
    df_desc['偏度'] = df_raw.skew()
    df_desc['峰度'] = df_raw.kurt()

    quantiles = [x for x in df_desc.columns if "%" in x]
    df_styled = df_desc.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["max", "min"] + quantiles)
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["偏度"])
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["峰度"])

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
    
    df_styled = df_styled.format(format_dict)
    st.dataframe(df_styled, use_container_width=True)
    st.caption("说明：描述性统计中 count 为非空值的个数，mean 为均值，std 为标准差，min 为最小值，max 为最大值，N% 为分位数。")


def show_df_describe(df: pd.DataFrame):
    """展示 DataFrame 的描述性统计信息

    :param df: pd.DataFrame，必须是 df.describe() 的结果
    """
    quantiles = [x for x in df.columns if "%" in x]
    df_styled = df.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    df_styled = df_styled.background_gradient(cmap="RdYlGn_r", axis=None, subset=["max", "min"] + quantiles)

    format_dict = {
        "count": "{:.0f}",
        "mean": "{:.4f}",
        "std": "{:.4f}",
        "min": "{:.4f}",
        "max": "{:.4f}",
    }
    for q in quantiles:
        format_dict[q] = "{:.4f}"

    df_styled = df_styled.format(format_dict)
    st.dataframe(df_styled, use_container_width=True) 