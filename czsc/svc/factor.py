"""
因子分析相关的可视化组件

包含特征收益、因子分层、因子数值分布、事件收益分析等功能
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from .base import safe_import_daily_performance, apply_stats_style, ensure_datetime_index


def show_feature_returns(df, features, ret_col="returns", **kwargs):
    """展示特征收益分析

    :param df: pd.DataFrame, 数据源
    :param features: list, 特征列名列表
    :param ret_col: str, 收益列名，默认为 'returns'
    :param kwargs:
        - method: str, 相关性计算方法，默认为 'spearman'
        - min_periods: int, 最小样本数，默认为100
        - show_correlation: bool, 是否展示相关性热力图，默认为True
    """
    method = kwargs.get("method", "spearman")
    min_periods = kwargs.get("min_periods", 100)
    show_correlation = kwargs.get("show_correlation", True)

    if ret_col not in df.columns:
        st.error(f"数据中没有找到收益列 '{ret_col}'")
        return

    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        st.error(f"数据中没有找到特征列: {missing_features}")
        return

    # 计算特征与收益的相关性
    correlations = []
    for feature in features:
        data = df[[feature, ret_col]].dropna()
        if len(data) >= min_periods:
            corr = data[feature].corr(data[ret_col], method=method)
            correlations.append({
                "特征": feature,
                "相关系数": corr,
                "样本数": len(data),
                "绝对相关系数": abs(corr)
            })

    if not correlations:
        st.warning("没有足够的数据计算相关性")
        return

    corr_df = pd.DataFrame(correlations)
    corr_df = corr_df.sort_values("绝对相关系数", ascending=False)

    # 显示排序后的相关性
    st.subheader("特征与收益的相关性排序")
    corr_styled = corr_df.style.background_gradient(cmap="RdYlGn_r", subset=["相关系数"])
    corr_styled = corr_styled.background_gradient(cmap="RdYlGn_r", subset=["绝对相关系数"])
    corr_styled = corr_styled.format({"相关系数": "{:.4f}", "绝对相关系数": "{:.4f}", "样本数": "{:.0f}"})
    st.dataframe(corr_styled, use_container_width=True, hide_index=True)

    # 绘制相关性条形图
    fig = px.bar(corr_df, x="特征", y="相关系数", 
                 title=f"特征与{ret_col}的相关性",
                 color="相关系数", color_continuous_scale="RdYlGn_r")
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    # 显示特征间相关性热力图
    if show_correlation and len(features) > 1:
        st.subheader("特征间相关性矩阵")
        feature_corr = df[features].corr(method=method)
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=feature_corr.values,
            x=feature_corr.columns,
            y=feature_corr.index,
            colorscale="RdBu_r",
            text=feature_corr.round(3).astype(str),
            texttemplate="%{text}",
            showscale=True,
            zmin=-1,
            zmax=1
        ))
        
        fig_heatmap.update_layout(title="特征间相关性热力图", width=600, height=500)
        st.plotly_chart(fig_heatmap, use_container_width=True)


def show_factor_layering(df, factor_col, ret_col, n_layers=5, **kwargs):
    """展示因子分层分析

    :param df: pd.DataFrame, 数据源
    :param factor_col: str, 因子列名
    :param ret_col: str, 收益列名
    :param n_layers: int, 分层数量，默认为5
    :param kwargs:
        - method: str, 分层方法，'qcut'（等频）或'cut'（等距），默认为'qcut'
        - show_cumulative: bool, 是否显示累计收益，默认为True
        - show_distribution: bool, 是否显示因子分布，默认为True
    """
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    method = kwargs.get("method", "qcut")
    show_cumulative = kwargs.get("show_cumulative", True)
    show_distribution = kwargs.get("show_distribution", True)

    if factor_col not in df.columns or ret_col not in df.columns:
        st.error(f"数据中没有找到列 '{factor_col}' 或 '{ret_col}'")
        return

    # 去除缺失值
    data = df[[factor_col, ret_col]].dropna()
    if len(data) < n_layers * 10:  # 每层至少10个观测值
        st.warning(f"数据量太少，建议减少分层数量。当前数据量：{len(data)}")

    # 因子分层
    if method == "qcut":
        data["layer"] = pd.qcut(data[factor_col], q=n_layers, labels=[f"第{i+1}层" for i in range(n_layers)], duplicates="drop")
    else:
        data["layer"] = pd.cut(data[factor_col], bins=n_layers, labels=[f"第{i+1}层" for i in range(n_layers)], duplicates="drop")

    # 计算各层收益统计
    layer_stats = []
    for layer in data["layer"].cat.categories:
        layer_data = data[data["layer"] == layer][ret_col]
        if len(layer_data) > 0:
            stats = daily_performance(layer_data.tolist())
            stats["分层"] = layer
            stats["样本数"] = len(layer_data)
            layer_stats.append(stats)

    if not layer_stats:
        st.error("分层后没有足够的数据")
        return

    stats_df = pd.DataFrame(layer_stats).set_index("分层")
    
    # 显示分层统计
    st.subheader(f"{factor_col} 分层收益分析")
    stats_styled = apply_stats_style(stats_df)
    st.dataframe(stats_styled, use_container_width=True)

    # 显示分层收益对比
    layer_returns = data.groupby("layer")[ret_col].mean()
    fig_bar = px.bar(x=layer_returns.index.astype(str), y=layer_returns.values,
                     title="各层平均收益对比",
                     labels={"x": "分层", "y": "平均收益"})
    st.plotly_chart(fig_bar, use_container_width=True)

    # 显示累计收益曲线（如果有时间信息）
    if show_cumulative and "dt" in df.columns:
        st.subheader("分层累计收益曲线")
        df_temp = df.copy()
        df_temp = df_temp.dropna(subset=[factor_col, ret_col])
        
        # 重新分层
        if method == "qcut":
            df_temp["layer"] = pd.qcut(df_temp[factor_col], q=n_layers, labels=[f"第{i+1}层" for i in range(n_layers)], duplicates="drop")
        else:
            df_temp["layer"] = pd.cut(df_temp[factor_col], bins=n_layers, labels=[f"第{i+1}层" for i in range(n_layers)], duplicates="drop")
        
        df_temp["dt"] = pd.to_datetime(df_temp["dt"])
        df_temp = df_temp.sort_values("dt")
        
        # 计算各层累计收益
        cumulative_returns = []
        for layer in df_temp["layer"].cat.categories:
            layer_data = df_temp[df_temp["layer"] == layer]
            layer_cumret = layer_data.groupby("dt")[ret_col].mean().cumsum()
            layer_cumret.name = layer
            cumulative_returns.append(layer_cumret)
        
        if cumulative_returns:
            cumret_df = pd.concat(cumulative_returns, axis=1).fillna(method="ffill")
            fig_cumret = px.line(cumret_df, title="分层累计收益曲线")
            st.plotly_chart(fig_cumret, use_container_width=True)

    # 显示因子分布
    if show_distribution:
        st.subheader(f"{factor_col} 分布分析")
        fig_hist = px.histogram(data, x=factor_col, color="layer", 
                               title=f"{factor_col} 在各层的分布")
        st.plotly_chart(fig_hist, use_container_width=True)


def show_factor_value(df, factor_col, bins=50, **kwargs):
    """展示因子数值分布

    :param df: pd.DataFrame, 数据源
    :param factor_col: str, 因子列名
    :param bins: int, 直方图箱数，默认为50
    :param kwargs:
        - show_outliers: bool, 是否显示异常值，默认为True
        - percentiles: list, 分位数列表，默认为[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    """
    if factor_col not in df.columns:
        st.error(f"数据中没有找到因子列 '{factor_col}'")
        return

    show_outliers = kwargs.get("show_outliers", True)
    percentiles = kwargs.get("percentiles", [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])

    data = df[factor_col].dropna()
    if len(data) == 0:
        st.error(f"因子 '{factor_col}' 没有有效数据")
        return

    st.subheader(f"{factor_col} 数值分布分析")

    # 基本统计信息
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("观测数", f"{len(data):,.0f}")
    c2.metric("均值", f"{data.mean():.4f}")
    c3.metric("标准差", f"{data.std():.4f}")
    c4.metric("缺失值", f"{df[factor_col].isnull().sum():,.0f}")

    # 分位数信息
    quantiles = data.quantile(percentiles)
    quantile_df = pd.DataFrame({
        "分位数": [f"{p:.1%}" for p in percentiles],
        "数值": quantiles.values
    })
    
    with st.expander("分位数分布", expanded=False):
        st.dataframe(quantile_df.style.format({"数值": "{:.4f}"}), use_container_width=True, hide_index=True)

    # 绘制直方图和箱线图
    col1, col2 = st.columns(2)
    
    with col1:
        fig_hist = px.histogram(df, x=factor_col, nbins=bins, 
                               title=f"{factor_col} 直方图")
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_box = px.box(df, y=factor_col, title=f"{factor_col} 箱线图")
        if not show_outliers:
            fig_box.update_traces(boxpoints=False)
        st.plotly_chart(fig_box, use_container_width=True)

    # 异常值分析
    if show_outliers:
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = data[(data < lower_bound) | (data > upper_bound)]
        if len(outliers) > 0:
            with st.expander(f"异常值分析 (共{len(outliers)}个)", expanded=False):
                st.write(f"**异常值边界**: [{lower_bound:.4f}, {upper_bound:.4f}]")
                st.write(f"**异常值占比**: {len(outliers)/len(data):.2%}")
                
                if len(outliers) <= 100:  # 只显示前100个异常值
                    outlier_df = pd.DataFrame({
                        "序号": range(1, len(outliers)+1),
                        "异常值": outliers.values
                    })
                    st.dataframe(outlier_df.style.format({"异常值": "{:.4f}"}), use_container_width=True, hide_index=True)


def show_event_return(df, event_col, ret_col, **kwargs):
    """展示事件收益分析

    :param df: pd.DataFrame, 数据源
    :param event_col: str, 事件列名（布尔类型或0/1）
    :param ret_col: str, 收益列名
    :param kwargs:
        - pre_periods: int, 事件前观察期数，默认为5
        - post_periods: int, 事件后观察期数，默认为10
        - min_observations: int, 最小观察数，默认为10
    """
    daily_performance = safe_import_daily_performance()
    if daily_performance is None:
        return

    pre_periods = kwargs.get("pre_periods", 5)
    post_periods = kwargs.get("post_periods", 10)
    min_observations = kwargs.get("min_observations", 10)

    if event_col not in df.columns or ret_col not in df.columns:
        st.error(f"数据中没有找到列 '{event_col}' 或 '{ret_col}'")
        return

    # 确保有时间索引
    if "dt" not in df.columns:
        st.error("数据中需要包含 'dt' 时间列")
        return

    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values("dt").reset_index(drop=True)

    # 找出事件发生的时点
    event_mask = (df[event_col] == True) | (df[event_col] == 1)
    event_indices = df[event_mask].index.tolist()

    if len(event_indices) < min_observations:
        st.warning(f"事件发生次数太少（{len(event_indices)}次），建议至少{min_observations}次")
        return

    st.subheader(f"事件收益分析 (事件发生{len(event_indices)}次)")

    # 计算事件前后的累计收益
    event_returns = []
    for event_idx in event_indices:
        start_idx = max(0, event_idx - pre_periods)
        end_idx = min(len(df), event_idx + post_periods + 1)
        
        if end_idx - start_idx >= pre_periods + post_periods:
            window_data = df.iloc[start_idx:end_idx]
            window_returns = window_data[ret_col].values
            
            # 计算相对于事件时点的累计收益
            event_point = pre_periods
            relative_returns = np.zeros(len(window_returns))
            for i in range(len(window_returns)):
                if i <= event_point:
                    relative_returns[i] = np.sum(window_returns[:i+1])
                else:
                    relative_returns[i] = np.sum(window_returns[event_point:i+1])
            
            event_returns.append(relative_returns)

    if len(event_returns) == 0:
        st.error("没有足够的数据进行事件分析")
        return

    # 计算平均事件收益
    event_returns_array = np.array(event_returns)
    mean_returns = np.mean(event_returns_array, axis=0)
    std_returns = np.std(event_returns_array, axis=0)
    
    # 时间轴（相对于事件时点）
    time_axis = list(range(-pre_periods, post_periods + 1))
    
    # 绘制事件研究图
    fig = go.Figure()
    
    # 添加平均累计收益
    fig.add_trace(go.Scatter(
        x=time_axis, y=mean_returns,
        mode='lines+markers', name='平均累计收益',
        line=dict(color='blue', width=2)
    ))
    
    # 添加置信区间
    upper_bound = mean_returns + 1.96 * std_returns / np.sqrt(len(event_returns))
    lower_bound = mean_returns - 1.96 * std_returns / np.sqrt(len(event_returns))
    
    fig.add_trace(go.Scatter(
        x=time_axis, y=upper_bound,
        fill=None, mode='lines', line_color='rgba(0,100,80,0)',
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter(
        x=time_axis, y=lower_bound,
        fill='tonexty', mode='lines', line_color='rgba(0,100,80,0)',
        name='95%置信区间', fillcolor='rgba(0,100,80,0.2)'
    ))
    
    # 添加事件发生时点的垂直线
    fig.add_vline(x=0, line_dash="dash", line_color="red", 
                  annotation_text="事件发生")
    
    fig.update_layout(
        title=f"事件收益分析 (前{pre_periods}期，后{post_periods}期)",
        xaxis_title="相对事件时点的期数",
        yaxis_title="累计收益",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 显示统计信息
    pre_event_return = mean_returns[pre_periods-1] if pre_periods > 0 else 0
    post_event_return = mean_returns[-1]
    event_effect = post_event_return - pre_event_return
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("事件次数", f"{len(event_indices)}")
    c2.metric("事件前累计收益", f"{pre_event_return:.4f}")
    c3.metric("事件后累计收益", f"{post_event_return:.4f}")
    c4.metric("事件效应", f"{event_effect:.4f}")


def show_event_features(df, event_col, feature_cols, **kwargs):
    """展示事件特征分析

    :param df: pd.DataFrame, 数据源
    :param event_col: str, 事件列名
    :param feature_cols: list, 特征列名列表
    :param kwargs:
        - test_method: str, 统计检验方法，'ttest'或'mannwhitney'，默认为'ttest'
        - alpha: float, 显著性水平，默认为0.05
    """
    from scipy import stats
    
    test_method = kwargs.get("test_method", "ttest")
    alpha = kwargs.get("alpha", 0.05)

    if event_col not in df.columns:
        st.error(f"数据中没有找到事件列 '{event_col}'")
        return

    missing_features = [f for f in feature_cols if f not in df.columns]
    if missing_features:
        st.error(f"数据中没有找到特征列: {missing_features}")
        return

    # 分组数据
    event_mask = (df[event_col] == True) | (df[event_col] == 1)
    event_data = df[event_mask]
    non_event_data = df[~event_mask]

    if len(event_data) == 0 or len(non_event_data) == 0:
        st.error("事件组或非事件组为空，无法进行比较")
        return

    st.subheader(f"事件特征分析 (事件组: {len(event_data)}, 非事件组: {len(non_event_data)})")

    # 统计检验结果
    test_results = []
    for feature in feature_cols:
        event_values = event_data[feature].dropna()
        non_event_values = non_event_data[feature].dropna()
        
        if len(event_values) == 0 or len(non_event_values) == 0:
            continue
        
        # 统计检验
        if test_method == "ttest":
            statistic, p_value = stats.ttest_ind(event_values, non_event_values)
            test_name = "T检验"
        else:
            statistic, p_value = stats.mannwhitneyu(event_values, non_event_values, alternative='two-sided')
            test_name = "Mann-Whitney U检验"
        
        result = {
            "特征": feature,
            "事件组均值": event_values.mean(),
            "非事件组均值": non_event_values.mean(),
            "差异": event_values.mean() - non_event_values.mean(),
            "检验统计量": statistic,
            "P值": p_value,
            "显著性": "是" if p_value < alpha else "否"
        }
        test_results.append(result)

    if not test_results:
        st.error("没有足够的数据进行特征比较")
        return

    # 显示检验结果
    results_df = pd.DataFrame(test_results)
    results_styled = results_df.style.background_gradient(cmap="RdYlGn_r", subset=["差异"])
    results_styled = results_styled.background_gradient(cmap="RdYlGn", subset=["P值"])
    results_styled = results_styled.format({
        "事件组均值": "{:.4f}",
        "非事件组均值": "{:.4f}",
        "差异": "{:.4f}",
        "检验统计量": "{:.4f}",
        "P值": "{:.4f}"
    })
    
    st.dataframe(results_styled, use_container_width=True, hide_index=True)
    st.caption(f"检验方法: {test_name}, 显著性水平: {alpha}")

    # 绘制特征分布对比
    for i, feature in enumerate(feature_cols[:4]):  # 最多显示4个特征
        if feature in results_df["特征"].values:
            col1, col2 = st.columns(2)
            
            with col1:
                # 直方图对比
                fig_hist = go.Figure()
                
                event_values = event_data[feature].dropna()
                non_event_values = non_event_data[feature].dropna()
                
                fig_hist.add_trace(go.Histogram(
                    x=event_values, name="事件组", opacity=0.7,
                    nbinsx=30
                ))
                fig_hist.add_trace(go.Histogram(
                    x=non_event_values, name="非事件组", opacity=0.7,
                    nbinsx=30
                ))
                
                fig_hist.update_layout(
                    title=f"{feature} 分布对比",
                    barmode='overlay',
                    xaxis_title=feature,
                    yaxis_title="频数"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # 箱线图对比
                comparison_data = []
                comparison_data.extend([{"group": "事件组", "value": v, "feature": feature} for v in event_values])
                comparison_data.extend([{"group": "非事件组", "value": v, "feature": feature} for v in non_event_values])
                comparison_df = pd.DataFrame(comparison_data)
                
                fig_box = px.box(comparison_df, x="group", y="value", 
                                title=f"{feature} 箱线图对比")
                st.plotly_chart(fig_box, use_container_width=True) 