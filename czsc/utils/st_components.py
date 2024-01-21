import czsc
import hashlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import statsmodels.api as sm
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression


def show_daily_return(df, **kwargs):
    """用 streamlit 展示日收益

    :param df: pd.DataFrame，数据源
    :param kwargs:

        - title: str，标题
        - stat_hold_days: bool，是否展示持有日绩效指标，默认为 True
        - legend_only_cols: list，仅在图例中展示的列名

    """
    if not df.index.dtype == 'datetime64[ns]':
        df['dt'] = pd.to_datetime(df['dt'])
        df.set_index('dt', inplace=True)

    assert df.index.dtype == 'datetime64[ns]', "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    def _stats(df_, type_='持有日'):
        df_ = df_.copy()
        stats = []
        for col in df_.columns:
            if type_ == '持有日':
                col_stats = czsc.daily_performance([x for x in df_[col] if x != 0])
            else:
                assert type_ == '交易日', "type_ 参数必须是 持有日 或 交易日"
                col_stats = czsc.daily_performance(df_[col])
            col_stats['日收益名称'] = col
            stats.append(col_stats)
        stats = pd.DataFrame(stats).set_index('日收益名称')
        # fmt_cols = ['年化', '夏普', '最大回撤', '卡玛', '年化波动率', '非零覆盖', '日胜率', '盈亏平衡点', '新高间隔', '新高占比']
        # stats = stats.style.background_gradient(cmap='RdYlGn_r', axis=None, subset=fmt_cols).format('{:.4f}')

        stats = stats.style.background_gradient(cmap='RdYlGn_r', axis=None, subset=['年化'])
        stats = stats.background_gradient(cmap='RdYlGn_r', axis=None, subset=['夏普'])
        stats = stats.background_gradient(cmap='RdYlGn', axis=None, subset=['最大回撤'])
        stats = stats.background_gradient(cmap='RdYlGn_r', axis=None, subset=['卡玛'])
        stats = stats.background_gradient(cmap='RdYlGn', axis=None, subset=['年化波动率'])
        stats = stats.background_gradient(cmap='RdYlGn', axis=None, subset=['盈亏平衡点'])
        stats = stats.background_gradient(cmap='RdYlGn_r', axis=None, subset=['日胜率'])
        stats = stats.background_gradient(cmap='RdYlGn_r', axis=None, subset=['非零覆盖'])
        stats = stats.background_gradient(cmap='RdYlGn', axis=None, subset=['新高间隔'])
        stats = stats.background_gradient(cmap='RdYlGn_r', axis=None, subset=['新高占比'])

        stats = stats.format(
            {
                '盈亏平衡点': '{:.2f}',
                '年化波动率': '{:.2%}',
                '最大回撤': '{:.2%}',
                '卡玛': '{:.2f}',
                '年化': '{:.2%}',
                '夏普': '{:.2f}',
                '非零覆盖': '{:.2%}',
                '日胜率': '{:.2%}',
                '新高间隔': '{:.2f}',
                '新高占比': '{:.2%}',
            }
        )
        return stats

    with st.container():
        title = kwargs.get("title", "")
        if title:
            st.subheader(title)
            st.divider()

        st.write("交易日绩效指标")
        st.dataframe(_stats(df, type_='交易日'), use_container_width=True)

        if kwargs.get("stat_hold_days", True):
            st.write("持有日绩效指标")
            st.dataframe(_stats(df, type_='持有日'), use_container_width=True)

        df = df.cumsum()
        fig = px.line(df, y=df.columns.to_list(), title="日收益累计曲线")
        fig.update_xaxes(title='')

        # 添加每年的开始第一个日期的竖线
        for year in range(df.index.year.min(), df.index.year.max() + 1):
            first_date = df[df.index.year == year].index.min()
            fig.add_vline(x=first_date, line_dash='dash', line_color='red')

        for col in kwargs.get("legend_only_cols", []):
            fig.update_traces(visible="legendonly", selector=dict(name=col))

        st.plotly_chart(fig, use_container_width=True)


