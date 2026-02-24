""" 
权重回测报告生成器

支持 HTML (f-string + plotly) 和 PDF (reportlab + plotly) 两种格式的 WeightBacktest 回测报告生成
"""
import os
from typing import Optional, Dict, Any

import pandas as pd

# 尝试从 rs_czsc 导入，失败则使用 Python 版本
try:
    from rs_czsc import WeightBacktest
except ImportError:
    from czsc.py.weight_backtest import WeightBacktest

from .plotting.backtest import (
    get_performance_metrics_cards,
    plot_backtest_stats,
    plot_long_short_comparison,
    plot_colored_table,
    plot_cumulative_returns,
    plot_drawdown_analysis,
    plot_daily_return_distribution,
    plot_monthly_heatmap,
)
from .html_report_builder import HtmlReportBuilder
from .pdf_report_builder import PdfReportBuilder


def _validate_input_data(df: pd.DataFrame) -> None:
    """验证输入数据格式
    
    :param df: 输入数据
    :raises ValueError: 当数据格式不正确时
    """
    required_columns = ["dt", "symbol", "weight", "price"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"数据缺少必需列: {missing_columns}")
    
    if len(df) == 0:
        raise ValueError("输入数据不能为空")
    
    if df[["weight", "price"]].isna().any().any():
        raise ValueError("权重和价格列不能包含空值")


def _prepare_config(kwargs: dict) -> Dict[str, Any]:
    """准备配置参数
    
    :param kwargs: 用户传入的参数
    :return: 配置字典
    """
    default_config = {
        "fee_rate": 0.0002,
        "digits": 2,
        "weight_type": "ts",
        "yearly_days": 252,
        "n_jobs": 1
    }
    
    config = {**default_config, **kwargs}
    return config


def _build_report_params(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, str]:
    """构建报告参数
    
    :param df: 权重数据
    :param config: 配置参数
    :return: 参数字典
    """
    return {
        "日期范围": f"{df['dt'].min().strftime('%Y-%m-%d')} ~ {df['dt'].max().strftime('%Y-%m-%d')}",
        "手续费": f"{config['fee_rate'] * 10000:.2f} BP",
        "小数位": str(config["digits"]),
        "年交易日": str(config["yearly_days"]),
        "标的数": str(df["symbol"].nunique())
    }


def generate_backtest_report(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "权重回测报告",
    **kwargs
) -> str:
    """统一的回测报告生成入口，根据 output_path 的后缀自动选择生成 PDF 或 HTML 报告

    :param df: 包含 dt, symbol, weight, price 列的权重数据
    :param output_path: 报告文件输出路径，根据后缀自动选择格式：
        - .pdf 后缀生成 PDF 报告
        - .html 后缀生成 HTML 报告（默认）
        - 默认为当前目录下的 backtest_report.html
    :param title: 报告标题
    :param kwargs: 回测参数和显示控制
        - fee_rate: float, 单边交易成本，默认 0.0002
        - digits: int, 权重小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
        - yearly_days: int, 年交易日天数，默认 252
        - n_jobs: int, 并行进程数，默认 1
    :return: 报告文件路径
    :raises ValueError: 当输入数据格式不正确时或文件后缀不支持时
    """
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "backtest_report.html")

    ext = os.path.splitext(output_path)[1].lower()

    if ext == ".pdf":
        return generate_pdf_backtest_report(df, output_path=output_path, title=title, **kwargs)
    elif ext in (".html", ".htm"):
        return generate_html_backtest_report(df, output_path=output_path, title=title, **kwargs)
    else:
        raise ValueError(f"不支持的文件后缀 '{ext}'，请使用 .html 或 .pdf")


