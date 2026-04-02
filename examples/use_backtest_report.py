"""
Backtest report example using the retained public surface.
"""

from __future__ import annotations

from pathlib import Path

from czsc import generate_backtest_report, mock
from czsc.utils.backtest_report import generate_pdf_backtest_report


def main():
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    dfw = mock.generate_klines_with_weights(seed=42)

    generate_backtest_report(
        dfw,
        output_path=output_dir / "backtest_report.html",
        title="CZSC Backtest Report",
        fee_rate=0.0002,
    )

    generate_pdf_backtest_report(
        dfw,
        output_path=output_dir / "backtest_report.pdf",
        title="CZSC Backtest Report",
        fee_rate=0.0002,
    )


if __name__ == "__main__":
    main()
