# pylint: disable-all
# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false
# type: ignore
"""
策略分析组件使用示例

本示例展示了 czsc.svc.strategy 模块中各种策略分析组件的使用方法。

运行方式:
streamlit run examples/develop/策略分析组件_svc版本.py

作者: 缠中说禅团队
"""
import sys

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from loguru import logger
from czsc.mock import (
    generate_strategy_returns,
    generate_portfolio,
    generate_weights,
    generate_price_data,
    generate_klines,
    generate_klines_with_weights,
)

# 设置页面配置
st.set_page_config(page_title="策略分析组件示例", page_icon="📈", layout="wide", initial_sidebar_state="expanded")


def show_returns_contribution_demo():
    """展示策略收益贡献分析演示"""
    st.header("🎯 策略收益贡献分析")
    st.markdown("分析各个子策略对总收益的贡献")

    # 生成策略收益数据
    df_strategies = generate_strategy_returns(8, None)  # 使用全部时间范围

    # 转换为透视表格式
    df_pivot = df_strategies.pivot(index="dt", columns="strategy", values="returns")

    # 使用策略分析组件
    from czsc.svc import show_returns_contribution

    st.subheader("📊 收益贡献分析")
    show_returns_contribution(df_pivot, max_returns=10)

    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_pivot.head(10), use_container_width=True)


def show_strategies_recent_demo():
    """展示最近N天策略表现演示"""
    st.header("📅 最近N天策略表现")
    st.markdown("展示策略在不同时间窗口下的表现")

    # 生成策略收益数据
    df_strategies = generate_strategy_returns(6, 1260)  # 约5年数据

    # 使用策略分析组件
    from czsc.svc import show_strategies_recent

    st.subheader("📈 策略近期表现")
    show_strategies_recent(df_strategies)

    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_strategies.head(20), use_container_width=True)


def show_quarterly_effect_demo():
    """展示季节性收益对比演示"""
    st.header("🌟 季节性收益对比")
    st.markdown("分析策略在不同季度的表现差异")

    # 生成单个策略的日收益序列
    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    returns = pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates)

    # 使用策略分析组件
    from czsc.svc import show_quarterly_effect

    st.subheader("📊 季度效应分析")
    show_quarterly_effect(returns)

    with st.expander("📋 数据预览", expanded=False):
        st.line_chart(returns.cumsum())


def show_portfolio_demo():
    """展示组合绩效分析演示"""
    st.header("💼 组合绩效分析")
    st.markdown("综合分析组合相对于基准的表现")

    # 生成组合数据
    df_portfolio = generate_portfolio()

    # 使用策略分析组件
    from czsc.svc import show_portfolio

    st.subheader("📈 组合表现分析")
    show_portfolio(df_portfolio, portfolio="portfolio", benchmark="benchmark")

    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_portfolio.head(10), use_container_width=True)


def show_turnover_rate_demo():
    """展示换手率分析演示"""
    st.header("🔄 换手率分析")
    st.markdown("分析策略的换手率变化情况")

    # 生成权重数据
    df_weights = generate_weights()

    # 使用策略分析组件
    from czsc.svc import show_turnover_rate

    st.subheader("📊 换手率变化")
    show_turnover_rate(df_weights)

    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_weights.head(20), use_container_width=True)


def show_stats_compare_demo():
    """展示策略绩效对比演示"""
    st.header("⚖️ 策略绩效对比")
    st.markdown("对比多个策略的回测绩效指标")

    # 生成多个策略的绩效数据
    stats_data = []
    for i in range(5):
        stats = {
            "name": f"策略_{i+1}",
            "绝对收益": np.random.uniform(0.1, 0.3),
            "年化": np.random.uniform(0.08, 0.25),
            "夏普": np.random.uniform(0.8, 2.2),
            "最大回撤": np.random.uniform(0.05, 0.2),
            "卡玛": np.random.uniform(0.5, 1.8),
            "年化波动率": np.random.uniform(0.12, 0.25),
            "交易胜率": np.random.uniform(0.45, 0.65),
            "品种数量": np.random.randint(3, 10),
            "持仓K线数": np.random.uniform(1000, 5000),
        }
        stats_data.append(stats)

    df_stats = pd.DataFrame(stats_data)

    # 使用策略分析组件
    from czsc.svc import show_stats_compare

    st.subheader("📊 绩效对比分析")
    show_stats_compare(df_stats)

    with st.expander("📋 原始数据", expanded=False):
        st.dataframe(df_stats, use_container_width=True)


