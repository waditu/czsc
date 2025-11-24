"""
输入标准的策略持仓数据，分析换手率、持仓权重的分布

标准的策略持仓数据含有 dt、symbol、weight 三列，样例输入如下：
         dt symbol    weight
0 2010-01-01   AAPL -0.255969
1 2010-01-02   AAPL  0.634864
2 2010-01-03   AAPL -1.000000
3 2010-01-04   AAPL -0.516123
4 2010-01-05   AAPL -0.411114
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
from scipy import stats
from typing import Dict, List


def calculate_weight_stats(dfw: pd.DataFrame) -> pd.DataFrame:
    """
    计算权重统计数据

    Args:
        dfw: 包含dt、symbol、weight列的DataFrame

    Returns:
        包含权重统计的DataFrame
    """
    # 计算各类统计量
    long_total = dfw[dfw['weight'] > 0].groupby('dt')['weight'].sum()
    short_total = dfw[dfw['weight'] < 0].groupby('dt')['weight'].sum().abs()  # 转为正值
    abs_total = dfw.groupby('dt')['weight'].apply(lambda x: x.abs().sum())
    net_total = dfw.groupby('dt')['weight'].sum()
    position_count = dfw[dfw['weight'] != 0].groupby('dt').size()

    # 合并所有统计量
    weight_stats = pd.DataFrame({
        'dt': dfw['dt'].unique(),
        'long_total': long_total,
        'short_total': short_total,
        'abs_total': abs_total,
        'net_total': net_total,
        'position_count': position_count
    }).fillna(0)
    return weight_stats


def plot_weight_time_series(dfw: pd.DataFrame,
                           title: str = "策略持仓权重分布分析",
                           height: int = 800,
                           show_position_count: bool = True) -> go.Figure:
    """
    绘制权重暴露曲线时序图

    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        title: 图表标题
        height: 图表高度
        show_position_count: 是否显示持仓数量

    Returns:
        Plotly图表对象
    """
    # 计算权重统计数据
    weight_stats = calculate_weight_stats(dfw)

    if show_position_count:
        # 创建双子图布局
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('持仓权重分布', '净仓位和持仓数量'),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
        )
    else:
        # 单图布局
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=('持仓权重分布',)
        )

    # 添加多头累计、空头累计、绝对仓位曲线
    fig.add_trace(
        go.Scatter(
            x=weight_stats['dt'],
            y=weight_stats['long_total'],
            mode='lines',
            name='多头累计',
            line=dict(color='green', width=2),
            hovertemplate='<b>%{fullData.name}</b><br>时间: %{x}<br>权重: %{y:.3f}<extra></extra>'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=weight_stats['dt'],
            y=weight_stats['short_total'],
            mode='lines',
            name='空头累计',
            line=dict(color='red', width=2),
            hovertemplate='<b>%{fullData.name}</b><br>时间: %{x}<br>权重: %{y:.3f}<extra></extra>'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=weight_stats['dt'],
            y=weight_stats['abs_total'],
            mode='lines',
            name='绝对仓位',
            line=dict(color='blue', width=2),
            hovertemplate='<b>%{fullData.name}</b><br>时间: %{x}<br>权重: %{y:.3f}<extra></extra>'
        ),
        row=1, col=1
    )

    # 添加净仓位曲线
    if show_position_count:
        fig.add_trace(
            go.Scatter(
                x=weight_stats['dt'],
                y=weight_stats['net_total'],
                mode='lines',
                name='净仓位',
                line=dict(color='purple', width=2),
                hovertemplate='<b>%{fullData.name}</b><br>时间: %{x}<br>净仓位: %{y:.3f}<extra></extra>'
            ),
            row=2, col=1
        )

        # 添加持仓数量柱状图（使用次坐标轴）
        fig.add_trace(
            go.Bar(
                x=weight_stats['dt'],
                y=weight_stats['position_count'],
                name='持仓数量',
                marker_color='orange',
                opacity=0.7,
                hovertemplate='<b>%{fullData.name}</b><br>时间: %{x}<br>数量: %{y}<extra></extra>'
            ),
            row=2, col=1,
            secondary_y=True
        )

    # 更新布局
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=height,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    # 更新x轴
    fig.update_xaxes(
        title_text="时间",
        title_font=dict(size=14),
        tickfont=dict(size=12)
    )

    # 更新y轴
    fig.update_yaxes(
        title_text="权重",
        title_font=dict(size=14),
        tickfont=dict(size=12),
        row=1, col=1
    )

    if show_position_count:
        fig.update_yaxes(
            title_text="净仓位",
            title_font=dict(size=14),
            tickfont=dict(size=12),
            row=2, col=1
        )

        fig.update_yaxes(
            title_text="持仓数量",
            title_font=dict(size=14),
            tickfont=dict(size=12),
            row=2, col=1,
            secondary_y=True
        )

    return fig


def plot_weight_histogram_kde(dfw: pd.DataFrame,
                             title: str = "仓位分布直方图与核密度估计",
                             height: int = 800,
                             width: int = 900) -> go.Figure:
    """
    绘制仓位分布直方图与核密度估计

    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        title: 图表标题
        height: 图表高度
        width: 图表宽度

    Returns:
        Plotly图表对象
    """
    # 计算权重统计数据
    weight_stats = calculate_weight_stats(dfw)
    # 创建子图布局
    fig_hist = make_subplots(
        rows=2, cols=2,
        subplot_titles=('多头仓位分布', '空头仓位分布', '净仓位分布', '绝对仓位分布'),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    # 准备仓位数据
    position_data = {
        '多头仓位': weight_stats['long_total'],
        '空头仓位': weight_stats['short_total'],  # 已经是正值
        '净仓位': weight_stats['net_total'],
        '绝对仓位': weight_stats['abs_total']
    }

    positions = ['多头仓位', '空头仓位', '净仓位', '绝对仓位']
    position_indices = [(1,1), (1,2), (2,1), (2,2)]
    colors = ['#2E8B57', '#DC143C', '#4682B4', '#FF8C00']

    for i, (position_type, (row, col)) in enumerate(zip(positions, position_indices)):
        data = position_data[position_type]
        color = colors[i]

        # 计算核密度估计
        kde = stats.gaussian_kde(data)
        x_range = np.linspace(data.min(), data.max(), 200)
        kde_values = kde(x_range)

        # 添加直方图
        fig_hist.add_trace(
            go.Histogram(
                x=data,
                nbinsx=50,
                name=f'{position_type}_直方图',
                marker_color=color,
                opacity=0.7,
                histnorm='probability density',  # 使用概率密度
                showlegend=False
            ),
            row=row, col=col
        )

        # 添加核密度估计曲线
        fig_hist.add_trace(
            go.Scatter(
                x=x_range,
                y=kde_values,
                mode='lines',
                name=f'{position_type}_KDE',
                line=dict(color='black', width=2),
                showlegend=False
            ),
            row=row, col=col
        )

        # 添加统计信息文本
        mean_val = data.mean()
        median_val = data.median()
        std_val = data.std()

        fig_hist.add_annotation(
            x=data.max() * 0.7,
            y=kde_values.max() * 0.8,
            text=f'均值: {mean_val:.3f}<br>中位数: {median_val:.3f}<br>标准差: {std_val:.3f}',
            showarrow=False,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.8)",
            row=row, col=col
        )

    # 更新布局
    fig_hist.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        height=height,
        width=width,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    # 更新所有子图的坐标轴
    for i in range(1, 3):
        for j in range(1, 3):
            fig_hist.update_xaxes(
                title_text="仓位值" if i == 2 else "",
                linecolor='black',
                linewidth=1,
                tickfont=dict(size=10),
                row=i, col=j
            )
            fig_hist.update_yaxes(
                title_text="密度" if j == 1 else "",
                linecolor='black',
                linewidth=1,
                tickfont=dict(size=10),
                row=i, col=j
            )

    return fig_hist


def plot_weight_cdf(dfw: pd.DataFrame,
                   title: str = "仓位分布累积分布函数(CDF)对比",
                   height: int = 600,
                   width: int = 800,
                   show_percentiles: bool = True) -> go.Figure:
    """
    绘制仓位分布累积分布函数图

    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        title: 图表标题
        height: 图表高度
        width: 图表宽度
        show_percentiles: 是否显示分位数参考线

    Returns:
        Plotly图表对象
    """
    # 计算权重统计数据
    weight_stats = calculate_weight_stats(dfw)
    # 创建累积分布函数图
    fig_cdf = go.Figure()

    # 准备仓位数据
    position_data = {
        '多头仓位': weight_stats['long_total'],
        '空头仓位': weight_stats['short_total'],  # 已经是正值
        '净仓位': weight_stats['net_total'],
        '绝对仓位': weight_stats['abs_total']
    }

    colors = ['#2E8B57', '#DC143C', '#4682B4', '#FF8C00']

    for i, (position_type, data) in enumerate(position_data.items()):
        color = colors[i]

        # 计算累积分布函数
        sorted_data = np.sort(data)
        n = len(sorted_data)
        cdf_y = np.arange(1, n + 1) / n

        # 添加CDF曲线
        fig_cdf.add_trace(go.Scatter(
            x=sorted_data,
            y=cdf_y,
            mode='lines',
            name=position_type,
            line=dict(color=color, width=2.5),
            hovertemplate='<b>%{fullData.name}</b><br>仓位: %{x:.3f}<br>累积概率: %{y:.3f}<extra></extra>'
        ))

    # 添加参考线
    if show_percentiles:
        fig_cdf.add_hline(y=0.25, line_dash="dash", line_color="gray", annotation_text="25%分位数")
        fig_cdf.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="中位数")
        fig_cdf.add_hline(y=0.75, line_dash="dash", line_color="gray", annotation_text="75%分位数")

    # 更新布局
    fig_cdf.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title="仓位值",
        yaxis_title="累积概率",
        height=height,
        width=width,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    # 更新坐标轴
    fig_cdf.update_xaxes(
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray'
    )

    fig_cdf.update_yaxes(
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        range=[0, 1]
    )

    return fig_cdf


def plot_absolute_position_analysis(dfw: pd.DataFrame,
                                  title: str = "绝对仓位详细分析图表",
                                  height: int = 900,
                                  width: int = 1000,
                                  ma_windows: List[int] = [5, 20, 60],
                                  volatility_window: int = 20) -> go.Figure:
    """
    绘制绝对仓位详细分析图

    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        title: 图表标题
        height: 图表高度
        width: 图表宽度
        ma_windows: 移动平均线窗口列表
        volatility_window: 波动率计算窗口

    Returns:
        Plotly图表对象
    """
    # 计算权重统计数据
    weight_stats = calculate_weight_stats(dfw)
    # 创建子图布局
    fig_abs = make_subplots(
        rows=3, cols=1,
        subplot_titles=('绝对仓位时序曲线', '滚动统计指标', '仓位分布统计'),
        vertical_spacing=0.08,
        row_heights=[0.5, 0.3, 0.2]
    )

    # 1. 绝对仓位时序曲线（主图）
    fig_abs.add_trace(
        go.Scatter(
            x=weight_stats['dt'],
            y=weight_stats['abs_total'],
            mode='lines',
            name='绝对仓位',
            line=dict(color='blue', width=2),
            hovertemplate='<b>绝对仓位</b><br>时间: %{x}<br>仓位: %{y:.3f}<extra></extra>'
        ),
        row=1, col=1
    )

    # 添加移动平均线
    colors_ma = ['orange', 'green', 'red']
    for window, color in zip(ma_windows, colors_ma):
        if len(weight_stats) >= window:
            ma_values = weight_stats['abs_total'].rolling(window=window).mean()
            fig_abs.add_trace(
                go.Scatter(
                    x=weight_stats['dt'],
                    y=ma_values,
                    mode='lines',
                    name=f'MA{window}',
                    line=dict(color=color, width=1.5, dash='dot'),
                    hovertemplate=f'<b>MA{window}</b><br>时间: %{{x}}<br>平均值: %{{y:.3f}}<extra></extra>'
                ),
                row=1, col=1
            )

    # 添加统计参考线
    mean_abs = weight_stats['abs_total'].mean()
    median_abs = weight_stats['abs_total'].median()

    # 添加水平参考线
    fig_abs.add_shape(
        type="line",
        x0=weight_stats['dt'].min(),
        y0=mean_abs,
        x1=weight_stats['dt'].max(),
        y1=mean_abs,
        line=dict(color="red", width=2, dash="dash"),
        row=1, col=1
    )

    # 计算注释位置（使用90%时间位置）
    annotation_x = weight_stats['dt'].min() + (weight_stats['dt'].max() - weight_stats['dt'].min()) * 0.9
    fig_abs.add_annotation(
        x=annotation_x,
        y=mean_abs,
        text=f"均值: {mean_abs:.3f}",
        showarrow=False,
        font=dict(color="red"),
        row=1, col=1
    )

    fig_abs.add_shape(
        type="line",
        x0=weight_stats['dt'].min(),
        y0=median_abs,
        x1=weight_stats['dt'].max(),
        y1=median_abs,
        line=dict(color="green", width=2, dash="dash"),
        row=1, col=1
    )

    fig_abs.add_annotation(
        x=annotation_x,
        y=median_abs,
        text=f"中位数: {median_abs:.3f}",
        showarrow=False,
        font=dict(color="green"),
        row=1, col=1
    )

    # 2. 滚动统计指标（第二幅图）
    # 计算滚动标准差和波动率
    rolling_std = weight_stats['abs_total'].rolling(window=volatility_window).std()
    rolling_volatility = (rolling_std / weight_stats['abs_total'].rolling(window=volatility_window).mean()) * 100

    fig_abs.add_trace(
        go.Scatter(
            x=weight_stats['dt'],
            y=rolling_volatility,
            mode='lines',
            name=f'{volatility_window}日滚动波动率(%)',
            line=dict(color='purple', width=2),
            hovertemplate='<b>滚动波动率</b><br>时间: %{x}<br>波动率: %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )

    # 3. 仓位分布直方图（第三幅图）
    fig_abs.add_trace(
        go.Histogram(
            x=weight_stats['abs_total'],
            nbinsx=50,
            name='绝对仓位分布',
            marker_color='lightblue',
            opacity=0.7,
            showlegend=False
        ),
        row=3, col=1
    )

    # 更新布局
    fig_abs.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=height,
        width=width,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified'
    )

    # 更新坐标轴
    # 主图坐标轴
    fig_abs.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=1, col=1
    )

    fig_abs.update_yaxes(
        title_text="绝对仓位大小",
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=1, col=1
    )

    # 波动率图坐标轴
    fig_abs.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=2, col=1
    )

    fig_abs.update_yaxes(
        title_text="波动率 (%)",
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=2, col=1
    )

    # 分布图坐标轴
    fig_abs.update_xaxes(
        title_text="绝对仓位值",
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=3, col=1
    )

    fig_abs.update_yaxes(
        title_text="频数",
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12),
        row=3, col=1
    )

    return fig_abs


# 使用示例
if __name__ == "__main__":
    import czsc

    # 生成模拟数据
    dfw = czsc.mock.generate_klines_with_weights()
    dfw = dfw[['dt', 'symbol', 'weight']].copy()

    # 或者单独使用某个函数
    # fig_time = plot_weight_time_series(dfw)
    # fig_hist = plot_weight_histogram_kde(dfw)
    # fig_cdf = plot_weight_cdf(dfw)
    # fig_abs = plot_absolute_position_analysis(dfw)
    # fig_time.show()