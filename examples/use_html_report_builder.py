"""
HtmlReportBuilder example aligned with the retained public surface.
"""

from __future__ import annotations

from pathlib import Path

from czsc import generate_backtest_report, mock
from czsc.utils.html_report_builder import HtmlReportBuilder


def basic_example(output_dir: Path):
    builder = HtmlReportBuilder(title="CZSC HTML Report")
    builder.add_header({"report": "demo", "source": "retained api"}, subtitle="Minimal HtmlReportBuilder example")
    builder.add_metrics(
        [
            {"label": "Total Return", "value": "12.4%", "is_positive": True},
            {"label": "Max Drawdown", "value": "-4.2%", "is_positive": False},
        ]
    )
    builder.add_footer()
    builder.save(output_dir / "html_report_builder_basic.html")


def backtest_example(output_dir: Path):
    dfw = mock.generate_klines_with_weights(seed=42)
    generate_backtest_report(
        df=dfw,
        output_path=output_dir / "html_report_builder_backtest.html",
        title="Backtest Report",
        fee_rate=0.0002,
        digits=2,
        weight_type="ts",
        yearly_days=252,
    )


def main():
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    basic_example(output_dir)
    backtest_example(output_dir)


if __name__ == "__main__":
    main()