def show_symbols_bench_demo():
    """展示品种基准分析演示"""
    st.header("🏪 品种基准分析")
    st.markdown("分析多个品种的基准收益表现")

    # 生成价格数据
    df_prices = generate_price_data()

    # 使用策略分析组件
    from czsc.svc import show_symbols_bench

    st.subheader("📈 品种基准表现")
    show_symbols_bench(df_prices)

    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_prices.head(20), use_container_width=True)


def show_cta_periods_classify_demo():
    """展示市场环境分类分析演示"""
    st.header("🌍 市场环境分类分析")
    st.markdown("分析策略在不同市场环境下的表现")

    # 生成K线数据
    df_kline = generate_klines()

    # 使用策略分析组件
    from czsc.svc import show_cta_periods_classify

    st.subheader("📊 市场环境分类回测")

    # 添加参数配置
    st.markdown("#### ⚙️ 参数配置")
    col1, col2, col3 = st.columns(3)
    with col1:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f")
    with col2:
        q1 = st.slider("最容易赚钱笔占比", 0.1, 0.3, 0.15, 0.05)
    with col3:
        q2 = st.slider("最难赚钱笔占比", 0.3, 0.5, 0.4, 0.05)

    # 添加更多配置选项
    col4, col5 = st.columns(2)
    with col4:
        digits = st.selectbox("小数位数", [1, 2, 3], index=1)
    with col5:
        weight_type = st.selectbox("权重类型", ["ts", "cs"], index=0, help="ts: 时序权重, cs: 截面权重")

    st.markdown("#### 📈 分类回测结果")
    show_cta_periods_classify(df_kline, fee_rate=fee_rate, digits=digits, weight_type=weight_type, q1=q1, q2=q2)

    # 添加说明信息
    with st.expander("📋 数据和参数说明", expanded=False):
        st.markdown(
            """
        **数据信息:**
        - 数据量: {:,} 条记录
        - 品种数: {} 个
        - 时间范围: {} 至 {}
        - 数据列: {}
        
        **参数说明:**
        - **手续费率**: 交易成本，影响最终收益
        - **最容易赚钱笔占比(q1)**: 趋势行情识别阈值，越小越严格
        - **最难赚钱笔占比(q2)**: 震荡行情识别阈值，越大越宽松
        - **权重类型**: ts表示时序权重，cs表示截面权重
        - **小数位数**: 收益率显示精度
        """.format(
                len(df_kline),
                df_kline["symbol"].nunique(),
                df_kline["dt"].min().strftime("%Y-%m-%d"),
                df_kline["dt"].max().strftime("%Y-%m-%d"),
                ", ".join(df_kline.columns.tolist()),
            )
        )