def show_monthly_return(df, ret_col='total', title="月度累计收益", **kwargs):
    """展示指定列的月度累计收益

    :param df: pd.DataFrame，数据源
    :param ret_col: str，收益列名
    :param title: str，标题
    :param kwargs:
    """
    if not df.index.dtype == 'datetime64[ns]':
        df['dt'] = pd.to_datetime(df['dt'])
        df.set_index('dt', inplace=True)

    assert df.index.dtype == 'datetime64[ns]', "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy().fillna(0)
    df.sort_index(inplace=True, ascending=True)

    if title:
        st.subheader(title, divider="rainbow")

    monthly = df[[ret_col]].resample('M').sum()
    monthly['year'] = monthly.index.year
    monthly['month'] = monthly.index.month
    monthly = monthly.pivot_table(index='year', columns='month', values=ret_col)
    month_cols = [f"{x}月" for x in monthly.columns]
    monthly.columns = month_cols
    monthly['年收益'] = monthly.sum(axis=1)

    monthly = monthly.style.background_gradient(cmap='RdYlGn_r', axis=None, subset=month_cols)
    monthly = monthly.background_gradient(cmap='RdYlGn_r', axis=None, subset=['年收益'])
    monthly = monthly.format('{:.2%}', na_rep='-')

    st.dataframe(monthly, use_container_width=True)


