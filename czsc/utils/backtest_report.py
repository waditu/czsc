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
    
    # 生成 HTML
    html_content = _build_html_template(
        report_title=title,
        start_date=df["dt"].min().strftime("%Y-%m-%d"),
        end_date=df["dt"].max().strftime("%Y-%m-%d"),
        fee=fee_rate * 10000,
        digits=digits,
        yearly_days=yearly_days,
        num_symbols=df["symbol"].nunique(),
        metrics=metrics,
        charts=charts
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return output_path


def _build_html_template(
    report_title: str,
    start_date: str,
    end_date: str,
    fee: float,
    digits: int,
    yearly_days: int,
    num_symbols: int,
    metrics: list,
    charts: dict
) -> str:
    """构建完整的 HTML 报告
    
    :param report_title: 报告标题
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param fee: 手续费
    :param digits: 权重小数位数
    :param yearly_days: 年交易日天数
    :param num_symbols: 标的数
    :param metrics: 绩效指标列表
    :param charts: 图表字典
    :return: HTML 字符串
    """
    # 生成指标卡片 HTML
    metrics_html = "\n".join([
        f'''                <div class="col-6 col-md-4 col-lg-3 col-xl-2">
                    <div class="metric-card">
                        <div class="metric-value {"metric-positive" if m["is_positive"] else "metric-negative"}">
                            {m["value"]}
                        </div>
                        <div class="metric-label">{m["label"]}</div>
                    </div>
                </div>'''
        for m in metrics
    ])
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建完整 HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    
    <style>
        :root {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --accent-green: #28a745;
            --accent-red: #dc3545;
            --accent-blue: #007bff;
            --accent-yellow: #ffc107;
            --border-color: #dee2e6;
            --shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            overflow-x: hidden;
        }}
        
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.5;
            display: flex;
            flex-direction: column;
        }}
        
        .header-section {{
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 1.5rem 0;
            margin-bottom: 1.5rem;
        }}
        
        .header-title {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.3rem;
        }}
        
        .header-subtitle {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .param-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        
        .param-badge {{
            background-color: var(--bg-primary);
            color: var(--text-secondary);
            padding: 0.35rem 0.7rem;
            border-radius: 6px;
            font-size: 0.8rem;
            border: 1px solid var(--border-color);
            transition: all 0.2s;
        }}
        
        .param-badge:hover {{
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }}
        
        .main-content {{
            flex: 1;
            padding: 0 0.5rem 0.5rem 0.5rem;
        }}
        
        .container {{
            max-width: 100%;
            padding: 0 0.5rem;
        }}
        
        .metric-card {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s;
            box-shadow: var(--shadow);
            height: 100%;
        }}
        
        .metric-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border-color: var(--accent-blue);
        }}
        
        .metric-value {{
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }}
        
        .metric-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .metric-positive {{
            color: var(--accent-green);
        }}
        
        .metric-negative {{
            color: var(--accent-red);
        }}
        
        .metric-neutral {{
            color: var(--accent-blue);
        }}
        
        .chart-card {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
            height: calc(100vh - 200px);
        }}
        
        .chart-header {{
            background: var(--bg-secondary);
            padding: 0.8rem 1.2rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .chart-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0;
            color: var(--text-primary);
        }}
        
        .chart-body {{
            padding: 0;
            height: calc(100% - 56px);
            width: 100%;
        }}
        
        .chart-body .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
        
        /* Fix for Plotly layout issues */
        .js-plotly-plot *, .plot-container * {{
            box-sizing: content-box;
        }}
        
        .nav-tabs {{
            border-bottom: 2px solid var(--border-color);
            background: var(--bg-secondary);
        }}
        
        .nav-tabs .nav-link {{
            color: var(--text-secondary);
            border: none;
            border-bottom: 3px solid transparent;
            padding: 0.8rem 1.2rem;
            transition: all 0.2s;
            font-size: 0.9rem;
        }}
        
        .nav-tabs .nav-link:hover {{
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }}
        
        .nav-tabs .nav-link.active {{
            color: var(--accent-blue);
            background: var(--bg-primary);
            border-bottom-color: var(--accent-blue);
        }}
        
        .tab-content {{
            background: var(--bg-primary);
            padding: 0;
            height: 100%;
        }}
        
        .tab-pane {{
            height: 100%;
        }}
        
        .data-table {{
            background: var(--bg-primary);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }}
        
        .table {{
            color: var(--text-primary);
            margin-bottom: 0;
            font-size: 0.9rem;
        }}
        
        .table thead th {{
            background: var(--bg-secondary);
            border-bottom: 2px solid var(--border-color);
            color: var(--text-primary);
            font-weight: 600;
            padding: 0.8rem;
            text-transform: uppercase;
            font-size: 0.75rem;
        }}
        
        .table tbody tr {{
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }}
        
        .table tbody tr:hover {{
            background: var(--bg-secondary);
        }}
        
        .table tbody td {{
            padding: 0.8rem;
            vertical-align: middle;
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.3rem;
            border-bottom: 2px solid var(--border-color);
        }}
        
        .section-title {{
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
        }}
        
        .section-icon {{
            margin-right: 0.5rem;
            color: var(--accent-blue);
        }}
        
        .footer {{
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 1rem 0;
            margin-top: auto;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        @media (max-width: 768px) {{
            .header-title {{
                font-size: 1.4rem;
            }}
            
            .metric-value {{
                font-size: 1.3rem;
            }}
            
            .nav-tabs .nav-link {{
                padding: 0.6rem 0.8rem;
                font-size: 0.85rem;
            }}
            
            .chart-card {{
                height: 70vh;
            }}
            
            .main-content {{
                padding: 0 0.5rem 0.5rem 0.5rem;
            }}
        }}
        
        @media (min-width: 1400px) {{
            .container {{
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <!-- 头部区域 -->
    <div class="header-section">
        <div class="container">
            <div class="row">
                <div class="col-12">
                    <h1 class="header-title">
                        <i class="bi bi-graph-up-arrow section-icon"></i>
                        {report_title}
                    </h1>
                    <p class="header-subtitle">基于权重策略的回测分析与绩效评估</p>
                    
                    <div class="param-badges">
                        <span class="param-badge">
                            <i class="bi bi-calendar3"></i> {start_date} ~ {end_date}
                        </span>
                        <span class="param-badge">
                            <i class="bi bi-cash-coin"></i> 手续费: {fee:.2f} BP
                        </span>
                        <span class="param-badge">
                            <i class="bi bi-percent"></i> 小数位: {digits}
                        </span>
                        <span class="param-badge">
                            <i class="bi bi-calendar-week"></i> 年交易日: {yearly_days}
                        </span>
                        <span class="param-badge">
                            <i class="bi bi-collection"></i> 标的数: {num_symbols}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 主要内容区域 -->
    <div class="main-content">
        <div class="container">
            <!-- 核心绩效指标 -->
            <section class="mb-4">
                <div class="section-header">
                    <i class="bi bi-speedometer2 section-icon"></i>
                    <h2 class="section-title">核心绩效指标</h2>
                </div>
                
                <div class="row g-2">
{metrics_html}
                </div>
            </section>
            
            <!-- 图表展示区域 -->
            <section class="mb-4">
                <div class="section-header">
                    <i class="bi bi-bar-chart-line section-icon"></i>
                    <h2 class="section-title">可视化分析</h2>
                </div>
                
                <div class="chart-card">
                    <ul class="nav nav-tabs" id="chartTabs" role="tablist">
                        <li class="nav-item">
                            <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#stats" type="button" role="tab">
                                <i class="bi bi-grid-1x2"></i> 回测统计
                            </button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#cumulative" type="button" role="tab">
                                <i class="bi bi-graph-up"></i> 累计收益
                            </button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#drawdown" type="button" role="tab">
                                <i class="bi bi-graph-down-arrow"></i> 回撤分析
                            </button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#daily-return" type="button" role="tab">
                                <i class="bi bi-bar-chart"></i> 日收益分布
                            </button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#monthly-heatmap" type="button" role="tab">
                                <i class="bi bi-grid-3x3-gap"></i> 月度热力图
                            </button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#long-short" type="button" role="tab">
                                <i class="bi bi-arrows-collapse"></i> 多空对比
                            </button>
                        </li>
                    </ul>
                    
                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="stats" role="tabpanel">
                            <div class="chart-body">
                                {charts["backtest_stats"]}
                            </div>
                        </div>
                        <div class="tab-pane fade" id="cumulative" role="tabpanel">
                            <div class="chart-body">
                                {charts["cumulative_returns"]}
                            </div>
                        </div>
                        <div class="tab-pane fade" id="drawdown" role="tabpanel">
                            <div class="chart-body">
                                {charts["drawdown"]}
                            </div>
                        </div>
                        <div class="tab-pane fade" id="daily-return" role="tabpanel">
                            <div class="chart-body">
                                {charts["daily_return"]}
                            </div>
                        </div>
                        <div class="tab-pane fade" id="monthly-heatmap" role="tabpanel">
                            <div class="chart-body">
                                {charts["monthly_heatmap"]}
                            </div>
                        </div>
                        <div class="tab-pane fade" id="long-short" role="tabpanel">
                            <div class="chart-body">
                                {charts["long_short_comparison"]}
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
    
    <!-- 页脚 -->
    <footer class="footer">
        <div class="container">
            <p class="mb-0">
                <i class="bi bi-code-square"></i>
                由 CZSC 缠中说禅技术分析工具生成 | 
                <i class="bi bi-clock-history"></i>
                生成时间: {current_time}
            </p>
        </div>
    </footer>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 监听 Tab 切换事件，重新调整图表大小
        document.addEventListener('DOMContentLoaded', function() {{
            var triggerTabList = [].slice.call(document.querySelectorAll('button[data-bs-toggle="tab"]'))
            triggerTabList.forEach(function(triggerEl) {{
                triggerEl.addEventListener('shown.bs.tab', function(event) {{
                    // 获取目标 Tab 面板 ID
                    var targetId = event.target.getAttribute('data-bs-target');
                    var targetPane = document.querySelector(targetId);
                    
                    // 查找该面板内的 Plotly 图表
                    var plotlyDiv = targetPane.querySelector('.plotly-graph-div');
                    if (plotlyDiv) {{
                        Plotly.Plots.resize(plotlyDiv);
                    }}
                }})
            }})
            
            // 窗口大小改变时也触发 resize
            window.addEventListener('resize', function() {{
                var activePane = document.querySelector('.tab-pane.active');
                if (activePane) {{
                    var plotlyDiv = activePane.querySelector('.plotly-graph-div');
                    if (plotlyDiv) {{
                        Plotly.Plots.resize(plotlyDiv);
                    }}
                }}
            }});
        }});
    </script>
</body>
</html>
    """
    
    return html_content


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
    config = {'responsive': True, 'displayModeBar': True}
    fig_stats = plot_backtest_stats(dret, ret_col="total", title="回测统计概览", template="plotly")
    fig1 = plot_cumulative_returns(dret, title="累计收益曲线", template="plotly")
    fig2 = plot_drawdown_analysis(dret, ret_col="total", title="回撤分析", template="plotly")
    fig3 = plot_daily_return_distribution(dret, ret_col="total", title="日收益分布", template="plotly")
    fig4 = plot_monthly_heatmap(dret, ret_col="total", title="月度收益热力图", template="plotly")
    
    charts = {
        "backtest_stats": fig_stats.to_html(include_plotlyjs=True, full_html=False, config=config),
        "cumulative_returns": fig1.to_html(include_plotlyjs=False, full_html=False, config=config),
        "drawdown": fig2.to_html(include_plotlyjs=False, full_html=False, config=config),
        "daily_return": fig3.to_html(include_plotlyjs=False, full_html=False, config=config),
        "monthly_heatmap": fig4.to_html(include_plotlyjs=False, full_html=False, config=config),
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
        charts["long_short_comparison"] = fig_ls.to_html(include_plotlyjs=False, full_html=False, config=config)
    except Exception as e:
        # 如果多空对比生成失败，不影响其他图表
        charts["long_short_comparison"] = f"<div style='padding: 20px; text-align: center; color: red;'>多空对比图生成失败: {str(e)}</div>"
    
    return charts