def show_cta_periods_classify_advanced_demo():
    """展示市场环境分类分析高级案例"""
    st.header("🎯 市场环境分类 - 高级案例")
    st.markdown("展示不同参数设置下的市场环境分类效果对比")

    # 生成K线数据
    df_kline = generate_klines()

    from czsc.svc import show_cta_periods_classify

    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["🔍 参数敏感性", "📊 多策略对比", "🧪 自定义测试"])

    with tab1:
        st.subheader("参数敏感性分析")
        st.markdown("观察不同q1、q2参数对市场环境分类的影响")

        # 参数组合
        param_sets = [
            {"q1": 0.1, "q2": 0.3, "name": "严格分类"},
            {"q1": 0.15, "q2": 0.4, "name": "中等分类"},
            {"q1": 0.2, "q2": 0.5, "name": "宽松分类"},
        ]

        selected_param = st.selectbox("选择参数组合", [p["name"] for p in param_sets])

        current_params = next(p for p in param_sets if p["name"] == selected_param)

        st.info(f"当前参数: q1={current_params['q1']}, q2={current_params['q2']}")

        show_cta_periods_classify(
            df_kline, fee_rate=0.0002, digits=2, weight_type="ts", q1=current_params["q1"], q2=current_params["q2"]
        )

    with tab2:
        st.subheader("多策略权重类型对比")
        st.markdown("比较时序权重(ts)和截面权重(cs)的表现差异")

        weight_type = st.radio("选择权重类型", ["ts", "cs"], help="ts: 时序权重，cs: 截面权重")

        show_cta_periods_classify(df_kline, fee_rate=0.0002, digits=2, weight_type=weight_type, q1=0.15, q2=0.4)

    with tab3:
        st.subheader("自定义参数测试")
        st.markdown("自由调整所有参数，观察回测效果")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            custom_fee = st.number_input("手续费率", 0.0001, 0.01, 0.0002, 0.0001, format="%.4f")
        with col2:
            custom_q1 = st.number_input("q1参数", 0.05, 0.3, 0.15, 0.01)
        with col3:
            custom_q2 = st.number_input("q2参数", 0.2, 0.6, 0.4, 0.01)
        with col4:
            custom_digits = st.number_input("小数位数", 1, 4, 2, 1)

        if st.button("🚀 运行自定义测试"):
            show_cta_periods_classify(
                df_kline, fee_rate=custom_fee, digits=custom_digits, weight_type="ts", q1=custom_q1, q2=custom_q2
            )


def show_volatility_classify_demo():
    """展示波动率分类分析演示"""
    st.header("📊 波动率分类分析")
    st.markdown("基于波动率对市场进行分类回测")

    # 生成K线数据
    df_kline = generate_klines()

    # 使用策略分析组件
    from czsc.svc import show_volatility_classify

    st.subheader("📈 波动率分类回测")

    # 添加参数配置
    st.markdown("#### ⚙️ 参数配置")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kind = st.selectbox("分类方式", ["ts", "cs"], index=0, help="ts:时序分类, cs:截面分类")
    with col2:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f")
    with col3:
        window = st.slider("波动率窗口", 10, 50, 20, 5)
    with col4:
        q_rate = st.slider("分位数占比", 0.1, 0.3, 0.2, 0.05)

    # 添加更多配置选项
    col5, col6 = st.columns(2)
    with col5:
        digits = st.selectbox("小数位数", [1, 2, 3], index=1, key="vol_digits")
    with col6:
        weight_type = st.selectbox(
            "权重类型", ["ts", "cs"], index=0, help="ts: 时序权重, cs: 截面权重", key="vol_weight"
        )

    st.markdown("#### 📊 波动率分类结果")
    show_volatility_classify(
        df_kline,
        kind=kind,
        fee_rate=fee_rate,
        digits=digits,
        weight_type=weight_type,
        window=window,
        q1=q_rate,
        q2=q_rate,
    )

    # 添加说明信息
    with st.expander("📋 波动率分类说明", expanded=False):
        st.markdown(
            """
        **波动率计算方法:**
        - 使用滚动窗口计算价格波动率
        - 基于分位数将K线分为高、中、低波动三类
        
        **分类方式说明:**
        - **时序分类(ts)**: 基于时间序列的波动率分位数分类
        - **截面分类(cs)**: 基于截面（品种间）的波动率分位数分类
        
        **参数影响:**
        - **窗口大小**: 影响波动率计算的平滑度
        - **分位数占比**: 控制高/低波动行情的识别严格程度
        - **权重类型**: 影响组合权重的分配方式
        
        **注意事项:**
        ⚠️ 该分析为后验分析，包含未来信息，不能直接用于实盘交易
        """
        )


