"""
相关性分析相关的可视化组件

包含相关性矩阵、截面IC、时序相关性、协整分析等功能
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from .base import ensure_datetime_index


def show_correlation(df, **kwargs):
    """展示相关性矩阵热力图

    :param df: pd.DataFrame，数据源
    :param kwargs:
        - method: str，相关性计算方法，支持 pearson, kendall, spearman，默认为 pearson
        - cmap: str，颜色映射，默认为 RdBu_r
        - fig_title: str，图表标题，默认为"相关性矩阵"
        - annotate: bool，是否在热力图上显示数值，默认为 True
    """
    method = kwargs.get("method", "pearson")
    cmap = kwargs.get("cmap", "RdBu_r")
    fig_title = kwargs.get("fig_title", "相关性矩阵")
    annotate = kwargs.get("annotate", True)

    # 只保留数值列
    df_numeric = df.select_dtypes(include=[np.number])
    if df_numeric.empty:
        st.error("数据中没有数值列，无法计算相关性")
        return

    # 计算相关性矩阵
    corr_matrix = df_numeric.corr(method=method)

    # 创建热力图
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale=cmap,
        text=corr_matrix.round(3).astype(str) if annotate else None,
        texttemplate="%{text}" if annotate else "",
        showscale=True,
        zmin=-1,
        zmax=1
    ))

    fig.update_layout(
        title=fig_title,
        xaxis_title="",
        yaxis_title="",
        width=600,
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # 显示统计信息
    with st.expander("相关性统计信息", expanded=False):
        # 获取上三角矩阵的相关系数（排除对角线）
        corr_values = corr_matrix.where(np.triu(np.ones_like(corr_matrix, dtype=bool), k=1))
        corr_values = corr_values.stack().dropna()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("平均相关性", f"{corr_values.mean():.3f}")
        c2.metric("最大相关性", f"{corr_values.max():.3f}")
        c3.metric("最小相关性", f"{corr_values.min():.3f}")
        
        st.dataframe(corr_matrix.style.background_gradient(cmap=cmap, vmin=-1, vmax=1), use_container_width=True)


def show_sectional_ic(df, factors, target_col, **kwargs):
    """展示截面IC分析

    :param df: pd.DataFrame, 数据源
    :param factors: list, 因子列名列表
    :param target_col: str, 目标列名
    :param kwargs:
        - dt_col: str, 日期列名，默认为 'dt'
        - show_cumsum_ic: bool, 是否显示累计IC，默认为 True
        - ic_method: str, IC计算方法，支持 pearson, kendall, spearman，默认为 spearman
    """
    dt_col = kwargs.get("dt_col", "dt")
    show_cumsum_ic = kwargs.get("show_cumsum_ic", True)
    ic_method = kwargs.get("ic_method", "spearman")

    if dt_col not in df.columns:
        st.error(f"数据中没有找到日期列 '{dt_col}'")
        return

    if target_col not in df.columns:
        st.error(f"数据中没有找到目标列 '{target_col}'")
        return

    missing_factors = [f for f in factors if f not in df.columns]
    if missing_factors:
        st.error(f"数据中没有找到因子列: {missing_factors}")
        return

    df[dt_col] = pd.to_datetime(df[dt_col])
    df = df.sort_values(dt_col)

    # 按日期分组计算IC
    ic_results = []
    for dt, group in df.groupby(dt_col):
        row = {"dt": dt}
        for factor in factors:
            valid_data = group[[factor, target_col]].dropna()
            if len(valid_data) > 5:  # 至少需要5个观测值
                ic_value = valid_data[factor].corr(valid_data[target_col], method=ic_method)
                row[factor] = ic_value
            else:
                row[factor] = np.nan
        ic_results.append(row)

    df_ic = pd.DataFrame(ic_results)
    df_ic = df_ic.set_index("dt")

    # 显示IC统计
    ic_stats = df_ic.describe()
    st.subheader("IC统计信息")
    st.dataframe(ic_stats.style.background_gradient(cmap="RdYlGn_r"), use_container_width=True)

    # 绘制IC时序图
    fig = px.line(df_ic.reset_index(), x="dt", y=factors, title="IC时序图")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="IC值")
    st.plotly_chart(fig, use_container_width=True)

    # 显示累计IC
    if show_cumsum_ic:
        df_cumsum_ic = df_ic.cumsum()
        fig_cumsum = px.line(df_cumsum_ic.reset_index(), x="dt", y=factors, title="累计IC")
        fig_cumsum.update_xaxes(title="")
        fig_cumsum.update_yaxes(title="累计IC")
        st.plotly_chart(fig_cumsum, use_container_width=True)


def show_ts_rolling_corr(df, col1, col2, window=60, **kwargs):
    """展示两个时间序列的滚动相关性

    :param df: pd.DataFrame，必须有datetime索引
    :param col1: str，列名1
    :param col2: str，列名2
    :param window: int，滚动窗口大小，默认为60
    :param kwargs:
        - method: str，相关性计算方法，默认为 pearson
        - sub_title: str，子标题
    """
    df = ensure_datetime_index(df)
    
    if col1 not in df.columns or col2 not in df.columns:
        st.error(f"数据中没有找到列 '{col1}' 或 '{col2}'")
        return

    method = kwargs.get("method", "pearson")
    sub_title = kwargs.get("sub_title", f"{col1} 与 {col2} 的{window}期滚动相关性")

    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 计算滚动相关性
    rolling_corr = df[col1].rolling(window=window).corr(df[col2])
    rolling_corr = rolling_corr.dropna()

    # 绘图
    fig = px.line(x=rolling_corr.index, y=rolling_corr.values, 
                  title=f"{col1} vs {col2} 滚动相关性 (窗口={window})")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="相关系数")
    
    # 添加参考线
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_hline(y=0.5, line_dash="dash", line_color="green", opacity=0.5)
    fig.add_hline(y=-0.5, line_dash="dash", line_color="red", opacity=0.5)
    
    st.plotly_chart(fig, use_container_width=True)

    # 显示统计信息
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均相关性", f"{rolling_corr.mean():.3f}")
    c2.metric("最大相关性", f"{rolling_corr.max():.3f}")
    c3.metric("最小相关性", f"{rolling_corr.min():.3f}")
    c4.metric("标准差", f"{rolling_corr.std():.3f}")


def show_ts_self_corr(df, col, max_lag=20, **kwargs):
    """展示时间序列的自相关性

    :param df: pd.DataFrame，必须有datetime索引
    :param col: str，列名
    :param max_lag: int，最大滞后期数，默认为20
    :param kwargs:
        - sub_title: str，子标题
        - show_partial: bool，是否显示偏自相关，默认为False
    """
    from statsmodels.tsa.stattools import acf, pacf
    
    df = ensure_datetime_index(df)
    
    if col not in df.columns:
        st.error(f"数据中没有找到列 '{col}'")
        return

    sub_title = kwargs.get("sub_title", f"{col} 的自相关分析")
    show_partial = kwargs.get("show_partial", False)

    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 计算自相关
    data = df[col].dropna()
    autocorr = acf(data, nlags=max_lag, fft=False)
    lags = list(range(max_lag + 1))

    # 绘制自相关图
    fig = go.Figure()
    fig.add_trace(go.Bar(x=lags, y=autocorr, name="自相关"))
    
    # 添加置信区间
    confidence_interval = 1.96 / np.sqrt(len(data))
    fig.add_hline(y=confidence_interval, line_dash="dash", line_color="red", 
                  annotation_text=f"95%置信上界 ({confidence_interval:.3f})")
    fig.add_hline(y=-confidence_interval, line_dash="dash", line_color="red",
                  annotation_text=f"95%置信下界 ({-confidence_interval:.3f})")
    
    fig.update_layout(title="自相关函数 (ACF)", xaxis_title="滞后期", yaxis_title="自相关系数")
    st.plotly_chart(fig, use_container_width=True)

    # 偏自相关
    if show_partial:
        partial_autocorr = pacf(data, nlags=max_lag)
        
        fig_pacf = go.Figure()
        fig_pacf.add_trace(go.Bar(x=lags, y=partial_autocorr, name="偏自相关"))
        fig_pacf.add_hline(y=confidence_interval, line_dash="dash", line_color="red")
        fig_pacf.add_hline(y=-confidence_interval, line_dash="dash", line_color="red")
        fig_pacf.update_layout(title="偏自相关函数 (PACF)", xaxis_title="滞后期", yaxis_title="偏自相关系数")
        st.plotly_chart(fig_pacf, use_container_width=True)


def show_cointegration(df, col1, col2, **kwargs):
    """展示两个时间序列的协整检验

    :param df: pd.DataFrame，必须有datetime索引
    :param col1: str，列名1
    :param col2: str，列名2
    :param kwargs:
        - sub_title: str，子标题
        - show_spread: bool，是否显示价差序列，默认为True
    """
    from statsmodels.tsa.stattools import coint
    
    df = ensure_datetime_index(df)
    
    if col1 not in df.columns or col2 not in df.columns:
        st.error(f"数据中没有找到列 '{col1}' 或 '{col2}'")
        return

    sub_title = kwargs.get("sub_title", f"{col1} 与 {col2} 的协整分析")
    show_spread = kwargs.get("show_spread", True)

    if sub_title:
        st.subheader(sub_title, divider="rainbow")

    # 准备数据
    data = df[[col1, col2]].dropna()
    if len(data) < 30:
        st.error("数据点太少，无法进行协整检验（至少需要30个观测值）")
        return

    # 协整检验
    coint_stat, p_value, critical_values = coint(data[col1], data[col2])
    
    # 显示检验结果
    c1, c2, c3 = st.columns(3)
    c1.metric("协整统计量", f"{coint_stat:.4f}")
    c2.metric("P值", f"{p_value:.4f}")
    c3.metric("是否协整", "是" if p_value < 0.05 else "否")
    
    # 显示临界值
    st.write("**临界值:**")
    crit_df = pd.DataFrame([critical_values], columns=["1%", "5%", "10%"])
    st.dataframe(crit_df, use_container_width=True)
    
    # 显示价差序列
    if show_spread:
        # 简单的线性回归计算价差
        from sklearn.linear_model import LinearRegression
        X = data[col1].values.reshape(-1, 1)
        y = data[col2].values
        
        reg = LinearRegression().fit(X, y)
        spread = y - reg.predict(X)
        
        spread_df = pd.DataFrame({
            "dt": data.index,
            "价差": spread
        })
        
        fig = px.line(spread_df, x="dt", y="价差", title="价差序列")
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.add_hline(y=spread.std(), line_dash="dash", line_color="red", opacity=0.5)
        fig.add_hline(y=-spread.std(), line_dash="dash", line_color="red", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)


def show_corr_graph(df, threshold=0.3, **kwargs):
    """展示相关性网络图

    :param df: pd.DataFrame，数据源
    :param threshold: float，显示边的相关性阈值，默认为0.3
    :param kwargs:
        - method: str，相关性计算方法，默认为 pearson
        - layout: str，布局算法，默认为 spring
    """
    import networkx as nx
    import plotly.graph_objects as go
    
    method = kwargs.get("method", "pearson")
    
    # 只保留数值列
    df_numeric = df.select_dtypes(include=[np.number])
    if df_numeric.empty:
        st.error("数据中没有数值列，无法计算相关性")
        return

    # 计算相关性矩阵
    corr_matrix = df_numeric.corr(method=method)
    
    # 创建网络图
    G = nx.Graph()
    
    # 添加节点
    for col in corr_matrix.columns:
        G.add_node(col)
    
    # 添加边（只添加高于阈值的相关性）
    for i, col1 in enumerate(corr_matrix.columns):
        for j, col2 in enumerate(corr_matrix.columns):
            if i < j:  # 避免重复边
                corr_val = abs(corr_matrix.loc[col1, col2])
                if corr_val > threshold:
                    G.add_edge(col1, col2, weight=corr_val, 
                              color='red' if corr_matrix.loc[col1, col2] > 0 else 'blue')
    
    if len(G.edges()) == 0:
        st.warning(f"没有找到相关性高于阈值 {threshold} 的变量对")
        return
    
    # 计算布局
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # 准备绘图数据
    edge_x = []
    edge_y = []
    edge_colors = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_colors.append(G[edge[0]][edge[1]]['color'])
    
    node_x = []
    node_y = []
    node_text = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
    
    # 创建图形
    fig = go.Figure()
    
    # 添加边
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y,
                            line=dict(width=2, color='gray'),
                            hoverinfo='none',
                            mode='lines',
                            name='相关性'))
    
    # 添加节点
    fig.add_trace(go.Scatter(x=node_x, y=node_y,
                            mode='markers+text',
                            hoverinfo='text',
                            text=node_text,
                            textposition="middle center",
                            marker=dict(size=20, color='lightblue'),
                            name='变量'))
    
    fig.update_layout(title=f"相关性网络图 (阈值={threshold})",
                     showlegend=False,
                     hovermode='closest',
                     margin=dict(b=20,l=5,r=5,t=40),
                     annotations=[dict(text="红色边表示正相关，蓝色边表示负相关",
                                     showarrow=False,
                                     xref="paper", yref="paper",
                                     x=0.005, y=-0.002,
                                     xanchor='left', yanchor='bottom',
                                     font=dict(size=12))],
                     xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                     yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    
    st.plotly_chart(fig, use_container_width=True)


def show_symbols_corr(df, symbols, **kwargs):
    """展示多个品种之间的相关性分析

    :param df: pd.DataFrame，包含多个品种的价格数据
    :param symbols: list，品种代码列表
    :param kwargs:
        - method: str，相关性计算方法，默认为 pearson
        - price_col: str，价格列名，默认为 'close'
        - dt_col: str，日期列名，默认为 'dt'
        - show_heatmap: bool，是否显示热力图，默认为 True
        - show_clustermap: bool，是否显示聚类图，默认为 False
    """
    method = kwargs.get("method", "pearson")
    price_col = kwargs.get("price_col", "close")
    dt_col = kwargs.get("dt_col", "dt")
    show_heatmap = kwargs.get("show_heatmap", True)
    show_clustermap = kwargs.get("show_clustermap", False)

    if dt_col not in df.columns:
        st.error(f"数据中没有找到日期列 '{dt_col}'")
        return

    if price_col not in df.columns:
        st.error(f"数据中没有找到价格列 '{price_col}'")
        return

    # 数据预处理
    df[dt_col] = pd.to_datetime(df[dt_col])
    
    # 透视表，构造品种-时间的价格矩阵
    price_matrix = df.pivot_table(index=dt_col, columns='symbol', values=price_col)
    
    # 只保留指定的品种
    available_symbols = [s for s in symbols if s in price_matrix.columns]
    if not available_symbols:
        st.error(f"数据中没有找到任何指定的品种: {symbols}")
        return
    
    if len(available_symbols) < len(symbols):
        missing_symbols = [s for s in symbols if s not in available_symbols]
        st.warning(f"以下品种在数据中未找到: {missing_symbols}")
    
    price_matrix = price_matrix[available_symbols]
    
    # 计算收益率（可选）
    if kwargs.get("use_returns", False):
        price_matrix = price_matrix.pct_change().dropna()
    
    # 计算相关性矩阵
    corr_matrix = price_matrix.corr(method=method)
    
    st.write(f"**品种数量**: {len(available_symbols)}, **数据期间**: {price_matrix.index.min().strftime('%Y-%m-%d')} ~ {price_matrix.index.max().strftime('%Y-%m-%d')}")
    
    # 显示热力图
    if show_heatmap:
        show_correlation(price_matrix, method=method, fig_title=f"品种相关性矩阵 ({method})")
    
    # 显示聚类图
    if show_clustermap:
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.spatial.distance import squareform
            
            # 计算距离矩阵
            distance_matrix = 1 - corr_matrix.abs()
            condensed_distances = squareform(distance_matrix)
            
            # 层次聚类
            linkage_matrix = linkage(condensed_distances, method='ward')
            
            # 绘制树状图
            fig = go.Figure()
            
            dend = dendrogram(linkage_matrix, labels=corr_matrix.index.tolist(), no_plot=True)
            
            # 这里简化处理，只显示聚类结果的文字描述
            st.write("**层次聚类结果**:")
            st.write("聚类功能需要进一步开发，当前显示相关性统计:")
            
            # 显示相关性统计
            corr_values = corr_matrix.where(np.triu(np.ones_like(corr_matrix, dtype=bool), k=1))
            corr_values = corr_values.stack().dropna()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("平均相关性", f"{corr_values.mean():.3f}")
            c2.metric("最高相关性", f"{corr_values.max():.3f}")
            c3.metric("最低相关性", f"{corr_values.min():.3f}")
            
        except ImportError:
            st.warning("无法导入scipy，跳过聚类分析") 