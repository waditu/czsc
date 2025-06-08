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

# 设置页面配置
st.set_page_config(
    page_title="策略分析组件示例",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎯 策略分析组件使用示例")
st.markdown("---")

# 侧边栏配置
st.sidebar.header("⚙️ 配置选项")
demo_type = st.sidebar.selectbox(
    "选择演示类型",
    ["策略收益贡献分析", "最近N天策略表现", "季节性收益对比", "组合绩效分析", 
     "换手率分析", "策略绩效对比", "品种基准分析", "市场环境分类", "波动率分类"]
)

# 生成示例数据的函数
@st.cache_data
def generate_strategy_returns(n_strategies=10, n_days=None):
    """生成多策略收益数据"""
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    if n_days and len(dates) > n_days:
        dates = dates[-n_days:]  # 取最近的n_days天
    data = []
    
    for i in range(n_strategies):
        strategy_name = f"策略_{i+1:02d}"
        # 生成具有不同特征的收益率
        base_return = np.random.normal(0.0005, 0.015, len(dates))
        if i % 3 == 0:  # 每3个策略中有一个表现更好
            base_return += np.random.normal(0.0002, 0.005, len(dates))
        
        for j, dt in enumerate(dates):
            data.append({
                'dt': dt,
                'strategy': strategy_name,
                'returns': base_return[j]
            })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_portfolio_data():
    """生成组合数据"""
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    portfolio_returns = np.random.normal(0.0008, 0.012, len(dates))
    benchmark_returns = np.random.normal(0.0003, 0.010, len(dates))
    
    return pd.DataFrame({
        'dt': dates,
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    })

@st.cache_data
def generate_weight_data():
    """生成权重数据"""
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    data = []
    for dt in dates:
        # 生成随机权重，每日权重和为1
        weights = np.random.random(len(symbols))
        weights = weights / weights.sum()
        
        for i, symbol in enumerate(symbols):
            data.append({
                'dt': dt,
                'symbol': symbol,
                'weight': weights[i]
            })
    
    return pd.DataFrame(data)

@st.cache_data  
def generate_price_data():
    """生成价格数据"""
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    data = []
    for symbol in symbols:
        price = 100.0
        for dt in dates:
            price *= (1 + np.random.normal(0.0005, 0.02))
            data.append({
                'symbol': symbol,
                'dt': dt,
                'price': price
            })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_kline_data():
    """生成K线数据，包含完整的OHLCVA信息（开高低收量额）"""
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    data = []
    for symbol in symbols:
        # 初始价格
        price = 100.0
        
        for i, dt in enumerate(dates):
            # 生成开盘价
            open_price = price * (1 + np.random.normal(0, 0.01))
            
            # 生成日内波动
            daily_return = np.random.normal(0.0005, 0.02)
            high_mult = 1 + abs(np.random.normal(0, 0.015))
            low_mult = 1 - abs(np.random.normal(0, 0.015))
            
            # 计算OHLC
            close_price = open_price * (1 + daily_return)
            high_price = max(open_price, close_price) * high_mult
            low_price = min(open_price, close_price) * low_mult
            
            # 成交量（随机生成）
            volume = np.random.randint(1000000, 10000000)
            
            # 成交金额（价格 * 成交量）
            amount = close_price * volume
            
            # 权重（简单均权或随机权重）
            weight = 1.0 / len(symbols) + np.random.normal(0, 0.02)
            weight = max(0.01, min(0.5, weight))  # 限制权重范围
            
            data.append({
                'dt': dt,
                'symbol': symbol,
                'open': round(open_price, 2),
                'close': round(close_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'vol': volume,
                'amount': round(amount, 2),  # 成交金额
                'weight': round(weight, 4),
                'price': round(close_price, 2)  # 用收盘价作为价格
            })
            
            # 更新基准价格
            price = close_price
    
    return pd.DataFrame(data)

# 根据选择的演示类型展示相应功能
if demo_type == "策略收益贡献分析":
    st.header("🎯 策略收益贡献分析")
    st.markdown("分析各个子策略对总收益的贡献")
    
    # 生成策略收益数据
    df_strategies = generate_strategy_returns(8, None)  # 使用全部时间范围
    
    # 转换为透视表格式
    df_pivot = df_strategies.pivot(index='dt', columns='strategy', values='returns')
    
    # 使用策略分析组件
    from czsc.svc import show_returns_contribution
    
    st.subheader("📊 收益贡献分析")
    show_returns_contribution(df_pivot, max_returns=10)
    
    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_pivot.head(10), use_container_width=True)

elif demo_type == "最近N天策略表现":
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

elif demo_type == "季节性收益对比":
    st.header("🌟 季节性收益对比")
    st.markdown("分析策略在不同季度的表现差异")
    
    # 生成单个策略的日收益序列
    dates = pd.date_range(start='2010-01-01', end='2025-06-08', freq='D')
    returns = pd.Series(
        np.random.normal(0.0008, 0.015, len(dates)),
        index=dates
    )
    
    # 使用策略分析组件
    from czsc.svc import show_quarterly_effect
    
    st.subheader("📊 季度效应分析")
    show_quarterly_effect(returns)
    
    with st.expander("📋 数据预览", expanded=False):
        st.line_chart(returns.cumsum())

elif demo_type == "组合绩效分析":
    st.header("💼 组合绩效分析")
    st.markdown("综合分析组合相对于基准的表现")
    
    # 生成组合数据
    df_portfolio = generate_portfolio_data()
    
    # 使用策略分析组件
    from czsc.svc import show_portfolio
    
    st.subheader("📈 组合表现分析")
    show_portfolio(df_portfolio, portfolio='portfolio', benchmark='benchmark')
    
    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_portfolio.head(10), use_container_width=True)