def show_correlation(df, cols=None, method='pearson', **kwargs):
    """用 streamlit 展示相关性

    :param df: pd.DataFrame，数据源
    :param cols: list，分析相关性的字段
    :param method: str，计算相关性的方法，可选 pearson 和 spearman
    """
    cols = cols or df.columns.to_list()
    dfr = df[cols].corr(method=method)
    dfr['average'] = (dfr.sum(axis=1) - 1) / (len(cols) - 1)
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
    col4.dataframe(
        dfm.style.background_gradient(cmap='RdYlGn_r', axis=None).format('{:.4f}', na_rep='MISS'),
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
    if df[y_col].max() > 100:  # 收益率单位为BP, 转换为万分之一
        df[y_col] = df[y_col] / 10000

    df = czsc.feture_cross_layering(df, x_col, n=n)

    mr = df.groupby(["dt", f'{x_col}分层'])[y_col].mean().reset_index()
    mrr = mr.pivot(index='dt', columns=f'{x_col}分层', values=y_col).fillna(0)

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
        dfr['多头'] = dfr[long].mean(axis=1)
        dfr['空头'] = -dfr[short].mean(axis=1)
        dfr['多空'] = (dfr['多头'] + dfr['空头']) / 2
        czsc.show_daily_return(dfr[['多头', '空头', '多空']])


def show_symbol_factor_layering(df, x_col, y_col='n1b', **kwargs):
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

    if f'{x_col}分层' not in df.columns:
        # 如果因子分层列不存在，先计算因子分层
        if df[x_col].nunique() > n:
            czsc.normalize_ts_feature(df, x_col, n=n)
        else:
            # 如果因子值的取值数量小于分层数量，直接使用因子独立值排序作为分层
            x_rank = sorted(df[x_col].unique())
            x_rank = {x_rank[i]: f'第{str(i+1).zfill(2)}层' for i in range(len(x_rank))}
            st.success(f"因子值分层对应关系：{x_rank}")
            df[f'{x_col}分层'] = df[x_col].apply(lambda x: x_rank[x])

    for i in range(n):
        df[f'第{str(i+1).zfill(2)}层'] = np.where(df[f'{x_col}分层'] == f'第{str(i+1).zfill(2)}层', df[y_col], 0)

    layering_cols = [f'第{str(i).zfill(2)}层' for i in range(1, n + 1)]
    mrr = df[['dt'] + layering_cols].copy()
    mrr.set_index('dt', inplace=True)

    tabs = st.tabs(["分层收益率", "多空组合"])

    with tabs[0]:
        show_daily_return(mrr)

    with tabs[1]:
        col1, col2 = st.columns(2)
        long = col1.multiselect("多头组合", layering_cols, default=["第02层"], key="symbol_factor_long")
        short = col2.multiselect("空头组合", layering_cols, default=["第01层"], key="symbol_factor_short")
        dfr = mrr.copy()
        dfr['多头'] = dfr[long].sum(axis=1)
        dfr['空头'] = -dfr[short].sum(axis=1)
        dfr['多空'] = dfr['多头'] + dfr['空头']
        show_daily_return(dfr[['多头', '空头', '多空']])


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
        - show_daily_detail: bool，是否展示每日收益详情，默认为 False

    """
    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("show_weight_backtest :: 持仓权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    wb = czsc.WeightBacktest(dfw, fee_rate=fee / 10000, digits=digits)
    stat = wb.results['绩效评价']

    st.divider()
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
    c1.metric("盈亏平衡点", f"{stat['盈亏平衡点']:.2%}")
    c2.metric("单笔收益", f"{stat['单笔收益']} BP")
    c3.metric("交易胜率", f"{stat['交易胜率']:.2%}")
    c4.metric("持仓K线数", f"{stat['持仓K线数']}")
    c5.metric("最大回撤", f"{stat['最大回撤']:.2%}")
    c6.metric("年化收益率", f"{stat['年化']:.2%}")
    c7.metric("夏普比率", f"{stat['夏普']:.2f}")
    c8.metric("卡玛比率", f"{stat['卡玛']:.2f}")
    st.divider()

    dret = wb.results['品种等权日收益']
    dret.index = pd.to_datetime(dret.index)
    show_daily_return(dret, legend_only_cols=dfw['symbol'].unique().tolist())

    if kwargs.get("show_backtest_detail", False):
        c1, c2 = st.columns([1, 1])
        with c1.expander("品种等权日收益", expanded=False):
            df_ = wb.results['品种等权日收益'].copy()
            st.dataframe(df_.style.background_gradient(cmap='RdYlGn_r').format("{:.2%}"), use_container_width=True)

        with c2.expander("查看开平交易对", expanded=False):
            dfp = pd.concat([v['pairs'] for k, v in wb.results.items() if k in wb.symbols], ignore_index=True)
            st.dataframe(dfp, use_container_width=True)

    if kwargs.get("show_splited_daily", False):
        with st.expander("品种等权日收益分段表现", expanded=False):
            show_splited_daily(dret[['total']].copy(), ret_col='total')

    return wb


def show_splited_daily(df, ret_col, **kwargs):
    """展示分段日收益表现

    :param df: pd.DataFrame
    :param ret_col: str, df 中的列名，指定收益列
    :param kwargs:

        sub_title: str, 子标题

    """
    if not df.index.dtype == 'datetime64[ns]':
        df['dt'] = pd.to_datetime(df['dt'])
        df.set_index('dt', inplace=True)

    assert df.index.dtype == 'datetime64[ns]', "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
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
    }

    rows = []
    for name, sdt in sdt_map.items():
        df1 = df.loc[sdt:last_dt].copy()
        row = czsc.daily_performance(df1[ret_col])
        row['开始日期'] = sdt.strftime('%Y-%m-%d')
        row['结束日期'] = last_dt.strftime('%Y-%m-%d')
        row['收益名称'] = name
        row['绝对收益'] = df1[ret_col].sum()
        rows.append(row)
    dfv = pd.DataFrame(rows).set_index('收益名称')
    cols = ['开始日期', '结束日期', '绝对收益', '年化', '夏普', '最大回撤', '卡玛', '年化波动率', '非零覆盖', '日胜率', '盈亏平衡点']
    dfv = dfv[cols].copy()

    dfv = dfv.style.background_gradient(cmap='RdYlGn_r', subset=['绝对收益'])
    dfv = dfv.background_gradient(cmap='RdYlGn_r', subset=['年化'])
    dfv = dfv.background_gradient(cmap='RdYlGn_r', subset=['夏普'])
    dfv = dfv.background_gradient(cmap='RdYlGn', subset=['最大回撤'])
    dfv = dfv.background_gradient(cmap='RdYlGn_r', subset=['卡玛'])
    dfv = dfv.background_gradient(cmap='RdYlGn', subset=['年化波动率'])
    dfv = dfv.background_gradient(cmap='RdYlGn', subset=['盈亏平衡点'])
    dfv = dfv.background_gradient(cmap='RdYlGn_r', subset=['日胜率'])
    dfv = dfv.background_gradient(cmap='RdYlGn_r', subset=['非零覆盖'])
    dfv = dfv.format(
        {
            '盈亏平衡点': '{:.2f}',
            '年化波动率': '{:.2%}',
            '最大回撤': '{:.2%}',
            '卡玛': '{:.2f}',
            '年化': '{:.2%}',
            '夏普': '{:.2f}',
            '非零覆盖': '{:.2%}',
            '日胜率': '{:.2%}',
            '绝对收益': '{:.2%}',
        }
    )
    st.dataframe(dfv, use_container_width=True)


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
        df['dt'] = pd.to_datetime(df['dt'])
        df = df.set_index('dt')

    df = df[[col1, col2]].copy()
    if df.isnull().sum().sum() > 0:
        st.dataframe(df[df.isnull().sum(axis=1) > 0])
        st.error(f"列 {col1} 或 {col2} 中存在缺失值，请先处理缺失值")
        return

    sub_title = kwargs.get('sub_title', None)
    if sub_title:
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode('utf-8')).hexdigest()[:8])

    min_periods = kwargs.get('min_periods', None)
    window = kwargs.get('window', None)
    corr_method = kwargs.get('corr_method', 'pearson')

    if not window or window <= 0:
        method = 'expanding'
        corr_result = df[col1].expanding(min_periods=min_periods).corr(df[col2], pairwise=True)
    else:
        method = 'rolling'
        corr_result = df[col1].rolling(window=window, min_periods=min_periods).corr(df[col2], pairwise=True)

    corr_result = corr_result.dropna()
    corr_result = corr_result.rename('corr')
    line = go.Scatter(x=corr_result.index, y=corr_result, mode='lines', name='corr')
    layout = go.Layout(
        title=f'滑动（{method}）相关系数',
        xaxis=dict(title=''),
        yaxis=dict(title='corr'),
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
        df['dt'] = pd.to_datetime(df['dt'])
        df = df.set_index('dt')
    df = df.sort_index(ascending=True)

    if df[col].isnull().sum() > 0:
        st.dataframe(df[df[col].isnull()])
        st.error(f"列 {col} 中存在缺失值，请先处理缺失值")
        return

    col1, col2 = st.columns(2)

    with col1:
        sub_title = f"自相关系数分析（{col}）"
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode('utf-8')).hexdigest()[:8])
        c1, c2, c3 = st.columns([2, 2, 1])
        nlags = int(c1.number_input('最大滞后阶数', value=20, min_value=1, max_value=100, step=1))
        method = c2.selectbox('选择分析方法', ['acf', 'pacf'], index=0)

        if method == 'acf':
            acf_result, conf_int = sm.tsa.acf(df[[col]].copy(), nlags=nlags, alpha=0.05, missing='raise')
        else:
            acf_result, conf_int = sm.tsa.pacf(df[[col]].copy(), nlags=nlags, alpha=0.05)

        bar = go.Bar(x=list(range(len(acf_result))), y=acf_result, name='自相关系数')
        upper = go.Scatter(x=list(range(len(acf_result))), y=conf_int[:, 1], mode='lines', name='95%置信区间上界')
        lower = go.Scatter(x=list(range(len(acf_result))), y=conf_int[:, 0], mode='lines', name='95%置信区间下界')
        layout = go.Layout(title=method.upper(), xaxis=dict(title='滞后阶数'), yaxis=dict(title='自相关系数'))
        fig = go.Figure(data=[bar, upper, lower], layout=layout)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sub_title = f"滞后N阶滑动相关性（{col}）"
        st.subheader(sub_title, divider="rainbow", anchor=hashlib.md5(sub_title.encode('utf-8')).hexdigest()[:8])
        c1, c2, c3, c4 = st.columns(4)
        min_periods = int(c1.number_input('最小滑动窗口长度', value=20, min_value=0, step=1))
        window = int(c2.number_input('滑动窗口长度', value=0, step=1, help='0 表示按 expanding 方式滑动'))
        corr_method = c3.selectbox('相关系数计算方法', ['pearson', 'kendall', 'spearman'])
        n = int(c4.number_input('自相关滞后阶数', value=1, min_value=1, step=1))

        df[f"{col}_lag{n}"] = df[col].shift(-n)
        df.dropna(subset=[f"{col}_lag{n}"], inplace=True)

        show_ts_rolling_corr(df, col, f"{col}_lag{n}", min_periods=min_periods, window=window, corr_method=corr_method)
