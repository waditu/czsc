"""
权重回测可视化 Plotly 绘图函数

从 czsc.svc 模块中提取的 WeightBacktest 相关的绘图代码，按功能整理
"""

from typing import Union, Literal, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ==================== 模块级常量 ====================

# 颜色常量
COLOR_DRAWDOWN = "salmon"
COLOR_RETURN = "#34a853"
COLOR_ANNO_GRAY = "rgba(128,128,128,0.5)"
COLOR_ANNO_RED = "red"
COLOR_BORDER = "darkgrey"
COLOR_HEADER_BG = "grey"

# 分位数常量
QUANTILES_DRAWDOWN = [0.05, 0.1, 0.2]
QUANTILES_DRAWDOWN_ANALYSIS = [0.1, 0.3, 0.5]

# Sigma 级别
SIGMA_LEVELS = [-3, -2, -1, 1, 2, 3]

# 月份标签
MONTH_LABELS = [
    '1月', '2月', '3月', '4月', '5月', '6月',
    '7月', '8月', '9月', '10月', '11月', '12月'
]

# 模板类型
TemplateType = Literal['plotly', 'plotly_dark', 'ggplot2', 'seaborn', 'simple_white']


# ==================== 辅助函数 ====================

def _figure_to_html(
    fig: go.Figure,
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """统一处理 Figure 转 HTML 的逻辑

    :param fig: Plotly Figure 对象
    :param to_html: 是否转换为 HTML
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库
    :return: Figure 对象或 HTML 字符串
    """
    if to_html:
        return fig.to_html(include_plotlyjs=include_plotlyjs, full_html=False)
    return fig


def _add_year_boundary_lines(
    fig: go.Figure,
    dates: pd.DatetimeIndex,
    row: Optional[int] = None,
    col: Optional[int] = None,
    line_color: str = "red",
    opacity: float = 0.3,
    line_dash: str = "dash"
) -> None:
    """在图表中添加年度分隔线

    :param fig: Plotly Figure 对象
    :param dates: 日期索引
    :param row: 子图行号（可选）
    :param col: 子图列号（可选）
    :param line_color: 线条颜色
    :param opacity: 透明度
    :param line_dash: 线条样式
    """
    years = dates.year.unique()
    for year in years:
        first_date = dates[dates.year == year].min()
        fig.add_vline(
            x=first_date,
            line_dash=line_dash,
            line_color=line_color,
            opacity=opacity,
            row=row, 
            col=col
        )


def _calculate_drawdown(
    returns: pd.Series,
    fillna: bool = True
) -> pd.DataFrame:
    """计算累计收益和回撤

    :param returns: 收益序列
    :param fillna: 是否填充 NaN 值
    :return: 包含 cum_ret, cum_max, drawdown 的 DataFrame
    """
    df = returns.copy()
    if fillna:
        df = df.fillna(0)
    df = df.sort_index(ascending=True)

    result = pd.DataFrame({
        'cum_ret': df.cumsum(),
        'cum_max': df.cumsum().cummax(),
        'drawdown': df.cumsum() - df.cumsum().cummax()
    })
    return result


def _create_monthly_heatmap_data(
    returns_df: pd.DataFrame,
    ret_col: str
) -> Tuple[pd.DataFrame, float, float]:
    """创建月度热力图所需数据

    :param returns_df: 日收益数据
    :param ret_col: 收益列名
    :return: (透视表, 月胜率, 年胜率)
    """
    df = returns_df[[ret_col]].copy()
    df['year'] = df.index.year
    df['month'] = df.index.month

    monthly_ret = df.groupby(['year', 'month'])[ret_col].sum() * 100
    monthly_ret = monthly_ret.reset_index()
    monthly_ret.columns = ['年份', '月份', '月收益']

    pivot_table = monthly_ret.pivot(index='年份', columns='月份', values='月收益')

    monthly_win_rate = (monthly_ret['月收益'] > 0).mean()
    yearly_ret = monthly_ret.groupby('年份')['月收益'].sum()
    yearly_win_rate = (yearly_ret > 0).mean()

    return pivot_table, monthly_win_rate, yearly_win_rate


def _add_drawdown_annotation(
    fig: go.Figure,
    drawdown_series: pd.Series,
    quantiles: list,
    row: int,
    col: int
) -> None:
    """添加回撤分位数标注线

    :param fig: Plotly Figure 对象
    :param drawdown_series: 回撤序列
    :param quantiles: 分位数列表
    :param row: 子图行号
    :param col: 子图列号
    """
    for quantile in quantiles:
        y_val = drawdown_series.quantile(quantile)
        fig.add_hline(
            y=y_val * 100,
            line_dash="dot",
            annotation_text=f"{quantile * 100:.0f}%: {y_val * 100:.2f}%",
            annotation_position="bottom left",
            line_color=COLOR_ANNO_GRAY,
            line_width=1,
            row=row, col=col
        )


def _add_sigma_lines(
    fig: go.Figure,
    returns_series: pd.Series,
    row: int,
    col: int
) -> None:
    """添加日收益分布的 Sigma 标注线

    :param fig: Plotly Figure 对象
    :param returns_series: 收益序列（百分比）
    :param row: 子图行号
    :param col: 子图列号
    """
    mean_val = returns_series.mean()
    std_val = returns_series.std()

    for sigma in SIGMA_LEVELS:
        val = mean_val + sigma * std_val
        fig.add_vline(
            x=val,
            line_dash="dot",
            line_color=COLOR_ANNO_GRAY,
            line_width=1,
            annotation_text=f"{sigma}σ<br>{val:.2f}%",
            annotation_font=dict(color=COLOR_ANNO_RED, size=10),
            annotation_position="top",
            row=row, col=col
        )


def plot_cumulative_returns(
    dret: pd.DataFrame,
    title: str = "累计收益",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制累计收益曲线

    参考 czsc.svc.returns.show_cumulative_returns

    :param dret: 日收益数据，index为日期，columns为策略收益
    :param title: 图表标题
    :param template: plotly 模板名称，默认 'plotly'（白色主题），可选 'plotly_dark'（深色主题）
    :param to_html: 是否转换为 HTML，默认 False（返回 Figure 对象）
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库，默认 True
    :return: Figure 对象或 HTML 字符串
    """
    assert dret.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型"
    assert dret.index.is_unique, "df 的索引必须唯一"
    assert dret.index.is_monotonic_increasing, "df 的索引必须单调递增"

    df_cumsum = dret.cumsum()
    fig = px.line(
        df_cumsum,
        y=df_cumsum.columns.to_list(),
        title=title,
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig.update_xaxes(title="")

    # 添加年度分隔线
    _add_year_boundary_lines(fig, df_cumsum.index)

    fig.update_layout(
        hovermode="x unified",
        template=template,
        margin=dict(l=0, r=0, b=0, t=40),
        legend=dict(orientation="h", y=-0.1, xanchor="center", x=0.5)
    )

    # 仅显示 total 的曲线，其他的曲线隐藏
    for trace in fig.data:
        if trace.name != 'total':
            trace.visible = 'legendonly'

    return _figure_to_html(fig, to_html, include_plotlyjs)


def plot_drawdown_analysis(
    dret: pd.DataFrame,
    ret_col: str = "total",
    title: str = "回撤分析",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制回撤分析图

    参考 czsc.svc.returns.show_drawdowns

    :param dret: 日收益数据，包含 ret_col 列
    :param ret_col: 收益列名
    :param title: 图表标题
    :param template: plotly 模板名称，默认 'plotly'（白色主题），可选 'plotly_dark'（深色主题）
    :param to_html: 是否转换为 HTML，默认 False（返回 Figure 对象）
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库，默认 True
    :return: Figure 对象或 HTML 字符串
    """
    # 计算回撤数据
    df_drawdown = _calculate_drawdown(dret[ret_col])

    fig = go.Figure()

    # 回撤曲线
    fig.add_trace(go.Scatter(
        x=df_drawdown.index,
        y=df_drawdown["drawdown"] * 100,  # 转为百分比
        fillcolor=COLOR_DRAWDOWN,
        line=dict(color=COLOR_DRAWDOWN),
        fill="tozeroy",
        mode="lines",
        name="回撤",
        opacity=0.5
    ))

    # 累计收益曲线
    fig.add_trace(go.Scatter(
        x=df_drawdown.index,
        y=df_drawdown["cum_ret"],
        mode="lines",
        name="累计收益",
        yaxis="y2",
        opacity=0.8,
        line=dict(color=COLOR_RETURN)
    ))

    fig.update_layout(
        yaxis2=dict(title="累计收益", overlaying="y", side="right"),
        margin=dict(l=0, r=0, t=0, b=0),
        title=title,
        xaxis_title="",
        yaxis_title="净值回撤 (%)",
        legend_title="回撤分析",
        hovermode="x unified",
        template=template
    )

    # 添加分位数线
    for quantile in QUANTILES_DRAWDOWN_ANALYSIS:
        y_val = df_drawdown["drawdown"].quantile(quantile)
        fig.add_hline(
            y=y_val * 100,
            line_dash="dot",
            line_color=f"rgba(52,168,83,0.5)",
            line_width=1
        )

    return _figure_to_html(fig, to_html, include_plotlyjs)


def plot_daily_return_distribution(
    dret: pd.DataFrame,
    ret_col: str = "total",
    title: str = "日收益分布",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制日收益分布直方图

    :param dret: 日收益数据，包含 ret_col 列
    :param ret_col: 收益列名
    :param title: 图表标题
    :param template: plotly 模板名称，默认 'plotly'（白色主题），可选 'plotly_dark'（深色主题）
    :param to_html: 是否转换为 HTML，默认 False（返回 Figure 对象）
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库，默认 True
    :return: Figure 对象或 HTML 字符串
    """
    daily_returns = (dret[ret_col] * 100).reset_index()
    daily_returns.columns = ["dt", "日收益"]

    fig = px.histogram(daily_returns, x="日收益", nbins=50, title=title)
    fig.update_xaxes(title="日收益 (%)")
    fig.update_yaxes(title="频数")

    fig.update_layout(
        template=template,
        margin=dict(l=0, r=0, b=0, t=40),
        bargap=0.1,
        hovermode="x unified"
    )

    return _figure_to_html(fig, to_html, include_plotlyjs)


def plot_monthly_heatmap(
    dret: pd.DataFrame,
    ret_col: str = "total",
    title: str = "月度收益热力图",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制月度收益热力图

    :param dret: 日收益数据，index为日期
    :param ret_col: 收益列名
    :param title: 图表标题
    :param template: plotly 模板名称，默认 'plotly'（白色主题），可选 'plotly_dark'（深色主题）
    :param to_html: 是否转换为 HTML，默认 False（返回 Figure 对象）
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库，默认 True
    :return: Figure 对象或 HTML 字符串
    """
    # 创建月度热力图数据
    pivot_table, _, _ = _create_monthly_heatmap_data(dret, ret_col)

    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=MONTH_LABELS,
        y=pivot_table.index,
        colorscale='RdYlGn_r',
        colorbar=dict(title="日收益 (%)"),
        text=pivot_table.values,
        texttemplate="%{text:.2f}%",
        textfont={"size": 10},
        hovertemplate=" %{y}<br>%{x}<br>收益: %{z:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="月份",
        yaxis_title="年份",
        template=template,
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return _figure_to_html(fig, to_html, include_plotlyjs)


def get_performance_metrics_cards(stats: dict) -> list:
    """从WeightBacktest.stats中提取核心绩效指标，用于HTML报告中的指标卡
    
    :param stats: WeightBacktest.stats 字典
    :return: 指标列表
    """
    metrics = [
        {"label": "年化收益率", "value": f"{stats.get('年化', 0):.2%}", "is_positive": stats.get('年化', 0) > 0},
        {"label": "单笔收益(BP)", "value": f"{stats.get('单笔收益', 0):.2f}", "is_positive": stats.get('单笔收益', 0) > 0},
        {"label": "交易胜率", "value": f"{stats.get('交易胜率', 0):.2%}", "is_positive": stats.get('交易胜率', 0) > 0.5},
        {"label": "持仓K线数", "value": f"{stats.get('持仓K线数', 0):.0f}", "is_positive": True},
        {"label": "最大回撤", "value": f"{stats.get('最大回撤', 0):.2%}", "is_positive": stats.get('最大回撤', 0) < 0.1},
        {"label": "年化", "value": f"{stats.get('年化', 0):.2%}", "is_positive": stats.get('年化', 0) > 0},
        {"label": "夏普", "value": f"{stats.get('夏普', 0):.2f}", "is_positive": stats.get('夏普', 0) > 1},
        {"label": "卡玛", "value": f"{stats.get('卡玛', 0):.2f}", "is_positive": stats.get('卡玛', 0) > 1},
        {"label": "年化波动率", "value": f"{stats.get('年化波动率', 0):.2%}", "is_positive": stats.get('年化波动率', 0) < 0.2},
        {"label": "多头占比", "value": f"{stats.get('多头占比', 0):.2%}", "is_positive": True},
        {"label": "空头占比", "value": f"{stats.get('空头占比', 0):.2%}", "is_positive": True},
    ]
    return metrics


def plot_backtest_stats(
    dret: pd.DataFrame,
    ret_col: str = "total",
    title: str = "",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制回测统计概览图（3图布局：上1下2）

    1. 第一行：回撤分析（包含累计收益），跨两列
    2. 第二行：左边是日收益分布，右边是月度收益热力图

    :param dret: 日收益数据，index为日期
    :param ret_col: 收益列名
    :param title: 图表标题
    :param template: plotly 模板名称
    :param to_html: 是否转换为 HTML
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库
    :return: Figure 对象或 HTML 字符串
    """
    # 创建 subplot，第一行跨两列
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("收益回撤分析", "日收益分布", "月度收益热力图"),
        vertical_spacing=0.1,
        horizontal_spacing=0.05,
        specs=[[{"secondary_y": True, "colspan": 2}, None],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # 1. 收益回撤分析 (Top, spanning 2 columns)
    df_drawdown = _calculate_drawdown(dret[ret_col])

    fig.add_trace(
        go.Scatter(
            x=df_drawdown.index,
            y=df_drawdown["drawdown"] * 100,
            fillcolor=COLOR_DRAWDOWN,
            line=dict(color=COLOR_DRAWDOWN),
            fill="tozeroy",
            mode="lines",
            name="回撤曲线",
            opacity=0.5,
            legendgroup="1"
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_drawdown.index,
            y=df_drawdown["cum_ret"],
            mode="lines",
            name="累计收益",
            opacity=0.8,
            line=dict(color=COLOR_RETURN),
            legendgroup="1"
        ),
        row=1, col=1, secondary_y=True
    )

    # 添加回撤分位数线
    _add_drawdown_annotation(fig, df_drawdown["drawdown"], QUANTILES_DRAWDOWN, row=1, col=1)

    # 添加年度分隔线
    _add_year_boundary_lines(fig, dret.index, row=1, col=1)

    # 2. 日收益分布 (Bottom Left)
    daily_returns = (dret[ret_col] * 100)
    fig.add_trace(
        go.Histogram(x=daily_returns, nbinsx=50, name="日收益分布", showlegend=False),
        row=2, col=1
    )

    # 添加 Sigma 线
    _add_sigma_lines(fig, daily_returns, row=2, col=1)

    # 3. 月度收益热力图 (Bottom Right)
    pivot_table, monthly_win_rate, yearly_win_rate = _create_monthly_heatmap_data(dret, ret_col)

    fig.add_trace(
        go.Heatmap(
            z=pivot_table.values,
            x=MONTH_LABELS,
            y=pivot_table.index,
            colorscale='RdYlGn_r',
            showscale=True,
            colorbar=dict(title="收益(%)", len=0.45, y=0.2),
            name="月收益热力图",
            # title=f"月收益热力图（月胜率: {monthly_win_rate:.1%}，年胜率: {yearly_win_rate:.1%})",
            text=pivot_table.values,
            texttemplate="%{text:.2f}%",
            textfont={"size": 9},
            hovertemplate=" %{y}<br>%{x}<br>收益: %{z:.2f}%<extra></extra>"
        ),
        row=2, col=2
    )

    # 添加胜率标注
    fig.add_annotation(
        text=f"<b>月胜率</b>: {monthly_win_rate:.1%}<br><b>年胜率</b>: {yearly_win_rate:.1%}",
        xref="x domain", yref="y domain",
        x=1.1, y=0.0,
        showarrow=False,
        font=dict(size=11, color="white"),
        bgcolor="rgba(0,0,0,0.6)",
        bordercolor="rgba(255,255,255,0.3)",
        borderwidth=1,
        borderpad=5,
        row=2, col=2
    )

    # 更新布局
    fig.update_layout(
        title=title,
        template=template,
        height=800,
        margin=dict(l=20, r=20, b=20, t=60),
        hovermode="x unified",
        showlegend=True
    )

    # 更新坐标轴标签
    fig.update_yaxes(title_text="回撤 (%)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="累计收益", row=1, col=1, secondary_y=True)

    fig.update_xaxes(title_text="日收益 (%)", row=2, col=1)
    fig.update_yaxes(title_text="频数", row=2, col=1)
    fig.update_yaxes(title_text="年份", row=2, col=2)

    return _figure_to_html(fig, to_html, include_plotlyjs)


def plot_colored_table(
    df: pd.DataFrame,
    title: str = "策略绩效统计",
    template: TemplateType = "plotly_dark",
    float_fmt: str = ".2f",
    to_html: bool = False,
    include_plotlyjs: bool = True,
    **kwargs
) -> Union[go.Figure, str]:
    """绘制带有列独立热力图颜色的表格

    :param df: 统计数据 DataFrame
    :param title: 图表标题
    :param template: plotly 模板
    :param float_fmt: 浮点数格式化精度
    :param to_html: 是否返回 HTML
    :param include_plotlyjs: 是否包含 plotly.js
    :param kwargs:
        - good_high_columns: list, 指定哪些列是数值越大越好
        - row_height: int, 行高，默认 30
        - border_color: str, 边框颜色，默认 'darkgrey'
        - header_bgcolor: str, 表头背景色，默认 'grey'
    :return:
    """
    # 准备表头
    headers = df.columns.tolist()
    if df.index.name:
        headers.insert(0, df.index.name)
    else:
        headers.insert(0, "Index")

    good_high_columns = kwargs.get("good_high_columns", None)
    row_height = kwargs.get("row_height", 30)
    border_color = kwargs.get("border_color", COLOR_BORDER)
    header_bgcolor = kwargs.get("header_bgcolor", COLOR_HEADER_BG)

    # 准备数据和颜色
    cell_values = []
    cell_colors = []

    # 处理索引列
    cell_values.append(df.index.tolist())
    cell_colors.append([header_bgcolor] * len(df))

    # 处理数据列
    for col in df.columns:
        series = df[col]

        # 格式化数值
        if pd.api.types.is_float_dtype(series):
            if "%" in str(col) or "率" in str(col) or "比" in str(col):
                formatted_vals = series.apply(lambda x: f"{x:.2%}")
            else:
                formatted_vals = series.apply(lambda x: f"{x:{float_fmt}}")
            cell_values.append(formatted_vals)
        else:
            cell_values.append(series.tolist())

        # 计算颜色
        if pd.api.types.is_numeric_dtype(series):
            is_good_high = str(col) in good_high_columns if good_high_columns is not None else True

            min_val, max_val = series.min(), series.max()
            if min_val == max_val:
                colors = ['rgba(0,0,0,0)'] * len(series)
            else:
                norm = (series - min_val) / (max_val - min_val)
                sample_vals = 1 - norm if is_good_high else norm
                colors = px.colors.sample_colorscale("RdYlGn_r", sample_vals)

            cell_colors.append(colors)
        else:
            cell_colors.append(['rgba(0,0,0,0)'] * len(series))

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color=header_bgcolor,
            align='center',
            font=dict(color='white', size=12),
            height=row_height,
            line=dict(color=border_color, width=1)
        ),
        cells=dict(
            values=cell_values,
            fill_color=cell_colors,
            align='center',
            font=dict(color='white', size=12),
            height=row_height,
            line=dict(color=border_color, width=1)
        )
    )])

    fig.update_layout(
        title=title,
        template=template,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return _figure_to_html(fig, to_html, include_plotlyjs)


def plot_long_short_comparison(
    dailys_pivot: pd.DataFrame,
    stats_df: pd.DataFrame,
    title: str = "多空收益对比",
    template: TemplateType = "plotly",
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """绘制多空收益对比图（累计收益曲线 + 绩效指标对比表）

    :param dailys_pivot: 透视表格式的日收益数据，index为日期，columns为策略名，values为收益率
    :param stats_df: 绩效指标对比表，每行代表一个策略的指标
    :param title: 图表标题
    :param template: plotly 模板名称
    :param to_html: 是否转换为 HTML
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库
    :return: Figure 对象或 HTML 字符串
    """
    # 创建 2x1 子图（上下布局），指定第二个子图为 table 类型
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("累计收益曲线对比", "绩效指标对比"),
        vertical_spacing=0.12,
        row_heights=[0.55, 0.45],
        specs=[[{"type": "xy"}], [{"type": "table"}]]
    )

    # ========== 上图：累计收益曲线 ==========
    df_cumsum = dailys_pivot.cumsum()
    for col in df_cumsum.columns:
        fig.add_trace(
            go.Scatter(
                x=df_cumsum.index,
                y=df_cumsum[col],
                name=col,
                mode='lines',
            ),
            row=1, col=1
        )

    # 添加年度分隔线
    _add_year_boundary_lines(fig, df_cumsum.index, row=1, col=1, line_color="gray", opacity=0.5)

    # ========== 下图：使用 plot_colored_table 绘制绩效对比表 ==========
    # 选择关键指标列
    key_cols = [
        "策略名称", "年化", "夏普", "卡玛", "最大回撤",
        "年化波动率", "交易胜率", "单笔收益", "持仓K线数", "多头占比", "空头占比"
    ]

    # 过滤存在的列
    available_cols = [col for col in key_cols if col in stats_df.columns]
    table_df = stats_df[available_cols].copy()

    # 设置策略名称为索引（如果存在）
    if "策略名称" in table_df.columns:
        table_df = table_df.set_index("策略名称")

    # 调用 plot_colored_table 生成表格图表
    table_fig = plot_colored_table(
        table_df,
        title="",
        template=template,
        float_fmt=".2f",
        to_html=False,
        good_high_columns=["年化", "夏普", "卡玛", "交易胜率", "单笔收益"]
    )

    # 将表格的 trace 添加到主图中
    for trace in table_fig.data:
        fig.add_trace(trace, row=2, col=1)

    # ========== 更新布局 ==========
    fig.update_layout(
        title=title,
        template=template,
        height=1200,
        margin=dict(l=20, r=20, b=20, t=60),
        hovermode="x unified",
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0)')
    )

    # 更新坐标轴标签
    fig.update_yaxes(title_text="累计收益", row=1, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)

    return _figure_to_html(fig, to_html, include_plotlyjs)
