"""
价格敏感性分析 Streamlit 组件

用于分析策略对执行价格的敏感性，通过对比不同交易价格的回测结果来评估价格执行对策略性能的影响。

作者: Assistant
创建时间: 2024年
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from loguru import logger
import czsc


def show_cumulative_returns(df, **kwargs):
    """展示累计收益曲线
    
    :param df: pd.DataFrame, 数据源，index 为日期，columns 为对应上一个日期至今的收益
    :param kwargs: dict, 可选参数
        - fig_title: str, 图表标题，默认 "累计收益"
        - legend_only_cols: list, 仅在图例中显示的列名列表
    """
    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    assert df.index.is_unique, "df 的索引必须唯一"
    assert df.index.is_monotonic_increasing, "df 的索引必须单调递增"

    fig_title = kwargs.get("fig_title", "累计收益")
    df = df.cumsum()
    fig = px.line(df, y=df.columns.to_list(), title=fig_title)
    fig.update_xaxes(title="")

    # 添加每年的开始第一个日期的竖线
    for year in range(df.index.year.min(), df.index.year.max() + 1):
        first_date = df[df.index.year == year].index.min()
        fig.add_vline(x=first_date, line_dash="dash", line_color="red")

    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector=dict(name=col))
        
    # 将 legend 移动到图表的底部并水平居中显示
    fig.update_layout(legend=dict(
        orientation="h",
        y=-0.1,
        xanchor="center",
        x=0.5
    ), margin=dict(l=0, r=0, b=0))
    
    st.plotly_chart(fig, use_container_width=True)


def show_price_sensitive(df, fee=2.0, digits=2, weight_type="ts", n_jobs=1, **kwargs):
    """价格敏感性分析组件
    
    用于分析策略对执行价格的敏感性，通过对比不同交易价格的回测结果来评估价格执行对策略性能的影响。
    
    :param df: pd.DataFrame, 包含以下必要列的数据框：
        - symbol: str, 合约代码
        - dt: datetime, 日期时间
        - weight: float, 仓位权重
        - price: float, 基准价格
        - TP*: float, 以TP开头的交易价格列（如TP_open, TP_high等）
    :param fee: float, 单边费率（BP），默认2.0
    :param digits: int, 小数位数，默认2
    :param weight_type: str, 权重类型，可选 "ts" 或 "cs"，默认 "ts"
    :param n_jobs: int, 并行数，默认1
    :param kwargs: dict, 其他参数
        - title_prefix: str, 标题前缀，默认为空
        - show_detailed_stats: bool, 是否显示详细统计信息，默认False
        - export_results: bool, 是否导出结果，默认False
    
    :return: tuple, (dfr, dfd) 分别为统计结果DataFrame和日收益率DataFrame，失败时返回None
    
    Examples:
    --------
    >>> # 基本用法
    >>> dfr, dfd = show_price_sensitive(df, fee=2.0, digits=2)
    
    >>> # 自定义参数
    >>> dfr, dfd = show_price_sensitive(
    ...     df, 
    ...     fee=1.5, 
    ...     digits=3, 
    ...     weight_type="cs",
    ...     n_jobs=4,
    ...     title_prefix="策略A - ",
    ...     show_detailed_stats=True
    ... )
    """
    from czsc.eda import cal_yearly_days
    
    # 参数处理
    title_prefix = kwargs.get("title_prefix", "")
    show_detailed_stats = kwargs.get("show_detailed_stats", False)
    export_results = kwargs.get("export_results", False)
    
    # 检查必要的列
    required_cols = ["symbol", "dt", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"缺少必要的列: {missing_cols}")
        logger.error(f"数据检查失败，缺少必要的列: {missing_cols}")
        return None
    
    # 查找交易价格列
    tp_cols = [x for x in df.columns if x.startswith("TP")]
    if len(tp_cols) == 0:
        st.error("没有找到交易价格列，请检查文件; 交易价列名必须以 TP 开头")
        logger.error("未找到以TP开头的交易价格列")
        return None
    
    logger.info(f"找到 {len(tp_cols)} 个交易价格列: {tp_cols}")
    
    try:
        yearly_days = cal_yearly_days(dts=df["dt"].unique().tolist())
        logger.info(f"计算得到年化天数: {yearly_days}")
    except Exception as e:
        st.error(f"计算年化天数失败: {e}")
        logger.error(f"计算年化天数失败: {e}")
        return None
    
    # 核心指标对比容器
    c1 = st.container(border=True)
    rows = []
    dfd = pd.DataFrame()
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, tp_col in enumerate(tp_cols):
        try:
            progress = (i + 1) / len(tp_cols)
            progress_bar.progress(progress)
            status_text.text(f"正在处理第 {i+1}/{len(tp_cols)} 个交易价格: {tp_col}")
            
            logger.info(f"正在处理第 {i+1}/{len(tp_cols)} 个交易价格: {tp_col}")
            
            # 准备数据
            df_temp = df.copy()
            df_temp[tp_col] = df_temp[tp_col].fillna(df_temp["price"])
            dfw = df_temp[["symbol", "dt", 'weight', tp_col]].copy()
            dfw.rename(columns={tp_col: "price"}, inplace=True)

            # 创建回测实例
            wb = czsc.WeightBacktest(
                dfw=dfw,
                digits=digits,
                fee_rate=fee/10000,
                weight_type=weight_type,
                n_jobs=n_jobs,
                yearly_days=yearly_days
            )
            
            # 获取日收益率
            daily = wb.daily_return.copy()
            daily.rename(columns={"total": tp_col}, inplace=True)
            
            if dfd.empty:
                dfd = daily[['date', tp_col]].copy()
            else:
                dfd = pd.merge(dfd, daily[['date', tp_col]], on='date', how='outer')

            # 收集统计结果
            res = {"交易价格": tp_col}
            res.update(wb.stats)
            rows.append(res)
            
        except Exception as e:
            st.warning(f"处理交易价格 {tp_col} 时出错: {e}")
            logger.error(f"处理交易价格 {tp_col} 时出错: {e}")
            continue
    
    # 清除进度条
    progress_bar.empty()
    status_text.empty()
    
    if not rows:
        st.error("所有交易价格处理失败，无法生成报告")
        return None

    with c1:
        st.markdown(f"##### :red[{title_prefix}不同交易价格回测核心指标对比]")
        dfr = pd.DataFrame(rows)

        # 选择关键指标展示
        if show_detailed_stats:
            # 显示详细指标
            display_cols = ['交易价格', "开始日期", "结束日期", "绝对收益", "年化", "年化波动率", 
                           "夏普", "最大回撤", "卡玛", "日胜率", "日盈亏比", "交易胜率", 
                           "单笔收益", "持仓K线数", "持仓天数", "多头占比", "空头占比"]
        else:
            # 显示核心指标
            display_cols = ['交易价格', "开始日期", "结束日期", "绝对收益", "年化", "年化波动率", 
                           "夏普", "最大回撤", "卡玛", "交易胜率", "单笔收益", "持仓K线数"]
        
        # 确保所有列都存在
        available_cols = [col for col in display_cols if col in dfr.columns]
        dfr_display = dfr[available_cols].copy()
        
        # 应用样式
        style_subset_positive = [col for col in ["绝对收益", "交易胜率", "年化", "夏普", "卡玛", "单笔收益", "日胜率"] if col in available_cols]
        style_subset_negative = [col for col in ["年化波动率", "最大回撤"] if col in available_cols]
        
        dfr_styled = dfr_display.style
        
        if style_subset_positive:
            dfr_styled = dfr_styled.background_gradient(cmap="RdYlGn_r", subset=style_subset_positive)
        if style_subset_negative:
            dfr_styled = dfr_styled.background_gradient(cmap="RdYlGn", subset=style_subset_negative)
        
        # 格式化数值
        format_dict = {}
        for col in available_cols:
            if col in ["绝对收益", "年化", "年化波动率", "最大回撤", "交易胜率", "日胜率", "多头占比", "空头占比"]:
                format_dict[col] = "{:.2%}"
            elif col in ["夏普", "卡玛", "单笔收益", "日盈亏比"]:
                format_dict[col] = "{:.2f}"
            elif col in ["持仓K线数", "持仓天数"]:
                format_dict[col] = "{:.0f}"
        
        if format_dict:
            dfr_styled = dfr_styled.format(format_dict)
        
        st.dataframe(dfr_styled, use_container_width=True)
        
        # 导出结果选项
        if export_results:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("导出统计结果为CSV"):
                    csv = dfr.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载统计结果",
                        data=csv,
                        file_name=f"price_sensitivity_stats_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("导出日收益率为CSV"):
                    csv = dfd.to_csv(encoding='utf-8-sig')
                    st.download_button(
                        label="下载日收益率",
                        data=csv,
                        file_name=f"price_sensitivity_returns_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    # 累计收益对比容器
    c2 = st.container(border=True)
    with c2:
        st.markdown(f"##### :red[{title_prefix}不同交易价格回测累计收益对比]")
        
        if not dfd.empty:
            dfd_plot = dfd.copy()
            dfd_plot['date'] = pd.to_datetime(dfd_plot['date'])
            dfd_plot.set_index("date", inplace=True)
            
            show_cumulative_returns(
                dfd_plot, 
                fig_title=f"{title_prefix}不同交易价格累计收益对比"
            )
        else:
            st.warning("没有有效的收益率数据用于绘制图表")
    
    logger.info(f"价格敏感性分析完成，共处理 {len(rows)} 个交易价格")
    return dfr, dfd


def price_sensitive_summary(dfr, top_n=3):
    """生成价格敏感性分析摘要
    
    :param dfr: pd.DataFrame, show_price_sensitive 返回的统计结果
    :param top_n: int, 显示前N个最佳交易价格，默认3
    """
    if dfr is None or dfr.empty:
        st.warning("没有可用的分析结果")
        return
    
    with st.container(border=True):
        st.markdown("##### :blue[价格敏感性分析摘要]")
        
        # 按年化收益率排序
        if "年化" in dfr.columns:
            dfr_sorted = dfr.sort_values("年化", ascending=False)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("最佳年化收益率", 
                         f"{dfr_sorted.iloc[0]['年化']:.2%}", 
                         f"交易价格: {dfr_sorted.iloc[0]['交易价格']}")
            
            with col2:
                if "夏普" in dfr.columns:
                    best_sharpe = dfr.loc[dfr["夏普"].idxmax()]
                    st.metric("最佳夏普比率", 
                             f"{best_sharpe['夏普']:.2f}", 
                             f"交易价格: {best_sharpe['交易价格']}")
            
            with col3:
                if "最大回撤" in dfr.columns:
                    min_drawdown = dfr.loc[dfr["最大回撤"].idxmin()]
                    st.metric("最小回撤", 
                             f"{min_drawdown['最大回撤']:.2%}", 
                             f"交易价格: {min_drawdown['交易价格']}")
            
            # 显示前N个最佳交易价格
            st.markdown(f"**前{top_n}个最佳交易价格（按年化收益率）：**")
            top_prices = dfr_sorted.head(top_n)
            for i, (_, row) in enumerate(top_prices.iterrows(), 1):
                st.write(f"{i}. {row['交易价格']}: 年化 {row['年化']:.2%}, 夏普 {row.get('夏普', 'N/A'):.2f if pd.notna(row.get('夏普')) else 'N/A'}")
        
        # 价格敏感性评估
        if len(dfr) > 1 and "年化" in dfr.columns:
            annual_returns = dfr["年化"].values
            sensitivity_score = (annual_returns.max() - annual_returns.min()) / annual_returns.mean()
            
            st.markdown("**敏感性评估：**")
            if sensitivity_score < 0.1:
                st.success(f"🟢 策略对价格执行不敏感 (敏感度: {sensitivity_score:.2%})")
            elif sensitivity_score < 0.3:
                st.warning(f"🟡 策略对价格执行中等敏感 (敏感度: {sensitivity_score:.2%})")
            else:
                st.error(f"🔴 策略对价格执行高度敏感 (敏感度: {sensitivity_score:.2%})") 