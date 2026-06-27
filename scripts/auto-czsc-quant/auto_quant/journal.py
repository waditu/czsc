"""Experiment journal rendering."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.schema import AutoQuantConfig


def _markdown_table(df: pd.DataFrame) -> str:
    """Render a small markdown table without optional tabulate dependency."""
    if df.empty:
        return ""
    headers = [str(x) for x in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[col]).replace("\n", " ") for col in df.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_journal(
    path: Path,
    *,
    config: AutoQuantConfig,
    leaderboard: pd.DataFrame,
    rejected: list[dict[str, Any]],
) -> None:
    """Write a compact markdown record for replay and next-round prompting."""
    lines = [
        f"# {config.task_name}",
        "",
        f"- run_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- symbols: {', '.join(config.symbols)}",
        f"- base_freq: {config.base_freq}",
        f"- candidates_scored: {len(leaderboard)}",
        f"- candidates_rejected: {len(rejected)}",
        "",
        "## Leaderboard",
        "",
    ]

    if leaderboard.empty:
        lines.append("没有候选通过评分。")
    else:
        cols = ["rank", "id", "hypothesis", "score", "annual_return", "sharpe", "max_drawdown", "trade_count"]
        lines.append(_markdown_table(leaderboard[cols].head(10)))

    if rejected:
        lines.extend(["", "## Rejected", ""])
        for item in rejected[:20]:
            lines.append(f"- {item.get('id', '<unknown>')}: {item['reason']}")

    lines.extend(
        [
            "",
            "## Next Round",
            "",
            "使用 `python -m auto_quant.cli prompt --run-dir <本目录>` 生成下一轮 /goal 输入。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
