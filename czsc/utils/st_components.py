import czsc
import pandas as pd
import streamlit as st
import plotly.express as px
from sklearn.linear_model import LinearRegression


def show_daily_return(df, **kwargs):
    """用 streamlit 展示日收益"""
    assert df.index.dtype == 'datetime64[ns]', "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    type_ = "持有日" if kwargs.get("none_zero", False) else "交易日"

    df = df.copy().fillna(0)
    stats = []
    for col in df.columns:
        col_stats = czsc.daily_performance([x for x in df[col] if x != 0]) if type_ == '持有日' else czsc.daily_performance(df[col])
        col_stats['日收益名称'] = col
        stats.append(col_stats)

    stats = pd.DataFrame(stats).set_index('日收益名称')
    fmt_cols = ['年化', '夏普', '最大回撤', '卡玛', '年化波动率', '非零覆盖', '日胜率', '盈亏平衡点']
    stats = stats.style.background_gradient(cmap='RdYlGn_r', axis=None).format('{:.4f}', subset=fmt_cols)

    df = df.cumsum()
    fig = px.line(df, y=df.columns.to_list(), title="日收益累计曲线")
    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector=dict(name=col))

    title = kwargs.get("title", "")
    with st.container():
        if title:
            st.subheader(title)
            st.divider()
        st.dataframe(stats, use_container_width=True)
        st.plotly_chart(fig, use_container_width=True)


def show_correlation(df, cols=None, method='pearson', **kwargs):
    """用 streamlit 展示相关性

    :param df: pd.DataFrame，数据源
    :param cols: list，分析相关性的字段
    :param method: str，计算相关性的方法，可选 pearson 和 spearman
    """
    cols = cols or df.columns.to_list()
    dfr = df[cols].corr(method=method)
    dfr['total'] = dfr.sum(axis=1) - 1
    dfr = dfr.style.background_gradient(cmap='RdYlGn_r', axis=None).format('{:.4f}', na_rep='MISS')
    st.dataframe(dfr, use_container_width=kwargs.get("use_container_width", True))


def show_sectional_ic(df, x_col, y_col, method='pearson', **kwargs):
    """使用 streamlit 展示截面IC

    :param df: pd.DataFrame，数据源
    :param x_col: str，因子列名
    :param y_col: str，收益列名
    :param method: str，计算IC的方法，可选 pearson 和 spearman
    """
    dfc, res = czsc.cross_sectional_ic(df, x_col=x_col, y_col=y_col, dt_col='dt', method=method)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
    col1.metric("IC均值", res['IC均值'])
    col1.metric("IC标准差", res['IC标准差'])
    col2.metric("ICIR", res['ICIR'])
    col2.metric("IC胜率", res['IC胜率'])
    col3.metric("IC绝对值>2%占比", res['IC绝对值>2%占比'])
    col3.metric("品种数量", df['symbol'].nunique())

    dfc[['year', 'month']] = dfc.dt.apply(lambda x: pd.Series([x.year, x.month]))
    dfm = dfc.groupby(['year', 'month']).agg({'ic': 'mean'}).reset_index()
    dfm = pd.pivot_table(dfm, index='year', columns='month', values='ic')

    col4.write("月度IC分析结果：")
    col4.dataframe(dfm.style.background_gradient(cmap='RdYlGn_r', axis=None).format('{:.4f}', na_rep='MISS'),
                   use_container_width=True)

    fig = px.histogram(df, x=x_col, marginal="box", title="因子数据分布图")
    st.plotly_chart(fig, use_container_width=True)


def show_factor_returns(df, x_col, y_col):
    """使用 streamlit 展示因子收益率

    :param df: pd.DataFrame，数据源
    :param x_col: str，因子列名
    :param y_col: str，收益列名
    """
    assert 'dt' in df.columns, "时间列必须为 dt"

    res = []
    for dt, dfg in df.groupby("dt"):
        dfg = dfg.copy().dropna(subset=[x_col, y_col])
        X = dfg[x_col].values.reshape(-1, 1)
        y = dfg[y_col].values.reshape(-1, 1)
        model = LinearRegression(fit_intercept=False).fit(X, y)
        res.append([dt, model.coef_[0][0]])

    res = pd.DataFrame(res, columns=["dt", "因子收益率"])
    res['dt'] = pd.to_datetime(res['dt'])

    col1, col2 = st.columns(2)
    fig = px.bar(res, x='dt', y="因子收益率", title="因子逐K收益率")
    col1.plotly_chart(fig, use_container_width=True)

    res["因子累计收益率"] = res["因子收益率"].cumsum()
    fig = px.line(res, x='dt', y="因子累计收益率", title="因子累计收益率")
    col2.plotly_chart(fig, use_container_width=True)


def show_factor_layering(df, x_col, y_col='n1b', **kwargs):
    """使用 streamlit 绘制因子分层收益率图

    :param df: 因子数据
    :param x_col: 因子列名
    :param y_col: 收益列名
    :param kwargs:

        - n: 分层数量，默认为10
        - long: 多头组合，例如 "第10层"
        - short: 空头组合，例如 "第01层"

    """
    n = kwargs.get("n", 10)
    if df[y_col].max() > 100:       # 收益率单位为BP, 转换为万分之一
        df[y_col] = df[y_col] / 10000

    def _layering(x):
        return pd.qcut(x, q=n, labels=False, duplicates='drop')
    df[f'{x_col}分层'] = df.groupby('dt')[x_col].transform(_layering)

    mr = df.groupby(["dt", f'{x_col}分层'])[y_col].mean().reset_index()
    mrr = mr.pivot(index='dt', columns=f'{x_col}分层', values=y_col).fillna(0)
    mrr.columns = [f'第{str(i).zfill(2)}层' for i in range(1, n + 1)]

    tabs = st.tabs(["分层收益率", "多空组合"])
    with tabs[0]:
        show_daily_return(mrr)

    with tabs[1]:
        long = kwargs.get("long", f"第{n}层")
        short = kwargs.get("short", "第01层")
        st.write(f"多头：{long}，空头：{short}")
        mrr['多空组合'] = (mrr[long] - mrr[short]) / 2
        show_daily_return(mrr[['多空组合']])
