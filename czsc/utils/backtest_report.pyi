import pandas as pd
from .html_report_builder import HtmlReportBuilder as HtmlReportBuilder
from .pdf_report_builder import PdfReportBuilder as PdfReportBuilder
from .plotting.backtest import get_performance_metrics_cards as get_performance_metrics_cards, plot_backtest_stats as plot_backtest_stats, plot_colored_table as plot_colored_table, plot_long_short_comparison as plot_long_short_comparison
from _typeshed import Incomplete
from typing import Any

def generate_backtest_report(df: pd.DataFrame, output_path: str | None = None, title: str = '权重回测报告', **kwargs) -> str: ...
def generate_html_backtest_report(df: pd.DataFrame, output_path: str | None = None, title: str = '权重回测报告', **kwargs) -> str: ...

class LongShortComparisonChart:
    df: Incomplete
    config: Incomplete
    def __init__(self, df: pd.DataFrame, config: dict[str, Any]) -> None: ...
    def generate(self) -> str: ...

def generate_pdf_backtest_report(df: pd.DataFrame, output_path: str | None = None, title: str = '权重回测报告', **kwargs) -> str: ...
