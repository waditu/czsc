"""
持仓权重分析相关的可视化组件

包含权重时序分析、分布分析、累积分布函数、绝对仓位分析等功能
"""
import streamlit as st
import plotly.graph_objects as go
from .base import generate_component_key


def show_weight_ts(df, key=None, **kwargs):
    """展示权重时序分析
    
    :param df: 包含dt、symbol、weight列的DataFrame
    :param key: str, 可选，组件的唯一标识符，默认自动生成
    :param kwargs:
        - title: str, 图表标题，默认为 "策略持仓权重分布分析"
        - height: int, 图表高度，默认为 800
        - show_position_count: bool, 是否显示持仓数量，默认为 True
    """
    from czsc.utils.plot_weight import plot_weight_time_series
    
    title = kwargs.get("title", "策略持仓权重分布分析")
    height = kwargs.get("height", 800)
    show_position_count = kwargs.get("show_position_count", True)
    
    fig = plot_weight_time_series(df, title=title, height=height, show_position_count=show_position_count)
    
    # 修复暗色主题支持
    fig.update_layout(
        plot_bgcolor=None,  # 使用 Streamlit 主题
        paper_bgcolor=None,  # 使用 Streamlit 主题
        font=dict(color=None)  # 使用 Streamlit 主题
    )
    
    if key is None:
        key = generate_component_key(df, prefix="w_ts", title=title, show_position_count=show_position_count, height=height)
    
    st.plotly_chart(fig, key=key, width='stretch')


def show_weight_dist(df, key=None, **kwargs):
    """展示权重分布分析（直方图与核密度估计）
    
    :param df: 包含dt、symbol、weight列的DataFrame
    :param key: str, 可选，组件的唯一标识符，默认自动生成
    :param kwargs:
        - title: str, 图表标题，默认为 "仓位分布直方图与核密度估计"
        - height: int, 图表高度，默认为 800
        - width: int, 图表宽度，默认为 900
    """
    from czsc.utils.plot_weight import plot_weight_histogram_kde
    
    title = kwargs.get("title", "仓位分布直方图与核密度估计")
    height = kwargs.get("height", 800)
    width = kwargs.get("width", 900)
    
    fig = plot_weight_histogram_kde(df, title=title, height=height, width=width)
    
    # 修复暗色主题支持
    fig.update_layout(
        plot_bgcolor=None,  # 使用 Streamlit 主题
        paper_bgcolor=None,  # 使用 Streamlit 主题
        font=dict(color=None)  # 使用 Streamlit 主题
    )
    
    if key is None:
        key = generate_component_key(df, prefix="w_dist", title=title, height=height, width=width)
    
    st.plotly_chart(fig, key=key, width='stretch')


def show_weight_cdf(df, key=None, **kwargs):
    """展示权重累积分布函数(CDF)
    
    :param df: 包含dt、symbol、weight列的DataFrame
    :param key: str, 可选，组件的唯一标识符，默认自动生成
    :param kwargs:
        - title: str, 图表标题，默认为 "仓位分布累积分布函数(CDF)对比"
        - height: int, 图表高度，默认为 600
        - width: int, 图表宽度，默认为 800
        - show_percentiles: bool, 是否显示分位数参考线，默认为 True
    """
    from czsc.utils.plot_weight import plot_weight_cdf
    
    title = kwargs.get("title", "仓位分布累积分布函数(CDF)对比")
    height = kwargs.get("height", 600)
    width = kwargs.get("width", 800)
    show_percentiles = kwargs.get("show_percentiles", True)
    
    fig = plot_weight_cdf(df, title=title, height=height, width=width, show_percentiles=show_percentiles)
    
    # 修复暗色主题支持
    fig.update_layout(
        plot_bgcolor=None,  # 使用 Streamlit 主题
        paper_bgcolor=None,  # 使用 Streamlit 主题
        font=dict(color=None)  # 使用 Streamlit 主题
    )
    
    if key is None:
        key = generate_component_key(df, prefix="w_cdf", title=title, show_percentiles=show_percentiles, height=height, width=width)
    
    st.plotly_chart(fig, key=key, width='stretch')


def show_weight_abs(df, key=None, **kwargs):
    """展示绝对仓位详细分析
    
    :param df: 包含dt、symbol、weight列的DataFrame
    :param key: str, 可选，组件的唯一标识符，默认自动生成
    :param kwargs:
        - title: str, 图表标题，默认为 "绝对仓位详细分析图表"
        - height: int, 图表高度，默认为 900
        - width: int, 图表宽度，默认为 1000
        - ma_windows: list, 移动平均线窗口列表，默认为 [5, 20, 60]
        - volatility_window: int, 波动率计算窗口，默认为 20
    """
    from czsc.utils.plot_weight import plot_absolute_position_analysis
    
    title = kwargs.get("title", "绝对仓位详细分析图表")
    height = kwargs.get("height", 900)
    width = kwargs.get("width", 1000)
    ma_windows = kwargs.get("ma_windows", [5, 20, 60])
    volatility_window = kwargs.get("volatility_window", 20)
    
    fig = plot_absolute_position_analysis(
        df, title=title, height=height, width=width, 
        ma_windows=ma_windows, volatility_window=volatility_window
    )
    
    # 修复暗色主题支持
    fig.update_layout(
        plot_bgcolor=None,  # 使用 Streamlit 主题
        paper_bgcolor=None,  # 使用 Streamlit 主题
        font=dict(color=None)  # 使用 Streamlit 主题
    )
    
    if key is None:
        key = generate_component_key(df, prefix="w_abs", title=title, ma_windows=ma_windows, volatility_window=volatility_window, height=height, width=width)
    
    st.plotly_chart(fig, key=key, width='stretch')


__all__ = [
    'show_weight_ts',
    'show_weight_dist',
    'show_weight_cdf',
    'show_weight_abs',
]
