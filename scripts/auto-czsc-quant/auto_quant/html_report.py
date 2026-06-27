"""Self-contained HTML report rendering for experiment results."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.schema import AutoQuantConfig, Candidate


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _table(headers: list[str], rows: list[list[Any]], *, empty: str = "无") -> str:
    if not rows:
        return f"<p class=\"empty\">{escape(empty)}</p>"
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(_fmt(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _leaderboard_table(leaderboard: pd.DataFrame) -> str:
    if leaderboard.empty:
        return "<p class=\"empty\">没有候选通过评分。</p>"
    cols = [
        "rank",
        "id",
        "hypothesis",
        "score",
        "annual_return",
        "sharpe",
        "max_drawdown",
        "trade_count",
        "symbol_coverage",
    ]
    rows = []
    for _, row in leaderboard[cols].iterrows():
        rows.append([row[col] for col in cols])
    return _table(cols, rows)


def _candidate_cards(candidates: list[Candidate], leaderboard: pd.DataFrame) -> str:
    rank_map = {}
    if not leaderboard.empty:
        rank_map = {str(row["id"]): int(row["rank"]) for _, row in leaderboard.iterrows()}

    cards = []
    for candidate in candidates:
        rank = rank_map.get(candidate.id, "-")
        position_text = json.dumps(candidate.position_data, ensure_ascii=False, indent=2)
        cards.append(
            f"""
            <article class="candidate">
              <div class="candidate-head">
                <h3>{escape(candidate.id)}</h3>
                <span>rank: {escape(str(rank))}</span>
              </div>
              <p>{escape(candidate.hypothesis)}</p>
              <details>
                <summary>Position JSON</summary>
                <pre>{escape(position_text)}</pre>
              </details>
            </article>
            """
        )
    return "\n".join(cards) if cards else "<p class=\"empty\">无候选。</p>"


def _artifact_links(run_dir: Path, artifacts: list[Path]) -> str:
    rows = []
    for path in artifacts:
        if path.exists():
            rel = path.relative_to(run_dir)
            rows.append([f"<a href=\"{escape(rel.as_posix())}\">{escape(rel.as_posix())}</a>", path.stat().st_size])
    if not rows:
        return "<p class=\"empty\">无额外产物。</p>"
    head = "<th>file</th><th>bytes</th>"
    body = "".join(f"<tr><td>{row[0]}</td><td>{row[1]}</td></tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def write_html_report(
    path: Path,
    *,
    config: AutoQuantConfig,
    run_dir: Path,
    leaderboard: pd.DataFrame,
    rejected: list[dict[str, Any]],
    candidates: list[Candidate],
    raw_candidate_count: int,
    bars_summary: dict[str, int],
    execution_log: list[dict[str, Any]],
    artifacts: list[Path],
) -> None:
    """Write a structured, dependency-free HTML report."""
    config_rows = [
        ["task_name", config.task_name],
        ["data_source", config.data_source],
        ["candidate_mode", config.candidate_mode],
        ["symbols", ", ".join(config.symbols)],
        ["base_freq", config.base_freq],
        ["date_range", f"{config.sdt} - {config.edt}"],
        ["fee_rate", config.fee_rate],
        ["top_k", config.top_k],
    ]
    if config.feather_path:
        config_rows.append(["feather_path", config.feather_path])
    if config.baseline_position_path:
        config_rows.append(["baseline_position_path", config.baseline_position_path])

    best = None if leaderboard.empty else leaderboard.iloc[0].to_dict()
    rejected_rows = [[item.get("id", "<unknown>"), item.get("reason", "")] for item in rejected]
    bars_rows = [[symbol, count] for symbol, count in bars_summary.items()]
    execution_rows = [
        [
            item.get("step"),
            item.get("status"),
            item.get("duration_sec"),
            item.get("detail", ""),
        ]
        for item in execution_log
    ]

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(config.task_name)} - auto-czsc-quant report</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1f2937; background: #f7f8fa; }}
    header {{ background: #12343b; color: white; padding: 28px 36px; }}
    header h1 {{ margin: 0 0 8px; font-size: 28px; }}
    header p {{ margin: 0; color: #d7e6e8; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 56px; }}
    section {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 18px; padding: 20px; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    h3 {{ margin: 0; font-size: 16px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #fbfcfd; }}
    .metric span {{ display: block; color: #6b7280; font-size: 12px; margin-bottom: 4px; }}
    .metric strong {{ font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; color: #374151; font-weight: 600; }}
    tr:hover td {{ background: #fafafa; }}
    .candidate {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
    .candidate-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .candidate-head span {{ color: #6b7280; font-size: 13px; }}
    details {{ margin-top: 8px; }}
    summary {{ cursor: pointer; color: #0f766e; }}
    pre {{ overflow: auto; background: #111827; color: #e5e7eb; padding: 12px; border-radius: 6px; font-size: 12px; }}
    .empty {{ color: #6b7280; margin: 0; }}
    a {{ color: #0f766e; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(config.task_name)}</h1>
    <p>auto-czsc-quant 优化结果与执行记录</p>
  </header>
  <main>
    <section>
      <h2>结果概览</h2>
      <div class="summary">
        <div class="metric"><span>候选总数</span><strong>{raw_candidate_count}</strong></div>
        <div class="metric"><span>通过校验</span><strong>{len(candidates)}</strong></div>
        <div class="metric"><span>拒绝 / 失败</span><strong>{len(rejected)}</strong></div>
        <div class="metric"><span>最佳候选</span><strong>{escape(_fmt(best.get("id") if best else "-"))}</strong></div>
        <div class="metric"><span>最佳 score</span><strong>{escape(_fmt(best.get("score") if best else "-"))}</strong></div>
        <div class="metric"><span>报告目录</span><strong>{escape(run_dir.name)}</strong></div>
      </div>
    </section>

    <section>
      <h2>运行配置</h2>
      {_table(["key", "value"], config_rows)}
    </section>

    <section>
      <h2>数据加载</h2>
      {_table(["symbol", "bar_count"], bars_rows)}
    </section>

    <section>
      <h2>执行记录</h2>
      {_table(["step", "status", "duration_sec", "detail"], execution_rows)}
    </section>

    <section>
      <h2>Leaderboard</h2>
      {_leaderboard_table(leaderboard)}
    </section>

    <section>
      <h2>候选详情</h2>
      {_candidate_cards(candidates, leaderboard)}
    </section>

    <section>
      <h2>拒绝与失败</h2>
      {_table(["id", "reason"], rejected_rows)}
    </section>

    <section>
      <h2>产物索引</h2>
      {_artifact_links(run_dir, artifacts)}
    </section>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
