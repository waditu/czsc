""" 
权重回测 HTML 报告生成器

使用 Python f-string + plotly 绘图实现 WeightBacktest 回测结果的 HTML 报告生成
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from rs_czsc import WeightBacktest

from .plot_backtest import (
    plot_cumulative_returns,
    plot_drawdown_analysis,
    plot_daily_return_distribution,
    plot_monthly_heatmap,
    get_performance_metrics_cards,
    plot_backtest_stats,
    plot_long_short_comparison
)
from .html_report_builder import HtmlReportBuilder


def generate_backtest_report(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "权重回测报告",
    **kwargs
) -> str:
    """生成权重回测的 HTML 报告
    
    :param df: pd.DataFrame, 包含 dt, symbol, weight, price 列的权重数据
    :param output_path: HTML 文件输出路径，默认为当前目录下的 backtest_report.html
    :param title: 报告标题
    :param kwargs: 回测参数和显示控制
        - fee_rate: float, 单边交易成本，默认 0.0002
        - digits: int, 权重小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
        - yearly_days: int, 年交易日天数，默认 252
        - n_jobs: int, 并行进程数，默认 1
    :return: HTML 文件路径
    """
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "backtest_report.html")
    
    # 提取回测参数
    fee_rate = kwargs.get("fee_rate", 0.0002)
    digits = kwargs.get("digits", 2)
    weight_type = kwargs.get("weight_type", "ts")
    yearly_days = kwargs.get("yearly_days", 252)
    n_jobs = kwargs.get("n_jobs", 1)
    
    # 创建 WeightBacktest 对象
    wb = WeightBacktest(
        dfw=df,
        fee_rate=fee_rate,
        digits=digits,
        weight_type=weight_type,
        yearly_days=yearly_days,
        n_jobs=n_jobs
    )
    
    # 提取数据
    metrics = _extract_metrics(wb)
    charts = _generate_charts(wb, df, fee_rate, digits, weight_type, yearly_days)
    
    # 使用新的 HtmlReportBuilder 生成报告
    builder = HtmlReportBuilder(title=title)
    
    # 添加头部
    params = {
        "日期范围": f"{df['dt'].min().strftime('%Y-%m-%d')} ~ {df['dt'].max().strftime('%Y-%m-%d')}",
        "手续费": f"{fee_rate * 10000:.2f} BP",
        "小数位": str(digits),
        "年交易日": str(yearly_days),
        "标的数": str(df["symbol"].nunique())
    }
    builder.add_header(params, subtitle="基于权重策略的回测分析与绩效评估")
    
    # 添加绩效指标
    builder.add_metrics(metrics)
    
    # 添加图表标签页
    # 第一个图表设为激活状态
    builder.add_chart_tab("回测统计", charts["backtest_stats"], "bi-grid-1x2", active=True)
    builder.add_chart_tab("多空对比", charts["long_short_comparison"], "bi-arrows-collapse")
    
    # 添加图表区域
    builder.add_charts_section()
    
    # 添加页脚
    builder.add_footer()
    
    # 保存文件
    builder.save(output_path)
    
    return output_path


def _extract_metrics(wb: WeightBacktest) -> list:
    """提取核心绩效指标
    
    :param wb: WeightBacktest 对象
    :return: 指标列表，每个元素为 {"label": str, "value": str, "is_positive": bool}
    """
    return get_performance_metrics_cards(wb.stats)


def _generate_charts(wb: WeightBacktest, df: pd.DataFrame, fee_rate: float, 
                     digits: int, weight_type: str, yearly_days: int) -> dict:
    """生成所有图表
    
    :param wb: WeightBacktest 对象
    :param df: 原始权重数据
    :param fee_rate: 手续费率
    :param digits: 权重小数位数
    :param weight_type: 权重类型
    :param yearly_days: 年交易日天数
    :return: 字典，包含所有图表的 HTML 片段
    """
    dret = wb.daily_return.copy()
    dret["dt"] = pd.to_datetime(dret["date"])
    dret = dret.set_index("dt").drop(columns=["date"])
    
    # 生成图表，第一个图表包含 Plotly.js，后续图表不包含
    config = {'responsive': True, 'displayModeBar': True, 'scrollZoom': True}
    fig_stats = plot_backtest_stats(dret, ret_col="total", title="回测统计概览", template="plotly")
    # fig1 = plot_cumulative_returns(dret, title="累计收益曲线", template="plotly")
    # fig2 = plot_drawdown_analysis(dret, ret_col="total", title="回撤分析", template="plotly")
    # fig3 = plot_daily_return_distribution(dret, ret_col="total", title="日收益分布", template="plotly")
    # fig4 = plot_monthly_heatmap(dret, ret_col="total", title="月度收益热力图", template="plotly")

    # 设置图表高度并启用自动调整，确保内容完整显示且自适应宽度
    fig_stats.update_layout(height=1000, autosize=True)
    # for fig in [fig1, fig2, fig3, fig4]:
    #     fig.update_layout(height=600, autosize=True)
    
    charts = {
        "backtest_stats": fig_stats.to_html(include_plotlyjs=True, full_html=False, config=config),
        # "cumulative_returns": fig1.to_html(include_plotlyjs=False, full_html=False, config=config),
        # "drawdown": fig2.to_html(include_plotlyjs=False, full_html=False, config=config),
        # "daily_return": fig3.to_html(include_plotlyjs=False, full_html=False, config=config),
        # "monthly_heatmap": fig4.to_html(include_plotlyjs=False, full_html=False, config=config),
    }
    
    # 生成多空对比图表
    try:
        # 拆分数据创建多个回测（参考 show_long_short_backtest）
        df_base = df[["dt", "symbol", "weight", "price"]].copy()
        
        dfl = df_base.copy()
        dfl["weight"] = dfl["weight"].clip(lower=0)  # 只保留多头
        
        dfs = df_base.copy()
        dfs["weight"] = dfs["weight"].clip(upper=0)  # 只保留空头
        
        dfb = df_base.copy()
        dfb['weight'] = 1  # 基准等权
        
        # 创建多个回测实例
        wbs = {
            "原始策略": WeightBacktest(df_base, fee_rate=fee_rate, digits=digits, 
                                       weight_type=weight_type, yearly_days=yearly_days),
            "策略多头": WeightBacktest(dfl, fee_rate=fee_rate, digits=digits, 
                                      weight_type=weight_type, yearly_days=yearly_days),
            "策略空头": WeightBacktest(dfs, fee_rate=fee_rate, digits=digits, 
                                      weight_type=weight_type, yearly_days=yearly_days),
            "基准等权": WeightBacktest(dfb, fee_rate=fee_rate, digits=digits, 
                                      weight_type="ts", yearly_days=yearly_days),
        }
        
        # 汇总日收益数据（参考 show_multi_backtest）
        dailys = []
        for strategy, wb_obj in wbs.items():
            daily = wb_obj.daily_return.copy()[["date", "total"]]
            daily["strategy"] = strategy
            daily["return"] = daily["total"]
            daily["dt"] = daily["date"]
            dailys.append(daily[["dt", "strategy", "return"]])
        
        dailys = pd.concat(dailys, axis=0)
        dailys["dt"] = pd.to_datetime(dailys["dt"])
        df_dailys = pd.pivot_table(dailys, index="dt", columns="strategy", values="return")
        
        # 汇总绩效指标
        stats_rows = []
        for strategy, wb_obj in wbs.items():
            stats = {"策略名称": strategy}
            stats.update(wb_obj.stats)
            stats_rows.append(stats)
        df_stats = pd.DataFrame(stats_rows)
        
        # 生成多空对比图表
        fig_ls = plot_long_short_comparison(df_dailys, df_stats, title="多空收益对比", template="plotly")
        fig_ls.update_layout(height=1000, autosize=True)
        charts["long_short_comparison"] = fig_ls.to_html(include_plotlyjs=False, full_html=False, config=config)
    except Exception as e:
        # 如果多空对比生成失败，不影响其他图表
        charts["long_short_comparison"] = f"<div style='padding: 20px; text-align: center; color: red;'>多空对比图生成失败: {str(e)}</div>"
    
    return charts