def generate_html_backtest_report(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "权重回测报告",
    **kwargs
) -> str:
    """生成权重回测的 HTML 报告

    :param df: 包含 dt, symbol, weight, price 列的权重数据
    :param output_path: HTML 文件输出路径，默认为当前目录下的 backtest_report.html
    :param title: 报告标题
    :param kwargs: 回测参数和显示控制
        - fee_rate: float, 单边交易成本，默认 0.0002
        - digits: int, 权重小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
        - yearly_days: int, 年交易日天数，默认 252
        - n_jobs: int, 并行进程数，默认 1
    :return: HTML 文件路径
    :raises ValueError: 当输入数据格式不正确时
    """
    # 验证输入数据
    _validate_input_data(df)
    
    # 准备配置
    config = _prepare_config(kwargs)
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "backtest_report.html")
    
    # 创建回测实例
    wb = WeightBacktest(
        dfw=df,
        fee_rate=config["fee_rate"],
        digits=config["digits"],
        weight_type=config["weight_type"],
        yearly_days=config["yearly_days"],
        n_jobs=config["n_jobs"]
    )
    
    # 提取数据
    metrics = get_performance_metrics_cards(wb.stats)
    charts = _generate_charts(wb, df, config)
    
    # 构建报告
    _build_and_save_report(title, df, config, metrics, charts, output_path)
    
    return output_path


def _build_and_save_report(title: str, df: pd.DataFrame, config: Dict[str, Any], 
                           metrics: list, charts: dict, output_path: str) -> None:
    """构建并保存报告
    
    :param title: 报告标题
    :param df: 权重数据
    :param config: 配置参数
    :param metrics: 绩效指标
    :param charts: 图表字典
    :param output_path: 输出路径
    """
    builder = HtmlReportBuilder(title=title)
    
    # 添加头部
    params = _build_report_params(df, config)
    builder.add_header(params, subtitle="基于权重策略的回测分析与绩效评估")
    
    # 添加绩效指标
    builder.add_metrics(metrics)
    
    # 添加图表标签页
    builder.add_chart_tab("回测统计", charts["backtest_stats"], "bi-grid-1x2", active=True)
    builder.add_chart_tab("多空对比", charts["long_short_comparison"], "bi-arrows-collapse")
    
    # 添加图表区域
    builder.add_charts_section()
    
    # 添加页脚
    builder.add_footer()
    
    # 保存文件
    builder.save(output_path)


def _prepare_daily_returns(wb: WeightBacktest) -> pd.DataFrame:
    """准备日收益数据
    
    :param wb: WeightBacktest 对象
    :return: 处理后的日收益数据
    """
    dret = wb.daily_return.copy()
    dret["dt"] = pd.to_datetime(dret["date"])
    dret = dret.set_index("dt").drop(columns=["date"])
    return dret


def _generate_main_charts(dret: pd.DataFrame) -> dict:
    """生成主要图表
    
    :param dret: 日收益数据
    :return: 图表字典
    """
    config = {'responsive': True, 'displayModeBar': True, 'scrollZoom': True}
    fig_stats = plot_backtest_stats(dret, ret_col="total", title="", template="plotly")
    fig_stats.update_layout(height=1000, autosize=True)
    
    return {
        "backtest_stats": fig_stats.to_html(include_plotlyjs=True, full_html=False, config=config)
    }


