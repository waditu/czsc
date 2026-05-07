"""
因子分析相关的 Streamlit 可视化组件

本模块面向单因子的常见分析场景，提供如下交互式组件：

1. :func:`show_feature_returns`：批量评估特征/因子与目标收益的相关性，并可绘制
   特征间相关性热力图；
2. :func:`show_factor_layering`：按 ``qcut`` / ``cut`` 对因子分层，统计每层日收益
   绩效与累计收益曲线，验证因子单调性；
3. :func:`show_factor_value`：分析因子的数值分布、分位数及异常值情况；
4. :func:`show_event_return`：经典事件研究法，绘制事件前后的累计收益与置信区间；
5. :func:`show_event_features`：对事件组与非事件组的特征做均值差异与显著性检验。

所有组件遵循统一的 Streamlit 风格，并通过 :func:`generate_component_key` 自动生成
组件 key，避免在同一页面多次复用时冲突。
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .base import apply_stats_style, generate_component_key
from wbt import daily_performance


def show_feature_returns(df, features, ret_col="returns", key=None, **kwargs):
    """展示特征收益分析

    针对每个特征列，计算其与目标收益列的相关系数（默认 Spearman），按绝对值排序后
    展示，并通过条形图与热力图直观呈现特征强度与特征间相关性。

    :param df: pd.DataFrame，数据源；至少包含 ``features`` 与 ``ret_col`` 列
    :param features: list，特征列名列表
    :param ret_col: str，收益列名，默认 ``"returns"``
    :param key: str，可选；组件基础标识符，每个图表会自动追加后缀
    :param kwargs: 其他参数
        - method: str，相关性计算方法，默认 ``"spearman"``
        - min_periods: int，最小样本数，特征样本不足该值时被跳过，默认 100
        - show_correlation: bool，是否展示特征间相关性热力图，默认 True
    :return: None；结果直接写入 Streamlit 页面
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

    # 逐个特征计算与目标收益的相关性，记录样本数与绝对相关系数用于排序
    correlations = []
    for feature in features:
        data = df[[feature, ret_col]].dropna()
        if len(data) >= min_periods:
            corr = data[feature].corr(data[ret_col], method=method)
            correlations.append({"特征": feature, "相关系数": corr, "样本数": len(data), "绝对相关系数": abs(corr)})

    if not correlations:
        st.warning("没有足够的数据计算相关性")
        return

    corr_df = pd.DataFrame(correlations)
    corr_df = corr_df.sort_values("绝对相关系数", ascending=False)

    # 展示按绝对相关系数排序的明细表
    st.subheader("特征与收益的相关性排序")
    corr_styled = corr_df.style.background_gradient(cmap="RdYlGn_r", subset=["相关系数"])
    corr_styled = corr_styled.background_gradient(cmap="RdYlGn_r", subset=["绝对相关系数"])
    corr_styled = corr_styled.format({"相关系数": "{:.4f}", "绝对相关系数": "{:.4f}", "样本数": "{:.0f}"})
    st.dataframe(corr_styled, width="stretch", hide_index=True)

    # 自动生成组件基础 key，确保多次调用不冲突
    if key is None:
        key = generate_component_key(df, prefix="feat_ret", features=features, ret_col=ret_col, method=method)

    # 条形图：特征 vs. 相关系数
    fig = px.bar(
        corr_df,
        x="特征",
        y="相关系数",
        title=f"特征与{ret_col}的相关性",
        color="相关系数",
        color_continuous_scale="RdYlGn_r",
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, key=f"{key}_bar", width="stretch")

    # 当特征数量大于 1 时，绘制特征间相关性热力图，便于发现共线性
    if show_correlation and len(features) > 1:
        st.subheader("特征间相关性矩阵")
        feature_corr = df[features].corr(method=method)

        fig_heatmap = go.Figure(
            data=go.Heatmap(
                z=feature_corr.values,
                x=feature_corr.columns,
                y=feature_corr.index,
                colorscale="RdBu_r",
                text=feature_corr.round(3).astype(str),
                texttemplate="%{text}",
                showscale=True,
                zmin=-1,
                zmax=1,
            )
        )

        fig_heatmap.update_layout(title="特征间相关性热力图", width=600, height=500)
        st.plotly_chart(fig_heatmap, key=f"{key}_heatmap", width="stretch")


