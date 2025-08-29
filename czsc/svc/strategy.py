"""
策略分析组件模块

该模块提供策略分析相关的 Streamlit 可视化组件，包括：
- 优化结果展示
- 策略收益分析
- 组合表现分析
- 风险分析等

作者: 缠中说禅团队
"""

import hashlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
from loguru import logger

from .base import safe_import_weight_backtest, apply_stats_style


def show_optuna_study(study, **kwargs):
    """展示 Optuna Study 的可视化结果

    :param study: optuna.study.Study, Optuna Study 对象
    :param kwargs: dict, 其他参数

        - sub_title: str, optional, 子标题
        - keep: float, optional, 默认0.2, 保留最佳参数的比例

    :return: optuna.study.Study
    """
    try:
        import optuna
    except ImportError:
        st.error("请安装 optuna 库, 执行命令：pip install optuna")
        return

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


def show_returns_contribution(df, returns=None, max_returns=100):
    """分析子策略对总收益的贡献

    :param df: pd.DataFrame, 子策略日收益数据，index 为 datetime, columns 为 子策略名称
    :param returns: list, 子策略名称列表
    :param max_returns: int, 最大展示策略数量
    """
    df = df.copy()
    for dt_col in ["date", "dt"]:
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
    plot_df = pd.DataFrame({"策略": total_returns.index, "收益贡献": total_returns.values})
    plot_df = plot_df.sort_values(by="收益贡献", ascending=False)

    # 创建两列布局
    col1, col2 = st.columns([3, 2])

    with col1.container(border=True):
        # 绘制柱状图
        fig_bar = px.bar(
            plot_df,
            x="策略",
            y="收益贡献",
            title="收益贡献分析（柱状图）",
            color="收益贡献",
            color_continuous_scale="RdYlGn_r",
            width=600,
            height=400,
        )
        fig_bar.update_layout(yaxis_title="绝对收益", xaxis_title="策略")
        st.plotly_chart(fig_bar)
        st.caption("柱状图展示每个策略的收益贡献, Y轴为绝对收益大小，X轴为策略名称")

    with col2.container(border=True):
        # 绘制饼图，如果收益贡献为负，删除
        plot_df = plot_df[plot_df["收益贡献"] > 0]
        fig_pie = px.pie(plot_df, values="收益贡献", names="策略", title="盈利贡献分析（饼图）", width=600, height=400)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
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
    try:
        from rs_czsc import daily_performance
    except ImportError:
        from czsc import daily_performance

    from czsc.eda import cal_yearly_days

    df = df[["symbol", "dt", "price"]].copy()
    df["pct_change"] = df.groupby("symbol")["price"].pct_change()
    df["date"] = df["dt"].dt.date
    dailys = df.groupby(["symbol", "date"])["pct_change"].sum().reset_index()
    dailys = dailys.pivot(index="date", columns="symbol", values="pct_change")
    dailys = dailys.sort_values(by="date", ascending=True)
    dailys = dailys.fillna(0)

    with st.container(border=True):
        st.markdown("##### 品种等权累计收益&最大回撤")
        dailys["total"] = dailys.mean(axis=1)
        dailys.index = pd.to_datetime(dailys.index)

        yearly_days = cal_yearly_days(dailys.index.to_list())
        stats = daily_performance(dailys["total"].to_list(), yearly_days=yearly_days)

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        c1.metric("年化收益率", f"{stats['年化']:.2%}", border=True)
        c2.metric("夏普比率", f"{stats['夏普']:.2f}", border=True)
        c3.metric("最大回撤", f"{stats['最大回撤']:.2%}", border=True)
        c4.metric("卡玛比率", f"{stats['卡玛']:.2f}", border=True)
        c5.metric("日胜率", f"{stats['日胜率']:.2%}", border=True)
        c6.metric("年化波动率", f"{stats['年化波动率']:.2%}", border=True)
        c7.metric("新高占比", f"{stats['新高占比']:.2%}", border=True, help="新高占比: 新高日占所有交易日的比例")
        c8.metric("新高间隔", f"{stats['新高间隔']}", border=True, help="新高间隔: 相邻新高日之间的最大交易日间隔")

        from .returns import show_drawdowns

        show_drawdowns(dailys, ret_col="total", sub_title="")

    with st.container(border=True):
        st.markdown("##### 品种间日收益相关性矩阵")
        from .correlation import show_correlation

        show_correlation(dailys, use_st_table=kwargs.get("use_st_table", False))