elif demo_type == "换手率分析":
    st.header("🔄 换手率分析")
    st.markdown("分析策略的换手率变化情况")
    
    # 生成权重数据
    df_weights = generate_weight_data()
    
    # 使用策略分析组件
    from czsc.svc import show_turnover_rate
    
    st.subheader("📊 换手率变化")
    show_turnover_rate(df_weights)
    
    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_weights.head(20), use_container_width=True)

elif demo_type == "策略绩效对比":
    st.header("⚖️ 策略绩效对比")
    st.markdown("对比多个策略的回测绩效指标")
    
    # 生成多个策略的绩效数据
    stats_data = []
    for i in range(5):
        stats = {
            'name': f'策略_{i+1}',
            '绝对收益': np.random.uniform(0.1, 0.3),
            '年化': np.random.uniform(0.08, 0.25),
            '夏普': np.random.uniform(0.8, 2.2),
            '最大回撤': np.random.uniform(0.05, 0.2),
            '卡玛': np.random.uniform(0.5, 1.8),
            '年化波动率': np.random.uniform(0.12, 0.25),
            '交易胜率': np.random.uniform(0.45, 0.65),
            '品种数量': np.random.randint(3, 10),
            '持仓K线数': np.random.uniform(1000, 5000),
        }
        stats_data.append(stats)
    
    df_stats = pd.DataFrame(stats_data)
    
    # 使用策略分析组件
    from czsc.svc import show_stats_compare
    
    st.subheader("📊 绩效对比分析")
    show_stats_compare(df_stats)
    
    with st.expander("📋 原始数据", expanded=False):
        st.dataframe(df_stats, use_container_width=True)

elif demo_type == "品种基准分析":
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

elif demo_type == "市场环境分类":
    st.header("🌍 市场环境分类分析")
    st.markdown("分析策略在不同市场环境下的表现")
    
    # 生成K线数据
    df_kline = generate_kline_data()
    
    # 使用策略分析组件
    from czsc.svc import show_cta_periods_classify
    
    st.subheader("📊 市场环境分类回测")
    
    # 添加参数配置
    col1, col2, col3 = st.columns(3)
    with col1:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f")
    with col2:
        q1 = st.slider("最容易赚钱笔占比", 0.1, 0.3, 0.15, 0.05)
    with col3:
        q2 = st.slider("最难赚钱笔占比", 0.3, 0.5, 0.4, 0.05)
    
    show_cta_periods_classify(
        df_kline, 
        fee_rate=fee_rate,
        digits=2,
        weight_type='ts',
        q1=q1,
        q2=q2
    )
    
    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_kline.head(20), use_container_width=True)
        st.markdown(f"**数据概览**: 共 {len(df_kline)} 条记录，{df_kline['symbol'].nunique()} 个品种")
        st.markdown(f"**数据列**: {', '.join(df_kline.columns.tolist())}")

elif demo_type == "波动率分类":
    st.header("📊 波动率分类分析")
    st.markdown("基于波动率对市场进行分类回测")
    
    # 生成K线数据
    df_kline = generate_kline_data()
    
    # 使用策略分析组件
    from czsc.svc import show_volatility_classify
    
    st.subheader("📈 波动率分类回测")
    
    # 添加参数配置
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kind = st.selectbox("分类方式", ['ts', 'cs'], index=0, help="ts:时序, cs:截面")
    with col2:
        fee_rate = st.slider("手续费率", 0.0001, 0.001, 0.0002, 0.0001, format="%.4f")
    with col3:
        window = st.slider("波动率窗口", 10, 50, 20, 5)
    with col4:
        q_rate = st.slider("分位数占比", 0.1, 0.3, 0.2, 0.05)
    
    show_volatility_classify(
        df_kline,
        kind=kind,
        fee_rate=fee_rate,
        digits=2,
        weight_type='ts',
        window=window,
        q1=q_rate,
        q2=q_rate
    )
    
    with st.expander("📋 数据预览", expanded=False):
        st.dataframe(df_kline.head(20), use_container_width=True)
        st.markdown(f"**数据概览**: 共 {len(df_kline)} 条记录，{df_kline['symbol'].nunique()} 个品种")
        st.markdown(f"**数据列**: {', '.join(df_kline.columns.tolist())}")

# 页面底部信息
st.markdown("---")
st.markdown("### 📚 使用说明")

with st.expander("💡 组件功能说明", expanded=False):
    st.markdown("""
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
    """)

with st.expander("🔧 技术特性", expanded=False):
    st.markdown("""
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
    """)

st.markdown("**🚀 开始使用**: 选择左侧不同的演示类型来体验各种策略分析功能！") 