def show_factor_layering(df, factor_col, ret_col, n_layers=5, key=None, **kwargs):
    """展示因子分层分析

    按 ``qcut``（等频）或 ``cut``（等距）将因子分成 ``n_layers`` 层，分别计算各层
    的日收益绩效与平均收益，并可绘制累计收益曲线与因子分布直方图。

    :param df: pd.DataFrame，数据源
    :param factor_col: str，因子列名
    :param ret_col: str，收益列名
    :param n_layers: int，分层数量，默认 5
    :param key: str，可选；组件基础标识符
    :param kwargs: 其他参数
        - method: str，分层方法，``'qcut'`` 或 ``'cut'``，默认 ``'qcut'``
        - show_cumulative: bool，是否绘制累计收益曲线（要求 df 包含 ``dt`` 列），默认 True
        - show_distribution: bool，是否绘制因子分布直方图，默认 True
    :return: None
    """
    method = kwargs.get("method", "qcut")
    show_cumulative = kwargs.get("show_cumulative", True)
    show_distribution = kwargs.get("show_distribution", True)

    if factor_col not in df.columns or ret_col not in df.columns:
        st.error(f"数据中没有找到列 '{factor_col}' 或 '{ret_col}'")
        return

    # 去除两列中的缺失值，避免 qcut/cut 报错
    data = df[[factor_col, ret_col]].dropna()
    if len(data) < n_layers * 10:  # 经验上每层至少需要 10 个观测
        st.warning(f"数据量太少，建议减少分层数量。当前数据量：{len(data)}")

    # 因子分层：等频或等距
    if method == "qcut":
        data["layer"] = pd.qcut(
            data[factor_col], q=n_layers, labels=[f"第{i + 1}层" for i in range(n_layers)], duplicates="drop"
        )
    else:
        data["layer"] = pd.cut(
            data[factor_col], bins=n_layers, labels=[f"第{i + 1}层" for i in range(n_layers)], duplicates="drop"
        )

    # 各层日收益的绩效统计
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

    # 展示分层绩效表
    st.subheader(f"{factor_col} 分层收益分析")
    stats_styled = apply_stats_style(stats_df)
    st.dataframe(stats_styled, width="stretch")

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df, prefix="layer", factor_col=factor_col, ret_col=ret_col, n_layers=n_layers, method=method
        )

    # 各层平均收益对比柱状图
    layer_returns = data.groupby("layer")[ret_col].mean()
    fig_bar = px.bar(
        x=layer_returns.index.astype(str),
        y=layer_returns.values,
        title="各层平均收益对比",
        labels={"x": "分层", "y": "平均收益"},
    )
    st.plotly_chart(fig_bar, key=f"{key}_bar", width="stretch")

    # 若存在时间列，则绘制各层累计收益曲线
    if show_cumulative and "dt" in df.columns:
        st.subheader("分层累计收益曲线")
        df_temp = df.copy()
        df_temp = df_temp.dropna(subset=[factor_col, ret_col])

        # 重新分层（保持与上方一致的方法）
        if method == "qcut":
            df_temp["layer"] = pd.qcut(
                df_temp[factor_col], q=n_layers, labels=[f"第{i + 1}层" for i in range(n_layers)], duplicates="drop"
            )
        else:
            df_temp["layer"] = pd.cut(
                df_temp[factor_col], bins=n_layers, labels=[f"第{i + 1}层" for i in range(n_layers)], duplicates="drop"
            )

        df_temp["dt"] = pd.to_datetime(df_temp["dt"])
        df_temp = df_temp.sort_values("dt")

        # 各层累计收益（横截面取均值）
        cumulative_returns = []
        for layer in df_temp["layer"].cat.categories:
            layer_data = df_temp[df_temp["layer"] == layer]
            layer_cumret = layer_data.groupby("dt")[ret_col].mean().cumsum()
            layer_cumret.name = layer
            cumulative_returns.append(layer_cumret)

        if cumulative_returns:
            cumret_df = pd.concat(cumulative_returns, axis=1).fillna(method="ffill")
            fig_cumret = px.line(cumret_df, title="分层累计收益曲线")
            st.plotly_chart(fig_cumret, key=f"{key}_cumret", width="stretch")

    # 因子在各层的分布直方图
    if show_distribution:
        st.subheader(f"{factor_col} 分布分析")
        fig_hist = px.histogram(data, x=factor_col, color="layer", title=f"{factor_col} 在各层的分布")
        st.plotly_chart(fig_hist, key=f"{key}_hist", width="stretch")


