"""
测试权重分析组件的 Streamlit 应用

使用方法：
    streamlit run test_weights_components.py
"""

import sys

sys.path.append("..")
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import streamlit as st

from czsc.svc import show_weight_abs, show_weight_cdf, show_weight_dist, show_weight_ts


@st.cache_data
def generate_mock_weights(days=252, symbols=10):
    """生成模拟的持仓权重数据

    :param days: 交易天数
    :param symbols: 品种数量
    :return: DataFrame with dt, symbol, weight columns
    """
    np.random.seed(42)

    # 生成日期范围
    dates = pd.date_range(start="2024-01-01", periods=days, freq="D")

    # 生成品种代码
    symbol_list = [f"STOCK{i:03d}" for i in range(symbols)]

    data = []
    for dt in dates:
        for symbol in symbol_list:
            # 随机生成权重，模拟真实持仓
            weight = np.random.randn() * 0.3  # 正态分布

            # 70% 概率有持仓
            if np.random.random() > 0.7:
                weight = 0

            # 限制权重范围
            weight = np.clip(weight, -1, 1)

            data.append({"dt": dt, "symbol": symbol, "weight": weight})

    df = pd.DataFrame(data)
    return df


def main():
    st.set_page_config(page_title="权重分析组件测试", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

    st.title("📊 权重分析组件测试页面")
    st.markdown("---")

    # 侧边栏配置
    st.sidebar.header("⚙️ 数据配置")

    days = st.sidebar.slider("交易天数", min_value=30, max_value=500, value=252, step=10)
    symbols = st.sidebar.slider("品种数量", min_value=5, max_value=50, value=10, step=1)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📝 说明")
    st.sidebar.info("""
    本页面用于测试 `czsc.svc.weights` 模块中的四个组件：
    
    1. **权重时序分析** (`show_weight_ts`)
       - 展示多头、空头、绝对仓位、净仓位的时序变化
    
    2. **权重分布分析** (`show_weight_dist`)
       - 展示仓位分布的直方图和核密度估计
    
    3. **权重累积分布** (`show_weight_cdf`)
       - 展示各类仓位的累积分布函数
    
    4. **绝对仓位分析** (`show_weight_abs`)
       - 详细分析绝对仓位的时序、统计和分布
    """)

    # 生成或使用示例数据
    st.header("🎲 数据生成")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write(f"生成 **{days}** 个交易日，**{symbols}** 个品种的模拟持仓数据")

    with col2:
        if st.button("🔄 重新生成数据", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    with col3:
        if st.button("📥 导出数据", width="stretch"):
            st.session_state["export_data"] = True

    # 生成数据
    df = generate_mock_weights(days=days, symbols=symbols)

    # 显示数据概览
    st.subheader("📋 数据概览")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("总记录数", f"{len(df):,}")

    with col2:
        non_zero = len(df[df["weight"] != 0])
        st.metric("非零持仓数", f"{non_zero:,}")

    with col3:
        long_pos = len(df[df["weight"] > 0])
        st.metric("多头持仓数", f"{long_pos:,}")

    with col4:
        short_pos = len(df[df["weight"] < 0])
        st.metric("空头持仓数", f"{short_pos:,}")

    # 数据预览
    with st.expander("🔍 查看数据样本", expanded=False):
        st.dataframe(df.head(100), width="stretch")

    # 导出数据
    if st.session_state.get("export_data", False):
        csv = df.to_csv(index=False)
        st.download_button(
            label="💾 下载 CSV 文件",
            data=csv,
            file_name=f"weight_data_{days}days_{symbols}symbols.csv",
            mime="text/csv",
        )
        st.session_state["export_data"] = False

    st.markdown("---")

    # 测试组件
    st.header("🧪 组件测试")

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["⏰ 权重时序分析", "📊 权重分布分析", "📈 权重累积分布", "🎯 绝对仓位分析"])

    with tab1:
        st.subheader("show_weight_ts - 权重时序分析")
        st.markdown("展示多头累计、空头累计、绝对仓位、净仓位和持仓数量的时序变化")

        col1, col2 = st.columns(2)
        with col1:
            show_count = st.checkbox("显示持仓数量", value=True)
        with col2:
            height = st.slider("图表高度", 400, 1200, 800)

        show_weight_ts(df, show_position_count=show_count, height=height)

    with tab2:
        st.subheader("show_weight_dist - 权重分布分析")
        st.markdown("展示多头、空头、净仓位、绝对仓位的分布直方图与核密度估计")

        col1, col2 = st.columns(2)
        with col1:
            height = st.slider("图表高度", 400, 1200, 800, key="dist_height")
        with col2:
            width = st.slider("图表宽度", 600, 1400, 900, key="dist_width")

        show_weight_dist(df, height=height, width=width)

    with tab3:
        st.subheader("show_weight_cdf - 权重累积分布")
        st.markdown("展示各类仓位的累积分布函数(CDF)对比")

        col1, col2 = st.columns(2)
        with col1:
            show_percentiles = st.checkbox("显示分位数参考线", value=True)
        with col2:
            height = st.slider("图表高度", 400, 1000, 600, key="cdf_height")

        show_weight_cdf(df, show_percentiles=show_percentiles, height=height)

    with tab4:
        st.subheader("show_weight_abs - 绝对仓位分析")
        st.markdown("展示绝对仓位的时序曲线、滚动统计指标和分布统计")

        col1, col2, col3 = st.columns(3)
        with col1:
            height = st.slider("图表高度", 600, 1200, 900, key="abs_height")
        with col2:
            ma_window = st.multiselect("移动平均线窗口", [5, 10, 20, 60, 120], default=[5, 20, 60])
        with col3:
            vol_window = st.slider("波动率窗口", 5, 60, 20)

        show_weight_abs(df, height=height, ma_windows=ma_window, volatility_window=vol_window)

    # 测试多次调用（验证 hash key 功能）
    st.markdown("---")
    st.header("🔄 多次调用测试（验证 Hash Key 功能）")

    st.info("下面两次调用同一个组件，验证 hash key 是否能避免 StreamlitDuplicateElementId 错误")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("调用 1")
        show_weight_ts(df, title="权重时序分析 - 调用1")

    with col2:
        st.subheader("调用 2")
        show_weight_ts(df, title="权重时序分析 - 调用2")

    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <p>CZSC 权重分析组件测试页面 | 基于 Streamlit 构建</p>
            <p>测试组件: show_weight_ts, show_weight_dist, show_weight_cdf, show_weight_abs</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