class LongShortComparisonChart:
    """多空对比图表生成器"""
    
    def __init__(self, df: pd.DataFrame, config: Dict[str, Any]):
        """初始化多空对比图表生成器
        
        :param df: 原始权重数据
        :param config: 配置参数
        """
        self.df = df
        self.config = config
        self._strategy_data = None
        self._backtests = None
    
    def _create_strategy_data(self) -> dict:
        """创建多空策略数据
        
        :return: 策略数据字典
        """
        if self._strategy_data is not None:
            return self._strategy_data
            
        df_base = self.df[["dt", "symbol", "weight", "price"]].copy()
        
        dfl = df_base.copy()
        dfl["weight"] = dfl["weight"].clip(lower=0)  # 只保留多头
        
        dfs = df_base.copy()
        dfs["weight"] = dfs["weight"].clip(upper=0)  # 只保留空头
        
        dfb = df_base.copy()
        dfb['weight'] = 1  # 基准等权
        
        self._strategy_data = {
            "原始策略": df_base,
            "策略多头": dfl,
            "策略空头": dfs,
            "基准等权": dfb
        }
        return self._strategy_data
    
    def _create_backtests(self) -> dict:
        """创建策略回测实例
        
        :return: 回测实例字典
        """
        if self._backtests is not None:
            return self._backtests
            
        strategy_data = self._create_strategy_data()
        wbs = {}
        for name, data in strategy_data.items():
            weight_type = "ts" if name == "基准等权" else self.config["weight_type"]
            wbs[name] = WeightBacktest(
                data, 
                fee_rate=self.config["fee_rate"], 
                digits=self.config["digits"],
                weight_type=weight_type, 
                yearly_days=self.config["yearly_days"]
            )
        self._backtests = wbs
        return wbs
    
    def _aggregate_daily_returns(self) -> pd.DataFrame:
        """汇总日收益数据
        
        :return: 汇总后的日收益数据
        """
        wbs = self._create_backtests()
        dailys = []
        for strategy, wb_obj in wbs.items():
            daily = wb_obj.daily_return.copy()[["date", "total"]]
            daily["strategy"] = strategy
            daily["return"] = daily["total"]
            daily["dt"] = pd.to_datetime(daily["date"])
            dailys.append(daily[["dt", "strategy", "return"]])
        
        dailys = pd.concat(dailys, axis=0)
        return pd.pivot_table(dailys, index="dt", columns="strategy", values="return")
    
    def _aggregate_strategy_stats(self) -> pd.DataFrame:
        """汇总策略统计信息
        
        :return: 统计信息 DataFrame
        """
        wbs = self._create_backtests()
        stats_rows = []
        for strategy, wb_obj in wbs.items():
            stats = {"策略名称": strategy}
            stats.update(wb_obj.stats)
            stats_rows.append(stats)
        return pd.DataFrame(stats_rows)
    
    def generate(self) -> str:
        """生成多空对比图表
        
        :return: 图表 HTML 字符串
        """
        try:
            # 准备数据
            df_dailys = self._aggregate_daily_returns()
            df_stats = self._aggregate_strategy_stats()
            
            # 生成图表
            plot_config = {'responsive': True, 'displayModeBar': True, 'scrollZoom': True}
            fig_ls = plot_long_short_comparison(df_dailys, df_stats, title="多空收益对比", template="plotly")
            fig_ls.update_layout(height=1000, autosize=True)
            
            return fig_ls.to_html(include_plotlyjs=False, full_html=False, config=plot_config)
            
        except Exception as e:
            return f"<div style='padding: 20px; text-align: center; color: red;'>多空对比图生成失败: {str(e)}</div>"