def show_volatility_classify_advanced_demo():
    """展示波动率分类分析高级案例"""
    st.header("🔬 波动率分类 - 高级分析")
    st.markdown("深入分析不同波动率分类策略的表现")

    # 生成K线数据
    df_kline = generate_klines()

    from czsc.svc import show_volatility_classify

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📏 窗口期分析", "🎯 分位数对比", "⚖️ 分类方式对比", "🧮 综合测试"])

    with tab1:
        st.subheader("不同波动率计算窗口的影响")
        st.markdown("比较不同窗口期对波动率分类效果的影响")

        window_options = [10, 15, 20, 30, 50]
        selected_window = st.select_slider("波动率计算窗口", options=window_options, value=20)

        st.info(
            f"当前窗口期: {selected_window}天 - "
            + ("短期波动" if selected_window <= 15 else "中期波动" if selected_window <= 30 else "长期波动")
        )

        show_volatility_classify(
            df_kline, kind="ts", fee_rate=0.0002, digits=2, weight_type="ts", window=selected_window, q1=0.2, q2=0.2
        )

    with tab2:
        st.subheader("分位数参数敏感性")
        st.markdown("测试不同分位数设置对分类效果的影响")

        # 预设分位数组合
        quantile_sets = [
            {"q": 0.1, "name": "极端分类(10%)"},
            {"q": 0.2, "name": "标准分类(20%)"},
            {"q": 0.3, "name": "宽松分类(30%)"},
        ]

        selected_q = st.selectbox("选择分位数设置", [q["name"] for q in quantile_sets], key="q_select")

        current_q = next(q for q in quantile_sets if q["name"] == selected_q)

        st.info(f"高/低波动占比各为: {current_q['q']:.1%}")

        show_volatility_classify(
            df_kline,
            kind="ts",
            fee_rate=0.0002,
            digits=2,
            weight_type="ts",
            window=20,
            q1=current_q["q"],
            q2=current_q["q"],
        )

    with tab3:
        st.subheader("时序vs截面分类对比")
        st.markdown("比较时序分类和截面分类的差异")

        classify_kind = st.radio(
            "选择分类方式",
            ["ts", "cs"],
            format_func=lambda x: f"时序分类 (ts)" if x == "ts" else f"截面分类 (cs)",
            help="时序: 基于时间维度分类; 截面: 基于品种维度分类",
        )

        if classify_kind == "ts":
            st.info("🕐 时序分类: 在时间维度上找到波动率的高低分位点进行分类")
        else:
            st.info("📊 截面分类: 在品种维度上找到波动率的高低分位点进行分类")

        show_volatility_classify(
            df_kline, kind=classify_kind, fee_rate=0.0002, digits=2, weight_type="ts", window=20, q1=0.2, q2=0.2
        )

    with tab4:
        st.subheader("综合参数测试平台")
        st.markdown("自由组合所有参数，进行综合测试")

        # 参数配置区域
        with st.container(border=True):
            st.markdown("**🔧 完整参数配置**")

            col1, col2, col3 = st.columns(3)
            with col1:
                comp_kind = st.selectbox("分类方式", ["ts", "cs"], key="comp_kind")
                comp_window = st.number_input("窗口期", 5, 100, 20, 5, key="comp_window")
            with col2:
                comp_q1 = st.number_input("高波动分位数", 0.05, 0.4, 0.2, 0.05, key="comp_q1")
                comp_q2 = st.number_input("低波动分位数", 0.05, 0.4, 0.2, 0.05, key="comp_q2")
            with col3:
                comp_fee = st.number_input("手续费率", 0.0, 0.01, 0.0002, 0.0001, format="%.4f", key="comp_fee")
                comp_weight = st.selectbox("权重类型", ["ts", "cs"], key="comp_weight")

        if st.button("🎯 执行综合测试", type="primary"):
            with st.spinner("正在运行波动率分类回测..."):
                show_volatility_classify(
                    df_kline,
                    kind=comp_kind,
                    fee_rate=comp_fee,
                    digits=2,
                    weight_type=comp_weight,
                    window=comp_window,
                    q1=comp_q1,
                    q2=comp_q2,
                )
            st.success("✅ 测试完成！")


