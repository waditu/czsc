""" 
权重回测 HTML 报告生成器

使用 Python f-string + plotly 绘图实现 WeightBacktest 回测结果的 HTML 报告生成
"""
import os
from typing import Optional, Dict, Any

import pandas as pd
from rs_czsc import WeightBacktest

from .plot_backtest import (
    get_performance_metrics_cards,
    plot_backtest_stats,
    plot_long_short_comparison
)
from .html_report_builder import HtmlReportBuilder


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
