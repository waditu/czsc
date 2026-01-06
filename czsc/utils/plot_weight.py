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
from typing import Dict, List, Tuple


def calculate_turnover_stats(dfw: pd.DataFrame) -> Dict:
    """
    计算策略换手率统计指标
    
    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        
    Returns:
        包含换手率统计指标的字典：
        - 单边换手率: 总换手量
        - 年化单边换手率: 年化换手率（假设252个交易日）
        - 日均换手率: 平均每日换手率
        - 最大单日换手率: 单日最大换手率
        - 最小单日换手率: 单日最小换手率
        - 换手率标准差: 换手率波动性
        - 日换手详情: 每日换手率DataFrame
    """
    df = dfw.copy()
    df['dt'] = pd.to_datetime(df['dt'])
    
    # 按品种和时间透视表
    dft = pd.pivot_table(df, index='dt', columns='symbol', values='weight', aggfunc='sum')
    dft = dft.fillna(0)
    
    # 计算换手率（相邻时间点的权重变化绝对值之和）
    df_turns = dft.diff().abs().sum(axis=1).reset_index()
    df_turns.columns = ['dt', 'turnover']
    
    # 修正第一个时间点的换手率（diff无法计算第一个点）
    sdt = df['dt'].min()
    initial_turnover = df[df['dt'] == sdt]['weight'].abs().sum()
    df_turns.loc[df_turns['dt'] == sdt, 'turnover'] = initial_turnover
    
    # 按日期重采样为日频
    df_daily = df_turns.set_index('dt').resample('D').sum().reset_index()
    
    # 计算统计指标
    total_turnover = df_daily['turnover'].sum()
    trading_days = len(df_daily)
    annual_turnover = total_turnover / trading_days * 252 if trading_days > 0 else 0
    
    return {
        '单边换手率': round(total_turnover, 4),
        '年化单边换手率': round(annual_turnover, 2),
        '日均换手率': round(df_daily['turnover'].mean(), 4),
        '最大单日换手率': round(df_daily['turnover'].max(), 4),
        '最小单日换手率': round(df_daily['turnover'].min(), 4),
        '换手率标准差': round(df_daily['turnover'].std(), 4),
        '交易日数量': trading_days,
        '日换手详情': df_daily
    }


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
    short_total = dfw[dfw['weight'] < 0].groupby('dt')['weight'].sum()
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


def plot_turnover_overview(dfw: pd.DataFrame, title: str = "策略换手率分析总览", height: int = 600) -> go.Figure:
    """
    绘制策略换手率总览图 - 一图看懂换手率核心指标
    
    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        title: 图表标题
        height: 图表高度
        
    Returns:
        Plotly图表对象
    """
    # 计算换手率统计
    stats = calculate_turnover_stats(dfw)
    df_daily = stats['日换手详情']
    
    # 创建图表
    fig = go.Figure()
    
    # 添加换手率时序曲线
    fig.add_trace(go.Scatter(
        x=df_daily['dt'],
        y=df_daily['turnover'],
        mode='lines+markers',
        name='日换手率',
        line=dict(color='#2E86C1', width=2),
        marker=dict(size=4),
        hovertemplate='<b>日期</b>: %{x}<br><b>换手率</b>: %{y:.4f}<extra></extra>'
    ))
    
    # 添加平均换手率参考线
    avg_turnover = stats['日均换手率']
    fig.add_hline(
        y=avg_turnover, 
        line_dash="dash", 
        line_color="#E74C3C",
        annotation_text=f"日均换手: {avg_turnover:.4f}",
        annotation_position="right"
    )
    
    # 添加关键指标注释
    metrics_text = (
        f"<b>核心指标</b><br>"
        f"年化换手率: {stats['年化单边换手率']:.2f} 倍<br>"
        f"日均换手率: {stats['日均换手率']:.4f}<br>"
        f"最大单日: {stats['最大单日换手率']:.4f}<br>"
        f"换手标准差: {stats['换手率标准差']:.4f}"
    )
    
    fig.add_annotation(
        x=0.02, y=0.98,
        text=metrics_text,
        showarrow=False,
        xref='paper', yref='paper',
        xanchor='left', yanchor='top',
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#2E86C1',
        borderwidth=2,
        font=dict(size=12)
    )
    
    # 更新布局
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title="日期",
        yaxis_title="换手率",
        height=height,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified'
    )
    
    # 更新坐标轴样式
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12)
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12)
    )
    
    return fig