def show_factor_value(df, factor_col, bins=50, key=None, **kwargs):
    """展示因子数值分布

    展示因子的样本数、均值、标准差、缺失值数量、分位数表，并绘制直方图与箱线图。
    同时基于 IQR 法进行异常值统计。

    :param df: pd.DataFrame，数据源
    :param factor_col: str，因子列名
    :param bins: int，直方图箱数，默认 50
    :param key: str，可选；组件基础标识符
    :param kwargs: 其他参数
        - show_outliers: bool，是否展示异常值统计与异常值列表，默认 True
        - percentiles: list，分位数列表，默认 [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    :return: None
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

    # 顶部展示基本统计量
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("观测数", f"{len(data):,.0f}")
    c2.metric("均值", f"{data.mean():.4f}")
    c3.metric("标准差", f"{data.std():.4f}")
    c4.metric("缺失值", f"{df[factor_col].isnull().sum():,.0f}")

    # 分位数明细
    quantiles = data.quantile(percentiles)
    quantile_df = pd.DataFrame({"分位数": [f"{p:.1%}" for p in percentiles], "数值": quantiles.values})

    with st.expander("分位数分布", expanded=False):
        st.dataframe(quantile_df.style.format({"数值": "{:.4f}"}), width="stretch", hide_index=True)

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df, prefix="fact_val", factor_col=factor_col, bins=bins, show_outliers=show_outliers
        )

    # 直方图与箱线图并排展示
    col1, col2 = st.columns(2)

    with col1:
        fig_hist = px.histogram(df, x=factor_col, nbins=bins, title=f"{factor_col} 直方图")
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, key=f"{key}_hist", width="stretch")

    with col2:
        fig_box = px.box(df, y=factor_col, title=f"{factor_col} 箱线图")
        if not show_outliers:
            fig_box.update_traces(boxpoints=False)
        st.plotly_chart(fig_box, key=f"{key}_box", width="stretch")

    # 基于 1.5 IQR 规则的异常值分析
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
                st.write(f"**异常值占比**: {len(outliers) / len(data):.2%}")

                if len(outliers) <= 100:  # 异常值过多时仅汇总，不再罗列
                    outlier_df = pd.DataFrame({"序号": range(1, len(outliers) + 1), "异常值": outliers.values})
                    st.dataframe(outlier_df.style.format({"异常值": "{:.4f}"}), width="stretch", hide_index=True)


def show_event_return(df, event_col, ret_col, key=None, **kwargs):
    """展示事件收益分析（事件研究法）

    定位 ``event_col`` 中所有发生事件的时点，计算事件前后若干期的累计收益，
    再求平均与 95% 置信区间，绘制经典的事件研究曲线。

    :param df: pd.DataFrame，数据源；必须包含 ``dt`` 时间列
    :param event_col: str，事件列名（布尔类型或 0/1）
    :param ret_col: str，收益列名
    :param key: str，可选；组件唯一标识符
    :param kwargs: 其他参数
        - pre_periods: int，事件前观察期数，默认 5
        - post_periods: int，事件后观察期数，默认 10
        - min_observations: int，最小事件次数，少于该值则警告，默认 10
    :return: None
    """
    pre_periods = kwargs.get("pre_periods", 5)
    post_periods = kwargs.get("post_periods", 10)
    min_observations = kwargs.get("min_observations", 10)

    if event_col not in df.columns or ret_col not in df.columns:
        st.error(f"数据中没有找到列 '{event_col}' 或 '{ret_col}'")
        return

    # 必须有时间列才能定位事件前后窗口
    if "dt" not in df.columns:
        st.error("数据中需要包含 'dt' 时间列")
        return

    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values("dt").reset_index(drop=True)

    # 找出事件发生的位置（True 或 1 都视为事件）
    event_mask = (df[event_col]) | (df[event_col] == 1)
    event_indices = df[event_mask].index.tolist()

    if len(event_indices) < min_observations:
        st.warning(f"事件发生次数太少（{len(event_indices)}次），建议至少{min_observations}次")
        return

    st.subheader(f"事件收益分析 (事件发生{len(event_indices)}次)")

    # 计算每个事件点前后窗口的相对累计收益
    event_returns = []
    for event_idx in event_indices:
        start_idx = max(0, event_idx - pre_periods)
        end_idx = min(len(df), event_idx + post_periods + 1)

        # 仅当窗口完整时才计入，避免边界数据干扰均值
        if end_idx - start_idx >= pre_periods + post_periods:
            window_data = df.iloc[start_idx:end_idx]
            window_returns = window_data[ret_col].values

            # 以事件时点为参考，前段累计 + 后段累计
            event_point = pre_periods
            relative_returns = np.zeros(len(window_returns))
            for i in range(len(window_returns)):
                if i <= event_point:
                    relative_returns[i] = np.sum(window_returns[: i + 1])
                else:
                    relative_returns[i] = np.sum(window_returns[event_point : i + 1])

            event_returns.append(relative_returns)

    if len(event_returns) == 0:
        st.error("没有足够的数据进行事件分析")
        return

    # 计算事件平均收益与标准差，构造 95% 置信区间
    event_returns_array = np.array(event_returns)
    mean_returns = np.mean(event_returns_array, axis=0)
    std_returns = np.std(event_returns_array, axis=0)

    # 时间轴：从 -pre_periods 到 +post_periods
    time_axis = list(range(-pre_periods, post_periods + 1))

    # 事件研究图：均值曲线 + 置信区间填充 + 事件分割线
    fig = go.Figure()

    # 平均累计收益主曲线
    fig.add_trace(
        go.Scatter(
            x=time_axis, y=mean_returns, mode="lines+markers", name="平均累计收益", line={"color": "blue", "width": 2}
        )
    )

    # 95% 置信区间（基于均值的标准误）
    upper_bound = mean_returns + 1.96 * std_returns / np.sqrt(len(event_returns))
    lower_bound = mean_returns - 1.96 * std_returns / np.sqrt(len(event_returns))

    fig.add_trace(
        go.Scatter(x=time_axis, y=upper_bound, fill=None, mode="lines", line_color="rgba(0,100,80,0)", showlegend=False)
    )

    fig.add_trace(
        go.Scatter(
            x=time_axis,
            y=lower_bound,
            fill="tonexty",
            mode="lines",
            line_color="rgba(0,100,80,0)",
            name="95%置信区间",
            fillcolor="rgba(0,100,80,0.2)",
        )
    )

    # 事件发生时点的红色虚线
    fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="事件发生")

    fig.update_layout(
        title=f"事件收益分析 (前{pre_periods}期，后{post_periods}期)",
        xaxis_title="相对事件时点的期数",
        yaxis_title="累计收益",
        hovermode="x unified",
    )

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df,
            prefix="event_ret",
            event_col=event_col,
            ret_col=ret_col,
            pre_periods=pre_periods,
            post_periods=post_periods,
        )

    st.plotly_chart(fig, key=key, width="stretch")

    # 底部展示 4 个关键指标：事件次数、事件前/后累计收益、事件效应
    pre_event_return = mean_returns[pre_periods - 1] if pre_periods > 0 else 0
    post_event_return = mean_returns[-1]
    event_effect = post_event_return - pre_event_return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("事件次数", f"{len(event_indices)}")
    c2.metric("事件前累计收益", f"{pre_event_return:.4f}")
    c3.metric("事件后累计收益", f"{post_event_return:.4f}")
    c4.metric("事件效应", f"{event_effect:.4f}")


def show_event_features(df, event_col, feature_cols, key=None, **kwargs):
    """展示事件特征分析

    将样本按事件是否发生切分为事件组与非事件组，针对每个特征做均值差异统计与
    显著性检验（T 检验或 Mann-Whitney U 检验），并绘制特征分布对比。

    :param df: pd.DataFrame，数据源
    :param event_col: str，事件列名
    :param feature_cols: list，特征列名列表
    :param key: str，可选；组件基础标识符
    :param kwargs: 其他参数
        - test_method: str，统计检验方法，``'ttest'`` 或 ``'mannwhitney'``，默认 ``'ttest'``
        - alpha: float，显著性水平，默认 0.05
    :return: None
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

    # 事件组与非事件组划分
    event_mask = (df[event_col]) | (df[event_col] == 1)
    event_data = df[event_mask]
    non_event_data = df[~event_mask]

    if len(event_data) == 0 or len(non_event_data) == 0:
        st.error("事件组或非事件组为空，无法进行比较")
        return

    st.subheader(f"事件特征分析 (事件组: {len(event_data)}, 非事件组: {len(non_event_data)})")

    # 逐特征做均值对比与统计检验
    test_results = []
    for feature in feature_cols:
        event_values = event_data[feature].dropna()
        non_event_values = non_event_data[feature].dropna()

        if len(event_values) == 0 or len(non_event_values) == 0:
            continue

        # 选择检验方法
        if test_method == "ttest":
            statistic, p_value = stats.ttest_ind(event_values, non_event_values)
            test_name = "T检验"
        else:
            statistic, p_value = stats.mannwhitneyu(event_values, non_event_values, alternative="two-sided")
            test_name = "Mann-Whitney U检验"

        result = {
            "特征": feature,
            "事件组均值": event_values.mean(),
            "非事件组均值": non_event_values.mean(),
            "差异": event_values.mean() - non_event_values.mean(),
            "检验统计量": statistic,
            "P值": p_value,
            "显著性": "是" if p_value < alpha else "否",
        }
        test_results.append(result)

    if not test_results:
        st.error("没有足够的数据进行特征比较")
        return

    # 检验结果表格
    results_df = pd.DataFrame(test_results)
    results_styled = results_df.style.background_gradient(cmap="RdYlGn_r", subset=["差异"])
    results_styled = results_styled.background_gradient(cmap="RdYlGn", subset=["P值"])
    results_styled = results_styled.format(
        {"事件组均值": "{:.4f}", "非事件组均值": "{:.4f}", "差异": "{:.4f}", "检验统计量": "{:.4f}", "P值": "{:.4f}"}
    )

    st.dataframe(results_styled, width="stretch", hide_index=True)
    st.caption(f"检验方法: {test_name}, 显著性水平: {alpha}")

    # 自动生成组件 key
    if key is None:
        key = generate_component_key(
            df, prefix="event_feat", event_col=event_col, feature_cols=feature_cols, test_method=test_method
        )

    # 为前 4 个特征绘制分布直方图与箱线图对比
    for _i, feature in enumerate(feature_cols[:4]):
        if feature in results_df["特征"].values:
            col1, col2 = st.columns(2)

            with col1:
                # 直方图叠加对比（半透明）
                fig_hist = go.Figure()

                event_values = event_data[feature].dropna()
                non_event_values = non_event_data[feature].dropna()

                fig_hist.add_trace(go.Histogram(x=event_values, name="事件组", opacity=0.7, nbinsx=30))
                fig_hist.add_trace(go.Histogram(x=non_event_values, name="非事件组", opacity=0.7, nbinsx=30))

                fig_hist.update_layout(
                    title=f"{feature} 分布对比", barmode="overlay", xaxis_title=feature, yaxis_title="频数"
                )
                st.plotly_chart(fig_hist, key=f"{key}_{feature}_hist", width="stretch")

            with col2:
                # 箱线图对比
                comparison_data = []
                comparison_data.extend([{"group": "事件组", "value": v, "feature": feature} for v in event_values])
                comparison_data.extend(
                    [{"group": "非事件组", "value": v, "feature": feature} for v in non_event_values]
                )
                comparison_df = pd.DataFrame(comparison_data)

                fig_box = px.box(comparison_df, x="group", y="value", title=f"{feature} 箱线图对比")
                st.plotly_chart(fig_box, key=f"{key}_{feature}_box", width="stretch")