def _generate_long_short_chart(df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """生成多空对比图表
    
    :param df: 原始权重数据
    :param config: 配置参数
    :return: 图表 HTML 字符串
    """
    chart_generator = LongShortComparisonChart(df, config)
    return chart_generator.generate()


def _generate_charts(wb: WeightBacktest, df: pd.DataFrame, config: Dict[str, Any]) -> dict:
    """生成所有图表
    
    :param wb: WeightBacktest 对象
    :param df: 原始权重数据
    :param config: 配置参数
    :return: 字典，包含所有图表的 HTML 片段
    """
    # 准备日收益数据
    dret = _prepare_daily_returns(wb)
    
    # 生成主要图表
    charts = _generate_main_charts(dret)
    
    # 生成多空对比图表
    charts["long_short_comparison"] = _generate_long_short_chart(df, config)
    
    return charts


# ========== PDF 回测报告 ==========


def _create_long_short_curves_figure(dailys_pivot):
    """为 PDF 创建多空对比累计收益曲线图（不含表格子图）

    :param dailys_pivot: 透视表格式的日收益数据
    :return: Plotly Figure 对象
    """
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    from .plotting.common import add_year_boundary_lines

    target_volatility = 0.2
    trading_days_per_year = 252

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "累计收益曲线对比",
            f"波动率调整后收益对比（目标波动率: {target_volatility:.0%}）",
        ),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5],
    )

    df_cumsum = dailys_pivot.cumsum()
    colors = px.colors.qualitative.Plotly * 10
    for i, col in enumerate(df_cumsum.columns):
        fig.add_trace(
            go.Scatter(x=df_cumsum.index, y=df_cumsum[col], name=col, mode="lines",
                       line=dict(color=colors[i]), legendgroup=col),
            row=1, col=1,
        )

    add_year_boundary_lines(fig, df_cumsum.index, row=1, col=1, line_color="gray", opacity=0.5)

    adjusted_returns = pd.DataFrame(index=dailys_pivot.index)
    for col in dailys_pivot.columns:
        daily_ret = dailys_pivot[col]
        annual_vol = daily_ret.std() * np.sqrt(trading_days_per_year)
        factor = target_volatility / annual_vol if annual_vol > 0 else 1.0
        adjusted_returns[col] = daily_ret * factor

    df_adj_cumsum = adjusted_returns.cumsum()
    for i, col in enumerate(df_adj_cumsum.columns):
        fig.add_trace(
            go.Scatter(x=df_adj_cumsum.index, y=df_adj_cumsum[col], name=f"{col}(调整)",
                       mode="lines", showlegend=False, legendgroup=col,
                       line=dict(color=colors[i])),
            row=2, col=1,
        )

    add_year_boundary_lines(fig, df_adj_cumsum.index, row=2, col=1, line_color="gray", opacity=0.5)

    fig.update_layout(
        title="多空收益对比", template="plotly", height=700,
        margin=dict(l=40, r=40, b=40, t=60),
        hovermode="x unified", showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_yaxes(title_text="累计收益", row=1, col=1)
    fig.update_yaxes(title_text="调整后累计收益", row=2, col=1)
    return fig


def _create_long_short_table_figure(stats_df):
    """为 PDF 创建多空绩效对比表格图

    :param stats_df: 绩效指标 DataFrame
    :return: Plotly Figure 对象
    """
    key_cols = [
        "策略名称", "年化", "夏普", "卡玛", "最大回撤",
        "年化波动率", "交易胜率", "单笔收益", "持仓K线数", "多头占比", "空头占比",
    ]
    available_cols = [c for c in key_cols if c in stats_df.columns]
    table_df = stats_df[available_cols].copy()
    if "策略名称" in table_df.columns:
        table_df = table_df.set_index("策略名称")

    fig = plot_colored_table(
        table_df, title="绩效指标对比", template="plotly", float_fmt=".2f",
        good_high_columns=["年化", "夏普", "卡玛", "交易胜率", "单笔收益"],
    )
    fig.update_layout(height=300, margin=dict(l=40, r=40, b=20, t=60))
    return fig


def _generate_pdf_figures(wb: WeightBacktest, df: pd.DataFrame, config: Dict[str, Any]) -> dict:
    """生成 PDF 报告所需的 Plotly Figure 对象

    :param wb: WeightBacktest 对象
    :param df: 原始权重数据
    :param config: 配置参数
    :return: 字典，key 为图表名称，value 为 Plotly Figure 对象
    """
    dret = _prepare_daily_returns(wb)

    # 回测统计概览图（收益回撤 + 日收益分布 + 月度热力图）
    fig_stats = plot_backtest_stats(dret, ret_col="total", title="回测统计概览", template="plotly")
    fig_stats.update_layout(height=800, margin=dict(l=40, r=40, b=40, t=60))

    # 累计收益曲线
    fig_cum = plot_cumulative_returns(dret, title="累计收益曲线", template="plotly")
    fig_cum.update_layout(height=400, margin=dict(l=40, r=40, b=40, t=60))
    # 强制显示所有品种的累计收益曲线（覆盖 plot_cumulative_returns 中默认仅显示 total 的设置）
    for trace in fig_cum.data:
        trace.visible = True

    # 回撤分析
    fig_dd = plot_drawdown_analysis(dret, ret_col="total", title="回撤分析", template="plotly")
    fig_dd.update_layout(height=400, margin=dict(l=40, r=40, b=40, t=60))

    # 日收益分布
    fig_dist = plot_daily_return_distribution(dret, ret_col="total", title="日收益分布", template="plotly")
    fig_dist.update_layout(height=400, margin=dict(l=40, r=40, b=40, t=60))

    # 月度收益热力图
    fig_heatmap = plot_monthly_heatmap(dret, ret_col="total", title="月度收益热力图", template="plotly")
    fig_heatmap.update_layout(height=400, margin=dict(l=40, r=40, b=40, t=60))

    figures = {
        "backtest_stats": fig_stats,
        "cumulative_returns": fig_cum,
        "drawdown_analysis": fig_dd,
        "daily_return_distribution": fig_dist,
        "monthly_heatmap": fig_heatmap,
    }

    # 多空对比图 —— 为 PDF 导出优化：拆分为两张独立图表（曲线图 + 表格），避免 kaleido 渲染 Table 子图异常
    try:
        ls_chart = LongShortComparisonChart(df, config)
        df_dailys = ls_chart._aggregate_daily_returns()
        df_stats = ls_chart._aggregate_strategy_stats()

        # 累计收益 + 波动率调整后收益（仅 xy 子图，不含 table）
        fig_ls_curves = _create_long_short_curves_figure(df_dailys)
        figures["long_short_comparison"] = fig_ls_curves

        # 绩效对比表（独立表格图）
        fig_ls_table = _create_long_short_table_figure(df_stats)
        figures["long_short_table"] = fig_ls_table
    except Exception:
        pass

    return figures


def _build_and_save_pdf_report(title: str, df: pd.DataFrame, config: Dict[str, Any],
                               metrics: list, figures: dict, output_path: str) -> None:
    """构建并保存 PDF 报告

    :param title: 报告标题
    :param df: 权重数据
    :param config: 配置参数
    :param metrics: 绩效指标
    :param figures: Plotly Figure 字典
    :param output_path: 输出路径
    """
    builder = PdfReportBuilder(title=title)

    # 添加头部
    params = _build_report_params(df, config)
    builder.add_header(params, subtitle="基于权重策略的回测分析与绩效评估")

    # 添加绩效指标
    builder.add_metrics(metrics)

    # 添加图表 —— 每个图表单独一页以保证清晰度
    chart_configs = [
        ("backtest_stats", "回测统计概览", 13.0),
        ("cumulative_returns", "累计收益曲线", 10.0),
        ("drawdown_analysis", "回撤分析", 10.0),
        ("daily_return_distribution", "日收益分布", 10.0),
        ("monthly_heatmap", "月度收益热力图", 10.0),
        ("long_short_comparison", "多空收益对比", 11.0),
        ("long_short_table", "多空绩效指标对比", 6.0),
    ]
    for key, chart_title, height in chart_configs:
        if key in figures:
            builder.add_chart(figures[key], title=chart_title, height=height)

    # 添加页脚
    builder.add_footer()

    # 保存文件
    builder.save(output_path)


def generate_pdf_backtest_report(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "权重回测报告",
    **kwargs
) -> str:
    """生成权重回测的 PDF 报告

    :param df: 包含 dt, symbol, weight, price 列的权重数据
    :param output_path: PDF 文件输出路径，默认为当前目录下的 backtest_report.pdf
    :param title: 报告标题
    :param kwargs: 回测参数和显示控制
        - fee_rate: float, 单边交易成本，默认 0.0002
        - digits: int, 权重小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
        - yearly_days: int, 年交易日天数，默认 252
        - n_jobs: int, 并行进程数，默认 1
    :return: PDF 文件路径
    :raises ValueError: 当输入数据格式不正确时
    """
    # 验证输入数据
    _validate_input_data(df)

    # 准备配置
    config = _prepare_config(kwargs)
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "backtest_report.pdf")

    # 创建回测实例
    wb = WeightBacktest(
        dfw=df,
        fee_rate=config["fee_rate"],
        digits=config["digits"],
        weight_type=config["weight_type"],
        yearly_days=config["yearly_days"],
        n_jobs=config["n_jobs"]
    )

    # 提取数据
    metrics = get_performance_metrics_cards(wb.stats)
    figures = _generate_pdf_figures(wb, df, config)

    # 构建报告
    _build_and_save_pdf_report(title, df, config, metrics, figures, output_path)

    return output_path
