# -*- coding: utf-8 -*-
"""
V字反转识别可视化验证脚本
使用Streamlit展示V字反转识别结果，方便人工验证

运行方式：
streamlit run show_mark_v.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# 导入CZSC相关模块
from czsc.mock import generate_klines, generate_symbol_kines
from czsc.eda import mark_v_reversal

# 页面配置
st.set_page_config(
    page_title="V字反转识别验证",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 V字反转识别验证工具")
st.markdown("---")

# 侧边栏参数设置
st.sidebar.header("参数设置")

# 数据选择
data_source = st.sidebar.selectbox(
    "数据源选择",
    ["多品种数据", "单品种数据"]
)

if data_source == "单品种数据":
    symbol = st.sidebar.selectbox(
        "选择品种",
        ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BTC", "ETH"]
    )
    freq = st.sidebar.selectbox(
        "选择频率",
        ["30分钟", "日线", "15分钟", "5分钟"]
    )
    
    # 时间范围
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=pd.to_datetime("2023-01-01"))
    with col2:
        end_date = st.date_input("结束日期", value=pd.to_datetime("2024-01-01"))

# V字反转识别参数
st.sidebar.subheader("V字反转参数")
min_power_percentile = st.sidebar.slider(
    "最小力度百分位数", 
    min_value=0.5, 
    max_value=0.95, 
    value=0.7, 
    step=0.05,
    help="第一个笔的最小力度百分位数，越高要求笔的力度越强"
)

min_retracement = st.sidebar.slider(
    "最小回撤比例", 
    min_value=0.3, 
    max_value=0.8, 
    value=0.5, 
    step=0.05,
    help="第二个笔相对第一个笔的最小回撤比例"
)

min_speed_ratio = st.sidebar.slider(
    "最小速度比例", 
    min_value=1.0, 
    max_value=3.0, 
    value=1.5, 
    step=0.1,
    help="第二个笔相对第一个笔的最小速度比例"
)

power_window = st.sidebar.slider(
    "力度排名窗口", 
    min_value=20, 
    max_value=100, 
    value=50, 
    step=10,
    help="计算笔力度排名的滚动窗口大小"
)

# 展示选项
st.sidebar.subheader("展示选项")
show_volume = st.sidebar.checkbox("显示成交量", value=True)
show_bi_info = st.sidebar.checkbox("显示笔信息", value=False)

# 主要内容区域
@st.cache_data
def load_data(data_source, symbol=None, freq=None, start_date=None, end_date=None):
    """加载数据"""
    if data_source == "多品种数据":
        df = generate_klines(seed=42)
        # 限制数据量，选择部分品种和时间范围
        symbols = df['symbol'].unique()[:5]  # 取前5个品种
        df = df[df['symbol'].isin(symbols)]
        df = df[df['dt'] >= '2023-01-01']
        df = df[df['dt'] <= '2024-01-01']
    else:
        sdt = start_date.strftime("%Y%m%d")
        edt = end_date.strftime("%Y%m%d")
        df = generate_symbol_kines(symbol, freq, sdt=sdt, edt=edt, seed=42)
    
    return df

def apply_v_reversal_analysis(df, params):
    """应用V字反转分析"""
    try:
        result = mark_v_reversal(
            df, 
            min_power_percentile=params['min_power_percentile'],
            min_retracement=params['min_retracement'],
            min_speed_ratio=params['min_speed_ratio'],
            power_window=params['power_window'],
            verbose=True,
            copy=True,
            rs=False  # 使用标准版本而非rust版本
        )
        return result
    except Exception as e:
        st.error(f"V字反转分析出错: {str(e)}")
        return None

def get_czsc_data(df_symbol):
    """从CZSC对象中提取笔和分型数据"""
    try:
        from czsc.analyze import CZSC
        from czsc.utils.bar_generator import format_standard_kline
        
        # 调试信息
        st.write(f"输入数据长度: {len(df_symbol)}")
        
        bars = format_standard_kline(df_symbol, freq="30分钟")
        st.write(f"格式化后K线数量: {len(bars)}")
        
        c = CZSC(bars, max_bi_num=len(bars))
        st.write(f"生成笔数量: {len(c.bi_list)}")
        st.write(f"生成分型数量: {len(c.fx_list)}")
        
        # 提取笔数据
        bi_data = None
        fx_data = None
        
        if len(c.bi_list) > 0:
            bi_points = []
            for bi in c.bi_list:
                bi_points.append({"dt": bi.fx_a.dt, "price": bi.fx_a.fx, "direction": bi.direction.value})
            # 添加最后一个笔的结束点
            last_bi = c.bi_list[-1]
            bi_points.append({"dt": last_bi.fx_b.dt, "price": last_bi.fx_b.fx, "direction": last_bi.direction.value})
            bi_data = pd.DataFrame(bi_points)
            st.write(f"笔数据提取成功，数据点数量: {len(bi_data)}")
        else:
            st.warning("没有生成笔数据")
        
        # 提取分型数据
        if len(c.fx_list) > 0:
            fx_points = []
            for fx in c.fx_list:
                fx_points.append({"dt": fx.dt, "price": fx.fx, "mark": fx.mark.value})
            fx_data = pd.DataFrame(fx_points)
            st.write(f"分型数据提取成功，数据点数量: {len(fx_data)}")
        else:
            st.warning("没有生成分型数据")
        
        return bi_data, fx_data
        
    except Exception as e:
        st.error(f"提取CZSC数据失败: {str(e)}")
        st.exception(e)
        return None, None

def create_kline_chart(df_symbol, symbol_name, show_bi_chart=True):
    """创建K线图表"""
    # 创建子图
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{symbol_name} K线图', '成交量'),
            row_width=[0.7, 0.3]
        )
    else:
        fig = make_subplots(rows=1, cols=1)
    
    # K线图
    fig.add_trace(
        go.Candlestick(
            x=df_symbol['dt'],
            open=df_symbol['open'],
            high=df_symbol['high'],
            low=df_symbol['low'],
            close=df_symbol['close'],
            name="K线",
            increasing_line_color='red',
            decreasing_line_color='green'
        ),
        row=1, col=1
    )
    
    # 获取CZSC数据（笔和分型）
    if show_bi_chart:
        st.write("🔍 正在提取CZSC笔数据...")
        bi_data, fx_data = get_czsc_data(df_symbol)
        
        # 绘制分型
        if fx_data is not None and not fx_data.empty:
            # 过滤时间范围
            sdt = df_symbol['dt'].min()
            edt = df_symbol['dt'].max()
            fx_filtered = fx_data[(fx_data['dt'] >= sdt) & (fx_data['dt'] <= edt)]
            
            if not fx_filtered.empty:
                st.write(f"绘制分型数量: {len(fx_filtered)}")
                fig.add_trace(
                    go.Scatter(
                        x=fx_filtered['dt'],
                        y=fx_filtered['price'],
                        mode='markers+lines',
                        line=dict(color='white', width=1, dash='dot'),
                        marker=dict(size=6, color='white', symbol='circle'),
                        name='分型',
                        text=[f'分型 {mark}' for mark in fx_filtered['mark']],
                        hovertemplate='%{text}<br>时间: %{x}<br>价格: %{y}<extra></extra>',
                        visible='legendonly'  # 默认隐藏，可在图例中切换
                    ),
                    row=1, col=1
                )
        
        # 绘制笔
        if bi_data is not None and not bi_data.empty:
            # 过滤时间范围
            sdt = df_symbol['dt'].min()
            edt = df_symbol['dt'].max()
            bi_filtered = bi_data[(bi_data['dt'] >= sdt) & (bi_data['dt'] <= edt)]
            
            if not bi_filtered.empty:
                st.write(f"绘制笔数量: {len(bi_filtered)}")
                # 绘制笔连线
                fig.add_trace(
                    go.Scatter(
                        x=bi_filtered['dt'],
                        y=bi_filtered['price'],
                        mode='lines+markers',
                        line=dict(color='yellow', width=2),
                        marker=dict(size=8, color='yellow', symbol='diamond'),
                        name='笔',
                        text=[f'{direction}笔' for direction in bi_filtered['direction']],
                        hovertemplate='%{text}<br>时间: %{x}<br>价格: %{y}<extra></extra>',
                        visible=True
                    ),
                    row=1, col=1
                )
            else:
                st.warning("过滤后没有笔数据在当前时间范围内")
    
    # V字反转标记
    v_up_data = df_symbol[df_symbol['is_v_reversal_up'] == 1]
    v_down_data = df_symbol[df_symbol['is_v_reversal_down'] == 1]
    
    if not v_up_data.empty:
        fig.add_trace(
            go.Scatter(
                x=v_up_data['dt'],
                y=v_up_data['high'] * 1.02,
                mode='markers',
                marker=dict(symbol='triangle-up', size=12, color='blue'),
                name='向上V字反转',
                text='向上V字反转',
                hovertemplate='%{text}<br>时间: %{x}<br>价格: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
    
    if not v_down_data.empty:
        fig.add_trace(
            go.Scatter(
                x=v_down_data['dt'],
                y=v_down_data['low'] * 0.98,
                mode='markers',
                marker=dict(symbol='triangle-down', size=12, color='orange'),
                name='向下V字反转',
                text='向下V字反转',
                hovertemplate='%{text}<br>时间: %{x}<br>价格: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # 成交量
    if show_volume:
        colors = ['red' if close >= open_ else 'green' 
                 for close, open_ in zip(df_symbol['close'], df_symbol['open'])]
        
        fig.add_trace(
            go.Bar(
                x=df_symbol['dt'],
                y=df_symbol['vol'],
                name="成交量",
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )
    
    # 更新布局
    fig.update_layout(
        title=f"{symbol_name} V字反转识别结果",
        xaxis_title="时间",
        yaxis_title="价格",
        height=700 if show_volume else 600,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    if show_volume:
        fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    return fig

def display_statistics(df):
    """显示统计信息"""
    total_bars = len(df)
    v_up_bars = df['is_v_reversal_up'].sum()
    v_down_bars = df['is_v_reversal_down'].sum()
    v_total_bars = df['is_v_reversal'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总K线数", f"{total_bars:,}")
    
    with col2:
        st.metric(
            "向上V字反转", 
            f"{v_up_bars:,}",
            f"{v_up_bars/total_bars:.2%}"
        )
    
    with col3:
        st.metric(
            "向下V字反转", 
            f"{v_down_bars:,}",
            f"{v_down_bars/total_bars:.2%}"
        )
    
    with col4:
        st.metric(
            "总V字反转", 
            f"{v_total_bars:,}",
            f"{v_total_bars/total_bars:.2%}"
        )

# 加载数据按钮
if st.sidebar.button("🔄 重新加载数据", type="primary"):
    st.cache_data.clear()

# 主逻辑
try:
    # 加载数据
    with st.spinner("正在加载数据..."):
        if data_source == "多品种数据":
            df = load_data(data_source)
        else:
            df = load_data(data_source, symbol, freq, start_date, end_date)
    
    st.success(f"数据加载成功！共 {len(df)} 条记录，{df['symbol'].nunique()} 个品种")
    
    # 应用V字反转分析
    params = {
        'min_power_percentile': min_power_percentile,
        'min_retracement': min_retracement,
        'min_speed_ratio': min_speed_ratio,
        'power_window': power_window
    }
    
    with st.spinner("正在进行V字反转识别..."):
        df_result = apply_v_reversal_analysis(df, params)
    
    if df_result is not None:
        st.success("V字反转识别完成！")
        
        # 显示整体统计
        st.subheader("📊 整体统计")
        display_statistics(df_result)
        
        # 品种选择和图表展示
        st.subheader("📈 品种图表")
        
        symbols = sorted(df_result['symbol'].unique())
        selected_symbol = st.selectbox("选择要查看的品种", symbols)
        
        # 筛选选中品种的数据
        df_symbol = df_result[df_result['symbol'] == selected_symbol].copy()
        df_symbol = df_symbol.sort_values('dt').reset_index(drop=True)
        
        # 创建并显示图表
        fig = create_kline_chart(df_symbol, selected_symbol, show_bi_info)
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示该品种的统计信息
        st.subheader(f"📈 {selected_symbol} 详细统计")
        display_statistics(df_symbol)
        
        # 显示V字反转详情
        if show_bi_info:
            st.subheader("🔍 V字反转详情")
            
            v_periods = df_symbol[df_symbol['is_v_reversal'] == 1]
            if not v_periods.empty:
                # 按连续区间分组
                v_periods['group'] = (v_periods['is_v_reversal'] != v_periods['is_v_reversal'].shift()).cumsum()
                
                st.write("V字反转时间段：")
                for group_id, group_data in v_periods.groupby('group'):
                    start_time = group_data['dt'].min()
                    end_time = group_data['dt'].max()
                    v_type = "向上" if group_data['is_v_reversal_up'].any() else "向下"
                    duration = len(group_data)
                    
                    st.write(f"- {v_type}V字反转: {start_time} ~ {end_time} (持续{duration}根K线)")
            else:
                st.info("该品种未识别出V字反转模式")
        
        # 数据预览
        with st.expander("📋 数据预览"):
            st.dataframe(
                df_symbol[['dt', 'open', 'close', 'high', 'low', 'vol', 
                          'is_v_reversal_up', 'is_v_reversal_down', 'is_v_reversal']].head(20)
            )

except Exception as e:
    st.error(f"程序运行出错: {str(e)}")
    st.write("错误详情:")
    st.exception(e)

# 使用说明
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    ### V字反转识别逻辑
    
    1. **力度评估**: 基于笔的价格变化、R平方、成交量三个维度计算综合力度评分
    2. **方向判断**: 识别相邻两笔方向相反的组合
    3. **回撤要求**: 第二笔回撤幅度需要达到第一笔的指定比例以上
    4. **速度要求**: 第二笔的执行速度需要快于第一笔的指定倍数
    
    ### 参数说明
    
    - **最小力度百分位数**: 控制第一个笔的力度要求，越高表示要求笔的力度越强
    - **最小回撤比例**: 第二个笔相对第一个笔的最小回撤比例，默认50%
    - **最小速度比例**: 第二个笔相对第一个笔的最小速度倍数，默认1.5倍
    - **力度排名窗口**: 计算笔力度排名的滚动窗口大小
    
    ### 图表说明
    
    - 🔵 蓝色三角向上: 向上V字反转（先跌后涨）
    - 🟠 橙色三角向下: 向下V字反转（先涨后跌）
    """)