def show_quarterly_effect(returns: pd.Series):
    """展示策略的季节性收益对比

    :param returns: 日收益率序列，index 为日期
    """
    import plotly.express as px
    from czsc.eda import cal_yearly_days

    try:
        from rs_czsc import daily_performance
    except ImportError:
        from czsc import daily_performance

    returns.index = pd.to_datetime(returns.index)
    yearly_days = cal_yearly_days(returns.index.to_list())

    # 按4个季度划分数据为 s1，s2，s3，s4，分别计算每个季度的统计指标
    s1 = returns[returns.index.quarter == 1]
    s2 = returns[returns.index.quarter == 2]
    s3 = returns[returns.index.quarter == 3]
    s4 = returns[returns.index.quarter == 4]

    def __show_quarter_stats(s: pd.Series):
        stats = daily_performance(s.to_list(), yearly_days=yearly_days)
        st.markdown(
            f"总交易天数: `{len(s)}天` \
                    | 年化: `{stats['年化']:.2%}` \
                    | 夏普: `{stats['夏普']:.2f}` \
                    | 最大回撤: `{stats['最大回撤']:.2%}` \
                    | 卡玛: `{stats['卡玛']:.2f}` \
                    | 年化波动率: `{stats['年化波动率']:.2%}`"
        )

        # 用 plotly 绘制累计收益率曲线, 用 数字作为index，方便对比
        fig = px.line(s.cumsum(), x=list(range(len(s))), y=s.cumsum().values, title="")
        fig.update_layout(xaxis_title="交易天数", yaxis_title="累计收益率", margin=dict(l=0, r=0, t=0, b=0))

        # 按年分组，绘制矩形覆盖
        years = s.index.year.unique()
        colors = ["rgba(102, 255, 178, 0.1)", "rgba(102, 178, 255, 0.1)"]  # 薄荷绿和天蓝色，半透明
        shapes = []
        for i, year in enumerate(years):
            # 获取该年的第一个和最后一个交易日在数字索引中的位置
            year_data = s[s.index.year == year]
            start_idx = s.index.get_indexer([year_data.index[0]])[0]
            end_idx = s.index.get_indexer([year_data.index[-1]])[0]

            # 添加矩形
            shapes.append(
                dict(
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
                )
            )

        # 更新图表布局，添加矩形
        fig.update_layout(shapes=shapes)

        # 添加年份标签
        annotations = []
        for i, year in enumerate(years):
            year_data = s[s.index.year == year]
            mid_idx = s.index.get_indexer([year_data.index[len(year_data) // 2]])[0]

            annotations.append(
                dict(x=mid_idx, y=0.95, xref="x", yref="paper", text=str(year), showarrow=False, font=dict(size=14))
            )

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


def show_multi_backtest(wbs: dict, **kwargs):
    """展示多个策略的回测结果"""
    from czsc.svc.base import apply_stats_style
    from czsc.svc.returns import show_cumulative_returns
    from czsc.svc.statistics import show_describe

    rows = []
    dailys = []
    for strategy, wb in wbs.items():
        stats = {
            "策略名称": strategy,
        }
        stats.update(wb.stats)
        rows.append(stats)

        # 获取日收益
        daily = wb.daily_return.copy()[["date", "total"]]
        daily["strategy"] = strategy
        daily["return"] = daily["total"]
        daily["dt"] = daily["date"]
        dailys.append(daily[["dt", "strategy", "return"]])

    df_stats = pd.DataFrame(rows)
    # st.write(df_stats.columns.to_list())
    cols = [
        "策略名称",
        "开始日期",
        "结束日期",
        "绝对收益",
        "年化",
        "夏普",
        "最大回撤",
        "卡玛",
        "年化波动率",
        "下行波动率",
        "非零覆盖",
        "新高间隔",
        "新高占比",
        "回撤风险",
        "交易胜率",
        "单笔收益",
        "持仓K线数",
        "多头占比",
        "空头占比",
        "与基准相关性",
        "波动比",
        "与基准波动相关性",
        "品种数量",
    ]
    df_stats = df_stats[cols].copy()
    with st.container(border=True):
        st.markdown("#### :orange[策略绩效对比]")

        st.dataframe(apply_stats_style(df_stats))

        dailys = pd.concat(dailys, axis=0)
        dailys["dt"] = pd.to_datetime(dailys["dt"])
        dailys = dailys.sort_values("dt", ascending=False)
        df_dailys = pd.pivot_table(dailys, index="dt", columns="strategy", values="return")

        show_cumulative_returns(df_dailys)

    if kwargs.get("show_describe", False):
        with st.container(border=True):
            st.markdown("#### :red[主要统计指标分布]")
            # 绘制单笔收益、持仓K线数、夏普的分布
            show_describe(df_stats[["单笔收益", "持仓K线数", "夏普", "年化"]])

    return df_stats, df_dailys


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
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        st.error("无法导入WeightBacktest类，请检查czsc或rs_czsc库的安装")
        return

    from czsc.eda import cal_yearly_days

    fee_rate = kwargs.get("fee_rate", 0.00)
    digits = kwargs.get("digits", 1)
    weight_type = kwargs.get("weight_type", "ts")

    yearly_days = cal_yearly_days(df["dt"].unique().tolist())

    mark_cols = [
        "is_best_period",
        "is_best_up_period",
        "is_best_down_period",
        "is_normal_period",
        "is_worst_period",
        "is_worst_up_period",
        "is_worst_down_period",
    ]
    if not all(col in df.columns for col in mark_cols):
        from czsc.eda import mark_cta_periods

        q1 = kwargs.get("q1", 0.15)
        q2 = kwargs.get("q2", 0.4)
        dfs = mark_cta_periods(df.copy(), freq="日线", verbose=False, q1=q1, q2=q2)
    else:
        dfs = df.copy()

    if "price" not in dfs.columns:
        dfs["price"] = dfs["close"]

    p1 = dfs["is_best_period"].value_counts()[1] / len(dfs)
    p1_up = dfs["is_best_up_period"].value_counts()[1] / len(dfs)
    p1_down = dfs["is_best_down_period"].value_counts()[1] / len(dfs)
    p2 = dfs["is_worst_period"].value_counts()[1] / len(dfs)
    p2_up = dfs["is_worst_up_period"].value_counts()[1] / len(dfs)
    p2_down = dfs["is_worst_down_period"].value_counts()[1] / len(dfs)
    st.markdown(
        f"趋势行情占比：:red[{p1:.2%}]，其中上涨趋势占比：:red[{p1_up:.2%}]，下跌趋势占比：:red[{p1_down:.2%}]；\n"
        f"震荡行情占比：:green[{p2:.2%}]，其中上行震荡占比：:green[{p2_up:.2%}]，下行震荡占比：:green[{p2_down:.2%}]"
    )
    st.caption(f"WeightBacktest 参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")

    wb_cols = ["dt", "symbol", "weight", "price"]
    period_flags = [
        None,
        "is_best_period",
        "is_worst_period",
        "is_normal_period",
        "is_best_up_period",
        "is_best_down_period",
        "is_worst_up_period",
        "is_worst_down_period",
    ]
    classify = ["原始策略", "趋势行情", "震荡行情", "普通行情", "上涨趋势", "下跌趋势", "上行震荡", "下行震荡"]

    wbs = {}
    for flag, classify_ in zip(period_flags, classify):
        df_tmp = dfs.copy()
        if flag:
            df_tmp["weight"] = np.where(df_tmp[flag], df_tmp["weight"], 0)
        wb = WeightBacktest(
            df_tmp[wb_cols],
            fee_rate=fee_rate,
            digits=digits,
            weight_type=weight_type,
            yearly_days=yearly_days,
        )
        wbs[classify_] = wb

    show_multi_backtest(wbs, show_describe=False)


def show_volatility_classify(df: pd.DataFrame, kind="ts", **kwargs):
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
        - q1: 波动率最大的K线数量占比，默认 0.3，mark_volatility 函数的参数
        - q2: 波动率最小的K线数量占比，默认 0.3，mark_volatility 函数的参数

    :return: None

    ==============
    example
    ==============
    >>> show_volatility_classify(df, fee_rate=0.00, digits=1, weight_type='ts',
    >>>                          kind='ts', window=20, q1=0.2, q2=0.2 )
    """
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        st.error("无法导入WeightBacktest类，请检查czsc或rs_czsc库的安装")
        return

    from czsc.eda import cal_yearly_days

    fee_rate = kwargs.get("fee_rate", 0.00)
    digits = kwargs.get("digits", 1)
    weight_type = kwargs.get("weight_type", "ts")

    yearly_days = cal_yearly_days(df["dt"].unique().tolist())

    mark_cols = ["is_max_volatility", "is_mid_volatility", "is_min_volatility"]
    if not all(col in df.columns for col in mark_cols):
        from czsc.eda import mark_volatility

        window = kwargs.get("window", 20)
        q1 = kwargs.get("q1", 0.3)
        q2 = kwargs.get("q2", 0.3)
        dfs = mark_volatility(df.copy(), kind=kind, verbose=False, q1=q1, q2=q2, window=window)

    else:
        dfs = df.copy()

    if "price" not in dfs.columns:
        dfs["price"] = dfs["close"]

    p1 = dfs["is_max_volatility"].value_counts()[1] / len(dfs)
    p2 = dfs["is_mid_volatility"].value_counts()[1] / len(dfs)
    p3 = dfs["is_min_volatility"].value_counts()[1] / len(dfs)
    st.markdown(f"高波动行情占比：:red[{p1:.2%}]；中波动行情占比：:green[{p2:.2%}]；低波动行情占比：:blue[{p3:.2%}]")
    st.caption(f"WeightBacktest 参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")

    wb = WeightBacktest(
        dfs[["dt", "symbol", "weight", "price"]],
        fee_rate=fee_rate,
        digits=digits,
        weight_type=weight_type,
        yearly_days=yearly_days,
    )

    df1 = dfs.copy()
    df1["weight"] = np.where(df1["is_max_volatility"], df1["weight"], 0)
    df1 = df1[["dt", "symbol", "weight", "price"]].copy().reset_index(drop=True)
    wb1 = WeightBacktest(df1, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days)

    df2 = dfs.copy()
    df2["weight"] = np.where(df2["is_mid_volatility"], df2["weight"], 0)
    df2 = df2[["dt", "symbol", "weight", "price"]].copy().reset_index(drop=True)
    wb2 = WeightBacktest(df2, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days)

    df3 = dfs.copy()
    df3["weight"] = np.where(df3["is_min_volatility"], df3["weight"], 0)
    df3 = df3[["dt", "symbol", "weight", "price"]].copy().reset_index(drop=True)
    wb3 = WeightBacktest(df3, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days)

    classify = ["原始策略", "高波动", "中波动", "低波动"]
    wbs = {classify_: wb_ for classify_, wb_ in zip(classify, [wb, wb1, wb2, wb3])}
    show_multi_backtest(wbs, show_describe=False)


def show_portfolio(df: pd.DataFrame, portfolio: str, benchmark: Optional[str] = None, **kwargs):
    """分析组合日收益绩效

    :param df: 日收益数据，包含 dt, portfolio, benchmark 三列, 其中 dt 为日期, portfolio 为组合收益, benchmark 为基准收益
    :param portfolio: 组合名称
    :param benchmark: 基准名称, 可选
    :param show_detail: 是否展示详情, 可选, 默认展示
    """
    try:
        from rs_czsc import daily_performance
    except ImportError:
        from czsc import daily_performance

    from czsc.eda import cal_yearly_days

    if benchmark is not None:
        df["alpha"] = df[portfolio] - df[benchmark]
        df = df[["dt", portfolio, benchmark, "alpha"]].copy()
    else:
        df = df[["dt", portfolio]].copy()

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

        from .returns import show_drawdowns

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

        daily = df.copy().set_index("dt")
        with tabs[0]:
            from .statistics import show_yearly_stats

            show_yearly_stats(daily, ret_col=portfolio, sub_title="")

        with tabs[1]:
            show_quarterly_effect(daily[portfolio])

        with tabs[2]:
            from .returns import show_monthly_return

            show_monthly_return(daily, ret_col=portfolio, sub_title="")

        if benchmark is not None:
            with tabs[3]:
                yearly_days = cal_yearly_days(daily.index.to_list())
                from .returns import show_daily_return

                show_daily_return(daily, stat_hold_days=False, plot_cumsum=True, sub_title="", yearly_days=yearly_days)


def show_turnover_rate(df: pd.DataFrame):
    """显示换手率变化

    :param df: 权重数据，必须包含 dt, symbol, weight 三列, 其他列忽略
    """
    from czsc.eda import turnover_rate

    res = turnover_rate(df, verbose=True)
    dfc = res["日换手详情"]  # 两列：dt, change
    dfc["dt"] = pd.to_datetime(dfc["dt"])

    # 最近30天换手率
    _sdt_30 = dfc["dt"].max() - pd.Timedelta(days=30)
    _dfc = dfc[dfc["dt"] >= _sdt_30]

    # 最近一年换手率
    _sdt_year = dfc["dt"].max() - pd.Timedelta(days=365)
    _dfy = dfc[dfc["dt"] >= _sdt_year]

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
    df_daily["change"] = df_daily["change"].cumsum()
    fig = px.line(df_daily, x="dt", y="change", title="日换手累计曲线")
    fig.update_xaxes(title_text="")
    p1.plotly_chart(fig, use_container_width=True)

    # 月换手的柱状图
    df_monthly = dfc.copy()
    df_monthly = df_monthly.set_index("dt").resample("ME").sum().reset_index()
    fig = px.bar(df_monthly, x="dt", y="change", title="月换手变化")
    fig.update_xaxes(title_text="")
    p2.plotly_chart(fig, use_container_width=True)

    # 年换手的柱状图
    df_yearly = dfc.copy()
    df_yearly = df_yearly.set_index("dt").resample("YE").sum().reset_index()
    df_yearly["dt"] = df_yearly["dt"].dt.strftime("%Y")
    df_yearly["change"] = df_yearly["change"].round(0)
    fig = px.bar(df_yearly, x="dt", y="change", title="年换手变化", hover_data=["change"])
    fig.update_xaxes(title_text="")
    p3.plotly_chart(fig, use_container_width=True)

    st.caption("说明：以单边换手率计算")


def show_stats_compare(df: pd.DataFrame, **kwargs):
    """显示多组策略回测的绩效对比

    :param df: 策略回测结果, WeightBacktest 的 stats 数据汇总成的 DataFrame，用 name 列区分不同的策略
    """
    if "name" in df.columns:
        df.set_index("name", inplace=True)

    stats_cols = [
        "绝对收益",
        "年化",
        "夏普",
        "最大回撤",
        "卡玛",
        "年化波动率",
        "下行波动率",
        "非零覆盖",
        "新高间隔",
        "新高占比",
        "回撤风险",
        "交易胜率",
        "单笔收益",
        "持仓K线数",
        "多头占比",
        "空头占比",
        "波动比",
        "盈亏平衡点",
        "日胜率",
        "日盈亏比",
        "日赢面",
        "品种数量",
        "开始日期",
        "结束日期",
    ]

    # 只选择存在的列
    existing_cols = [col for col in stats_cols if col in df.columns]
    df = df[existing_cols].copy()

    # 应用样式
    df = apply_stats_style(df)
    st.dataframe(df, use_container_width=True)


def show_symbol_penalty(df: pd.DataFrame, n=3, **kwargs):
    """依次删除策略收益最高的N个品种，对比收益变化

    :param df: 策略权重数据
    :param n: 删除的品种数量
    :return: None
    """
    WeightBacktest = safe_import_weight_backtest()

    digits = kwargs.get("digits", 2)
    fee_rate = kwargs.get("fee_rate", 0.0)
    weight_type = kwargs.get("weight_type", "ts")
    yearly_days = kwargs.get("yearly_days", 252)

    n = min(n, df["symbol"].nunique() - 1)
    dfw = df[["dt", "symbol", "weight", "price"]].copy()
    wb_map = {}
    wb1 = WeightBacktest(dfw.copy(), digits=digits, fee_rate=fee_rate, weight_type=weight_type, yearly_days=yearly_days)
    wb_map["原始策略"] = wb1

    for i in list(range(1, n + 1)):
        top_symbols = wb1.get_top_symbols(i, kind="profit")
        dfw1 = dfw[~dfw["symbol"].isin(top_symbols)].copy().reset_index(drop=True)
        wb2 = WeightBacktest(
            dfw1.copy(), digits=digits, fee_rate=fee_rate, weight_type=weight_type, yearly_days=yearly_days
        )
        wb_map[f"删除：{';'.join(top_symbols)}"] = wb2

    dfs = []
    dailys = []
    for k, wb in wb_map.items():
        s = wb.stats.copy()
        s["name"] = k
        dfs.append(s)

        d = wb.daily_return.copy()
        d = d[["date", "total"]].copy()
        d["name"] = k
        dailys.append(d)

    dfd = pd.concat(dailys, ignore_index=True)
    dfd["date"] = pd.to_datetime(dfd["date"])
    dfd = pd.pivot_table(dfd, index="date", columns="name", values="total", aggfunc="sum")

    from .returns import show_cumulative_returns

    show_cumulative_returns(dfd, fig_title="删除表现最佳品种后的累计收益对比")

    dfs = pd.DataFrame(dfs)
    show_stats_compare(dfs)