def show_yearly_backtest_demo():
    """展示按年度权重回测演示"""
    st.header("📅 按年度权重回测")
    st.markdown("根据权重数据，按年回测分析绩效差异")

    # 生成带权重的K线数据
    df_klines_weights = generate_klines_with_weights()

    # 使用策略分析组件
    from czsc.svc import show_yearly_backtest

    st.subheader("📊 年度回测分析")

    # 添加参数配置
    st.markdown("#### ⚙️ 参数配置")
    col1, col2, col3 = st.columns(3)
    with col1:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f", key="yearly_fee")
    with col2:
        digits = st.selectbox("小数位数", [1, 2, 3], index=1, key="yearly_digits")
    with col3:
        weight_type = st.selectbox(
            "权重类型", ["ts", "cs"], index=0, help="ts: 时序权重, cs: 截面权重", key="yearly_weight"
        )

    st.markdown("#### 📈 年度回测结果")
    show_yearly_backtest(df_klines_weights, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    # 添加说明信息
    with st.expander("📋 数据和参数说明", expanded=False):
        st.markdown(
            """
        **数据信息:**
        - 数据量: {:,} 条记录
        - 品种数: {} 个
        - 时间范围: {} 至 {}
        - 年份跨度: {} 年
        - 权重统计: 均值 {:.4f}, 标准差 {:.4f}
        
        **功能说明:**
        - **年度对比**: 对比不同年份的回测表现
        - **基准对比**: 包含全部年份作为基准进行对比
        - **风险分析**: 分析各年份的风险收益特征
        
        **参数说明:**
        - **手续费率**: 交易成本，影响最终收益
        - **权重类型**: ts表示时序权重，cs表示截面权重
        - **小数位数**: 权重保留精度
        """.format(
                len(df_klines_weights),
                df_klines_weights["symbol"].nunique(),
                df_klines_weights["dt"].min().strftime("%Y-%m-%d"),
                df_klines_weights["dt"].max().strftime("%Y-%m-%d"),
                df_klines_weights["dt"].dt.year.nunique(),
                df_klines_weights["weight"].mean(),
                df_klines_weights["weight"].std(),
            )
        )


def show_backtest_by_thresholds_demo():
    """展示权重阈值回测演示"""
    st.header("🎯 权重阈值回测")
    st.markdown("根据权重阈值进行回测对比，优化权重使用策略")

    # 生成带权重的K线数据
    df_klines_weights = generate_klines_with_weights()

    # 使用策略分析组件
    from czsc.svc import show_backtest_by_thresholds

    st.subheader("📊 阈值回测分析")

    # 添加参数配置
    st.markdown("#### ⚙️ 参数配置")
    col1, col2 = st.columns(2)
    with col1:
        out_sample_sdt = st.date_input(
            "样本外开始时间",
            value=pd.to_datetime("2020-01-01"),
            help="用于分割样本内外数据",
            key="threshold_sample_date",
        ).strftime("%Y-%m-%d")
    with col2:
        only_out_sample = st.checkbox(
            "仅样本外分析", value=False, help="是否只分析样本外数据", key="threshold_only_out"
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f", key="threshold_fee")
    with col4:
        digits = st.selectbox("小数位数", [1, 2, 3], index=1, key="threshold_digits")
    with col5:
        weight_type = st.selectbox(
            "权重类型", ["ts", "cs"], index=0, help="ts: 时序权重, cs: 截面权重", key="threshold_weight"
        )

    # 分位数设置
    st.markdown("#### 📊 分位数阈值设置")
    col6, col7, col8 = st.columns(3)
    with col6:
        start_percentile = st.slider("起始分位数", 0.0, 0.8, 0.0, 0.1, key="threshold_start")
    with col7:
        end_percentile = st.slider("结束分位数", 0.2, 0.9, 0.9, 0.1, key="threshold_end")
    with col8:
        step_size = st.slider("步长", 0.1, 0.2, 0.1, 0.1, key="threshold_step")

    percentiles = list(np.arange(start_percentile, end_percentile + step_size, step_size))
    st.info(f"当前分位数序列: {[f'{p:.1f}' for p in percentiles]}")

    st.markdown("#### 📈 阈值回测结果")
    show_backtest_by_thresholds(
        df_klines_weights,
        out_sample_sdt=out_sample_sdt,
        percentiles=percentiles,
        fee_rate=fee_rate,
        digits=digits,
        weight_type=weight_type,
        only_out_sample=only_out_sample,
    )

    # 添加说明信息
    with st.expander("📋 权重阈值回测说明", expanded=False):
        st.markdown(
            """
        **数据分割:**
        - 样本内数据: 用于计算权重阈值
        - 样本外数据: 用于验证策略效果
        - 样本外开始时间: {}
        
        **阈值策略:**
        - 计算样本内权重绝对值的分位数作为阈值
        - 仅当权重绝对值大于等于阈值时，使用 sign(weight) 进行交易
        - 其他情况权重设为0，即不交易
        
        **分位数含义:**
        - 0%分位数: 使用所有权重信号
        - 50%分位数: 仅使用权重绝对值在中位数以上的信号
        - 90%分位数: 仅使用权重绝对值在90%分位数以上的信号
        
        **预期效果:**
        - 较高的阈值可能减少交易频率和成本
        - 可能提高信号质量，过滤掉弱信号
        - 需要权衡信号覆盖度和信号质量
        
        **注意事项:**
        ⚠️ 该分析基于历史数据的后验分析，实盘应用需谨慎
        """.format(
                out_sample_sdt
            )
        )


def show_backtest_by_thresholds_advanced_demo():
    """展示权重阈值回测高级案例"""
    st.header("🎯 权重阈值回测 - 高级案例")
    st.markdown("深入分析不同阈值策略的表现和优化方向")

    # 生成带权重的K线数据
    df_klines_weights = generate_klines_with_weights()

    from czsc.svc import show_backtest_by_thresholds

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 分位数敏感性", "📊 样本期对比", "⚖️ 成本影响分析", "🧮 综合优化"])

    with tab1:
        st.subheader("不同分位数设置的影响")
        st.markdown("测试不同分位数范围对阈值策略的影响")

        # 预设分位数组合
        quantile_sets = [
            {"range": [0.0, 0.5], "step": 0.1, "name": "保守策略(0-50%)"},
            {"range": [0.0, 0.9], "step": 0.1, "name": "标准策略(0-90%)"},
            {"range": [0.5, 0.9], "step": 0.1, "name": "激进策略(50-90%)"},
        ]

        selected_set = st.selectbox("选择分位数组合", [q["name"] for q in quantile_sets])
        current_set = next(q for q in quantile_sets if q["name"] == selected_set)

        percentiles = list(
            np.arange(current_set["range"][0], current_set["range"][1] + current_set["step"], current_set["step"])
        )
        st.info(f"当前分位数序列: {[f'{p:.1f}' for p in percentiles]}")

        show_backtest_by_thresholds(
            df_klines_weights,
            out_sample_sdt="2020-01-01",
            percentiles=percentiles,
            fee_rate=0.0002,
            digits=2,
            weight_type="ts",
            only_out_sample=False,
        )

    with tab2:
        st.subheader("样本内外数据对比")
        st.markdown("对比样本内外数据的回测效果差异")

        sample_analysis = st.radio(
            "选择分析范围",
            ["全部数据", "仅样本外"],
            format_func=lambda x: f"📊 全部数据分析" if x == "全部数据" else f"🎯 仅样本外分析",
            help="全部数据: 使用完整数据集; 仅样本外: 只分析样本外数据",
        )

        only_out_sample = sample_analysis == "仅样本外"

        if only_out_sample:
            st.info("🎯 仅分析样本外数据，更贴近实际交易情况")
        else:
            st.info("📊 分析全部数据，包含样本内和样本外")

        show_backtest_by_thresholds(
            df_klines_weights,
            out_sample_sdt="2020-01-01",
            percentiles=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            fee_rate=0.0002,
            digits=2,
            weight_type="ts",
            only_out_sample=only_out_sample,
        )

    with tab3:
        st.subheader("交易成本影响分析")
        st.markdown("分析不同手续费率对阈值策略的影响")

        fee_scenarios = {
            "低成本(0.01%)": 0.0001,
            "标准成本(0.02%)": 0.0002,
            "高成本(0.05%)": 0.0005,
        }

        selected_fee = st.selectbox("选择手续费场景", list(fee_scenarios.keys()))
        fee_rate = fee_scenarios[selected_fee]

        st.info(f"当前手续费率: {fee_rate:.4f} ({fee_rate:.2%})")

        show_backtest_by_thresholds(
            df_klines_weights,
            out_sample_sdt="2020-01-01",
            percentiles=[0.0, 0.2, 0.4, 0.6, 0.8],
            fee_rate=fee_rate,
            digits=2,
            weight_type="ts",
            only_out_sample=True,
        )

    with tab4:
        st.subheader("综合参数优化平台")
        st.markdown("自由组合所有参数，寻找最优阈值策略")

        # 参数配置区域
        with st.container(border=True):
            st.markdown("**🔧 完整参数配置**")

            col1, col2, col3 = st.columns(3)
            with col1:
                opt_out_sample = st.date_input(
                    "样本外开始时间", value=pd.to_datetime("2020-01-01"), key="opt_sample_date"
                ).strftime("%Y-%m-%d")
                opt_only_out = st.checkbox("仅样本外", value=True, key="opt_only_out")

            with col2:
                opt_start_p = st.number_input("起始分位数", 0.0, 0.8, 0.0, 0.1, key="opt_start_p")
                opt_end_p = st.number_input("结束分位数", 0.2, 0.9, 0.8, 0.1, key="opt_end_p")

            with col3:
                opt_fee = st.number_input("手续费率", 0.0, 0.01, 0.0002, 0.0001, format="%.4f", key="opt_fee")
                opt_weight = st.selectbox("权重类型", ["ts", "cs"], key="opt_weight")

        opt_percentiles = list(np.arange(opt_start_p, opt_end_p + 0.1, 0.1))

        if st.button("🎯 执行综合优化测试", type="primary"):
            with st.spinner("正在运行权重阈值优化回测..."):
                show_backtest_by_thresholds(
                    df_klines_weights,
                    out_sample_sdt=opt_out_sample,
                    percentiles=opt_percentiles,
                    fee_rate=opt_fee,
                    digits=2,
                    weight_type=opt_weight,
                    only_out_sample=opt_only_out,
                )
            st.success("✅ 优化测试完成！")


def show_help_info():
    """展示帮助信息和组件说明"""
    st.markdown("---")
    st.markdown("### 📚 使用说明")

    with st.expander("💡 组件功能说明", expanded=False):
        st.markdown(
            """
        #### 🎯 策略分析组件功能
        
        **策略收益贡献分析** (`show_returns_contribution`)
        - 分析各子策略对总收益的贡献度
        - 提供柱状图和饼图两种视角
        - 自动过滤负收益策略，突出盈利贡献
        
        **最近N天策略表现** (`show_strategies_recent`) 
        - 展示策略在不同时间窗口的表现
        - 计算盈利策略数量和比例
        - 支持自定义时间序列
        
        **季节性收益对比** (`show_quarterly_effect`)
        - 按季度分析策略表现差异
        - 提供各季度详细统计指标
        - 可视化季度内累计收益曲线
        
        **组合绩效分析** (`show_portfolio`)
        - 综合分析组合表现
        - 支持基准对比和超额收益分析
        - 包含年度、季度、月度多维度分析
        
        **换手率分析** (`show_turnover_rate`)
        - 分析策略换手率变化
        - 提供日、月、年多个时间维度
        - 计算最近时期换手率统计
        
        **策略绩效对比** (`show_stats_compare`)
        - 多策略绩效指标对比
        - 统一的样式和格式化
        - 支持自定义绩效指标集合
        
        **品种基准分析** (`show_symbols_bench`)
        - 分析多个品种的基准收益表现
        - 计算各品种的关键统计指标
        - 提供可视化的基准对比
        
        **市场环境分类** (`show_cta_periods_classify`)
        - 基于趋势强弱对市场环境进行分类
        - 分析策略在不同环境下的表现差异
        - 支持自定义分类参数和手续费率
        
        **波动率分类** (`show_volatility_classify`)
        - 基于波动率水平进行市场分类
        - 支持时序和截面两种分类方式
        - 可调节波动率计算窗口和分位数参数
        
        **按年度权重回测** (`show_yearly_backtest`)
        - 根据权重数据按年度进行回测分析
        - 对比不同年份的策略表现差异
        - 包含全部年份作为基准进行对比分析
        - 支持自定义回测参数和权重类型
        
        **权重阈值回测** (`show_backtest_by_thresholds`)
        - 根据权重阈值进行回测对比分析
        - 基于样本内权重分位数设定阈值
        - 分析不同阈值下的策略表现
        - 支持样本内外数据分割和权重使用统计
        
        **高级案例分析**
        - 市场环境分类高级案例：参数敏感性分析、多策略对比、自定义测试
        - 波动率分类高级案例：窗口期分析、分位数对比、分类方式对比、综合测试
        - 权重阈值回测高级案例：分位数敏感性、样本期对比、成本影响分析、综合优化
        """
        )

    with st.expander("🔧 技术特性", expanded=False):
        st.markdown(
            """
        #### 🛠️ 技术优势
        
        **模块化设计**
        - 功能解耦，便于维护和扩展
        - 统一的基础组件和样式
        - 完整的向后兼容性
        
        **数据安全**
        - 智能的库导入机制
        - 完善的错误处理
        - 数据格式自动检测和转换
        
        **性能优化**
        - 缓存机制减少重复计算
        - 延迟加载外部依赖
        - 优化的数据处理流程
        
        **用户体验**
        - 一致的界面风格
        - 详细的参数说明
        - 丰富的交互功能
        
        **新增特性**
        - 分层级的案例组织：基础分析、市场环境分析、高级案例
        - 多标签页设计：提供不同维度的深入分析
        - 参数敏感性测试：系统化的参数影响分析
        - 交互式配置界面：实时调整参数观察效果
        """
        )

    st.markdown("**🚀 开始使用**: 选择左侧不同的演示类型来体验各种策略分析功能！")


def main():
    """主函数，负责页面路由和调用相应的演示函数"""
    st.title("🎯 策略分析组件使用示例")
    st.markdown("---")

    # 侧边栏配置
    st.sidebar.header("⚙️ 配置选项")

    # 分组展示演示类型
    demo_category = st.sidebar.selectbox("选择分析类别", ["基础策略分析", "市场环境分析", "高级案例分析"])

    if demo_category == "基础策略分析":
        demo_options = [
            "策略收益贡献分析",
            "最近N天策略表现",
            "季节性收益对比",
            "组合绩效分析",
            "换手率分析",
            "策略绩效对比",
            "品种基准分析",
            "按年度权重回测",
            "权重阈值回测",
        ]
    elif demo_category == "市场环境分析":
        demo_options = ["市场环境分类", "波动率分类"]
    else:  # 高级案例分析
        demo_options = ["市场环境分类-高级案例", "波动率分类-高级案例", "权重阈值回测-高级案例"]

    demo_type = st.sidebar.selectbox("选择具体演示", demo_options)

    # 演示类型到函数的映射字典
    demo_functions = {
        "策略收益贡献分析": show_returns_contribution_demo,
        "最近N天策略表现": show_strategies_recent_demo,
        "季节性收益对比": show_quarterly_effect_demo,
        "组合绩效分析": show_portfolio_demo,
        "换手率分析": show_turnover_rate_demo,
        "策略绩效对比": show_stats_compare_demo,
        "品种基准分析": show_symbols_bench_demo,
        "市场环境分类": show_cta_periods_classify_demo,
        "波动率分类": show_volatility_classify_demo,
        "市场环境分类-高级案例": show_cta_periods_classify_advanced_demo,
        "波动率分类-高级案例": show_volatility_classify_advanced_demo,
        "按年度权重回测": show_yearly_backtest_demo,
        "权重阈值回测": show_backtest_by_thresholds_demo,
        "权重阈值回测-高级案例": show_backtest_by_thresholds_advanced_demo,
    }

    # 调用相应的演示函数
    demo_function = demo_functions.get(demo_type)
    if demo_function:
        demo_function()

    # 显示帮助信息
    show_help_info()


if __name__ == "__main__":
    main()
