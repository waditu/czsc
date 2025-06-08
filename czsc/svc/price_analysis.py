"""
价格敏感性分析模块

用于分析策略对执行价格的敏感性，通过对比不同交易价格的回测结果来评估价格执行对策略性能的影响。

主要功能：
1. 累计收益曲线展示
2. 价格敏感性分析
3. 分析结果摘要

作者: czsc
"""

import pandas as pd
import streamlit as st
from loguru import logger
from typing import Optional, Tuple

from .base import safe_import_weight_backtest, apply_stats_style
from .returns import show_cumulative_returns


def show_price_sensitive(df: pd.DataFrame, 
                        fee: float = 2.0, 
                        digits: int = 2, 
                        weight_type: str = "ts", 
                        n_jobs: int = 1, 
                        **kwargs) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
    """价格敏感性分析组件
    
    分析策略对执行价格的敏感性，通过对比不同交易价格的回测结果来评估价格执行对策略性能的影响。
    
    参数:
        df: 包含以下必要列的数据框：
            - symbol: 合约代码
            - dt: 日期时间
            - weight: 仓位权重
            - price: 基准价格
            - TP*: 以TP开头的交易价格列（如TP_open, TP_high等）
        fee: 单边费率（BP），默认2.0
        digits: 小数位数，默认2
        weight_type: 权重类型，可选 "ts" 或 "cs"，默认 "ts"
        n_jobs: 并行数，默认1
        **kwargs: 其他参数
            - title_prefix: 标题前缀，默认为空
            - show_detailed_stats: 是否显示详细统计信息，默认False
    
    返回:
        tuple: (dfr, dfd) 分别为统计结果DataFrame和日收益率DataFrame，失败时返回None
    
    示例:
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
    
    # 数据验证
    required_cols = ["symbol", "dt", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        error_msg = f"缺少必要的列: {missing_cols}"
        st.error(error_msg)
        logger.error(f"数据检查失败，{error_msg}")
        return None
    
    # 查找交易价格列
    tp_cols = [x for x in df.columns if x.startswith("TP")]
    if not tp_cols:
        error_msg = "没有找到交易价格列，请检查文件；交易价列名必须以 TP 开头"
        st.error(error_msg)
        logger.error("未找到以TP开头的交易价格列")
        return None
    
    logger.info(f"找到 {len(tp_cols)} 个交易价格列: {tp_cols}")
    
    # 计算年化天数
    try:
        yearly_days = cal_yearly_days(dts=df["dt"].unique().tolist())
        logger.info(f"计算得到年化天数: {yearly_days}")
    except Exception as e:
        error_msg = f"计算年化天数失败: {e}"
        st.error(error_msg)
        logger.error(error_msg)
        return None
    
    # 获取WeightBacktest类
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        st.error("无法导入回测类，请检查 czsc 安装")
        return None
    
    # 结果收集
    c1 = st.container(border=True)
    rows = []
    dfd = pd.DataFrame()
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 逐个处理交易价格
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
            wb = WeightBacktest(
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
            warning_msg = f"处理交易价格 {tp_col} 时出错: {e}"
            st.warning(warning_msg)
            logger.error(warning_msg)
            continue
    
    # 清除进度条
    progress_bar.empty()
    status_text.empty()
    
    if not rows:
        st.error("所有交易价格处理失败，无法生成报告")
        return None


    # 显示结果
    with c1:
        st.markdown(f"##### :red[{title_prefix}不同交易价格回测核心指标对比]")
        dfr = pd.DataFrame(rows)

        # 敏感性评估
        if len(dfr) > 1 and "年化" in dfr.columns:
            _show_sensitivity_assessment(dfr)

        # 选择显示列
        if show_detailed_stats:
            display_cols = ['交易价格', "开始日期", "结束日期", "绝对收益", "年化", "年化波动率", 
                           "夏普", "最大回撤", "卡玛", "日胜率", "日盈亏比", "交易胜率", 
                           "单笔收益", "持仓K线数", "持仓天数", "多头占比", "空头占比"]
        else:
            display_cols = ['交易价格', "开始日期", "结束日期", "绝对收益", "年化", "年化波动率", 
                           "夏普", "最大回撤", "卡玛", "交易胜率", "单笔收益", "持仓K线数"]
        
        # 确保所有列都存在
        available_cols = [col for col in display_cols if col in dfr.columns]
        dfr_display = dfr[available_cols].copy()
        
        # 应用样式
        dfr_styled = apply_stats_style(dfr_display)
        st.dataframe(dfr_styled, use_container_width=True)
    
    # 累计收益对比
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


def _show_sensitivity_assessment(dfr: pd.DataFrame) -> None:
    """显示敏感性评估"""
    annual_returns = dfr["年化"]
    sensitivity_score = (annual_returns.max() - annual_returns.min()) / annual_returns.mean()
    
    st.markdown("**敏感性评估：**")
    if sensitivity_score < 0.1:
        st.success(f"🟢 策略对价格执行不敏感 (敏感度: {sensitivity_score:.2%})")
    elif sensitivity_score < 0.3:
        st.warning(f"🟡 策略对价格执行中等敏感 (敏感度: {sensitivity_score:.2%})")
    else:
        st.error(f"🔴 策略对价格执行高度敏感 (敏感度: {sensitivity_score:.2%})")


# 支持的函数列表
__all__ = [
    'show_price_sensitive', 
] 