def plot_turnover_cost_analysis(dfw: pd.DataFrame,
                               fee_rate: float = 0.0003,
                               title: str = "换手成本分析",
                               height: int = 500) -> go.Figure:
    """
    绘制换手成本分析图 - 评估交易成本对收益的影响
    
    Args:
        dfw: 包含dt、symbol、weight列的DataFrame
        fee_rate: 单边交易费率（默认0.03%）
        title: 图表标题
        height: 图表高度
        
    Returns:
        Plotly图表对象
    """
    # 计算换手率统计
    stats = calculate_turnover_stats(dfw)
    df_daily = stats['日换手详情']
    
    # 计算累计换手成本
    df_daily['cumulative_cost'] = (df_daily['turnover'] * fee_rate).cumsum()
    
    fig = go.Figure()
    
    # 添加累计成本曲线
    fig.add_trace(go.Scatter(
        x=df_daily['dt'],
        y=df_daily['cumulative_cost'],
        mode='lines',
        name=f'累计成本 (费率{fee_rate*100:.3f}%)',
        line=dict(color='#C0392B', width=2),
        fill='tozeroy',
        fillcolor='rgba(192, 57, 43, 0.1)',
        hovertemplate='<b>日期</b>: %{x}<br><b>累计成本</b>: %{y:.4f}<extra></extra>'
    ))
    
    # 添加单日成本柱状图
    fig.add_trace(go.Bar(
        x=df_daily['dt'],
        y=df_daily['turnover'] * fee_rate,
        name='单日成本',
        marker_color='#E74C3C',
        opacity=0.6,
        hovertemplate='<b>日期</b>: %{x}<br><b>单日成本</b>: %{y:.4f}<extra></extra>'
    ))
    
    # 添加成本统计信息
    total_cost = df_daily['turnover'].sum() * fee_rate
    avg_daily_cost = df_daily['turnover'].mean() * fee_rate
    
    cost_text = (
        f"<b>成本分析</b><br>"
        f"总成本: {total_cost:.4f}<br>"
        f"日均成本: {avg_daily_cost:.6f}<br>"
        f"年化成本: {avg_daily_cost * 252:.4f}"
    )
    
    fig.add_annotation(
        x=0.98, y=0.98,
        text=cost_text,
        showarrow=False,
        xref='paper', yref='paper',
        xanchor='right', yanchor='top',
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#C0392B',
        borderwidth=2,
        font=dict(size=11)
    )
    
    # 更新布局
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title="日期",
        yaxis_title="成本（比例）",
        height=height,
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
    
    # 更新坐标轴样式
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12)
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgray',
        linecolor='black',
        linewidth=2,
        tickfont=dict(size=12)
    )
    
    return fig


if __name__ == "__main__":
    import czsc
    
    print("欢迎使用策略持仓分析工具！")
    print("=" * 50)
    
    # 生成模拟数据
    print("正在生成模拟数据...")
    dfw = czsc.mock.generate_klines_with_weights()
    dfw = dfw[['dt', 'symbol', 'weight']].copy()
    print(f"数据生成完成：{len(dfw)} 条记录")
    
    print("\n推荐使用简化版函数：")
    print("1. plot_turnover_overview(dfw) - 换手率总览")
    print("2. plot_positions_simple(dfw) - 持仓分析")
    print("3. plot_turnover_cost_analysis(dfw) - 成本分析")
    
    print("\n传统详细分析函数：")
    print("4. plot_weight_time_series(dfw) - 完整时序分析")
    print("5. plot_weight_histogram_kde(dfw) - 分布统计分析")
    print("6. plot_absolute_position_analysis(dfw) - 绝对仓位详细分析")
    
    # 示例：使用简化函数
    # fig_overview = plot_turnover_overview(dfw)
    # fig_overview.show()
    
    # fig_simple = plot_positions_simple(dfw)
    # fig_simple.show()
    
    # fig_cost = plot_turnover_cost_analysis(dfw)
    # fig_cost.show()