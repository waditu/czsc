"""Self-contained HTML report rendering for experiment results."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.schema import AutoQuantConfig, Candidate


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_class(value: Any, *, invert: bool = False) -> str:
    number = _num(value)
    if number is None or abs(number) < 1e-12:
        return "neutral"
    positive = number > 0
    if invert:
        positive = not positive
    return "good" if positive else "bad"


def _table(headers: list[str], rows: list[list[Any]], *, empty: str = "无") -> str:
    if not rows:
        return f"<p class=\"empty\">{escape(empty)}</p>"
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(_fmt(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _row_by_id(leaderboard: pd.DataFrame, candidate_id: str) -> dict[str, Any] | None:
    if leaderboard.empty or "id" not in leaderboard:
        return None
    matched = leaderboard[leaderboard["id"].astype(str) == candidate_id]
    if matched.empty:
        return None
    return matched.iloc[0].to_dict()


def _score_width(score: Any, min_score: float, max_score: float) -> int:
    value = _num(score)
    if value is None:
        return 0
    if abs(max_score - min_score) < 1e-12:
        return 100
    return max(4, min(100, int((value - min_score) / (max_score - min_score) * 100)))


def _leaderboard_table(leaderboard: pd.DataFrame) -> str:
    if leaderboard.empty:
        return "<p class=\"empty\">没有候选通过评分。</p>"

    scores = [_num(x) for x in leaderboard["score"].tolist()]
    numeric_scores = [x for x in scores if x is not None]
    min_score = min(numeric_scores) if numeric_scores else 0.0
    max_score = max(numeric_scores) if numeric_scores else 0.0

    rows = []
    for _, row in leaderboard.iterrows():
        score = row.get("score")
        width = _score_width(score, min_score, max_score)
        annual = row.get("annual_return")
        sharpe = row.get("sharpe")
        drawdown = row.get("max_drawdown")
        rank = int(row.get("rank", 0))
        rows.append(
            f"""
            <tr>
              <td><span class="rank-badge">#{rank}</span></td>
              <td>
                <strong>{escape(_fmt(row.get("id")))}</strong>
                <span class="row-note">{escape(_fmt(row.get("hypothesis")))}</span>
              </td>
              <td>
                <div class="score-cell">
                  <span class="metric-value {_metric_class(score)}">{escape(_fmt(score))}</span>
                  <span class="score-track"><span style="width:{width}%"></span></span>
                </div>
              </td>
              <td><span class="metric-value {_metric_class(annual)}">{escape(_fmt(annual))}</span></td>
              <td><span class="metric-value {_metric_class(sharpe)}">{escape(_fmt(sharpe))}</span></td>
              <td><span class="metric-value {_metric_class(drawdown, invert=True)}">{escape(_fmt(drawdown))}</span></td>
              <td>{escape(_fmt(row.get("trade_count")))}</td>
              <td>{escape(_fmt(row.get("symbol_coverage")))}</td>
            </tr>
            """
        )
    return f"""
    <div class="table-wrap">
      <table class="leaderboard">
        <thead>
          <tr>
            <th>rank</th>
            <th>candidate</th>
            <th>score</th>
            <th>annual</th>
            <th>sharpe</th>
            <th>drawdown</th>
            <th>trades</th>
            <th>coverage</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _comparison_panel(best: dict[str, Any] | None, baseline: dict[str, Any] | None) -> str:
    if not best:
        return "<p class=\"empty\">暂无可比较结果。</p>"

    metrics = [
        ("score", "score", False),
        ("annual_return", "annual", False),
        ("sharpe", "sharpe", False),
        ("max_drawdown", "drawdown", True),
        ("trade_count", "trades", False),
    ]
    cards = []
    for key, label, invert in metrics:
        best_value = best.get(key)
        base_value = baseline.get(key) if baseline else None
        delta = None
        if base_value is not None and _num(best_value) is not None and _num(base_value) is not None:
            delta = _num(best_value) - _num(base_value)  # type: ignore[operator]
        cards.append(
            f"""
            <div class="compare-item">
              <span>{escape(label)}</span>
              <strong class="{_metric_class(best_value, invert=invert)}">{escape(_fmt(best_value))}</strong>
              <em class="{_metric_class(delta, invert=invert)}">{'baseline ' + escape(_fmt(base_value)) if baseline else 'no baseline'}{', delta ' + escape(_fmt(delta)) if delta is not None else ''}</em>
            </div>
            """
        )

    return f"""
    <div class="compare-layout">
      <div>
        <span class="eyebrow">best candidate</span>
        <h3>{escape(_fmt(best.get("id")))}</h3>
        <p>{escape(_fmt(best.get("hypothesis")))}</p>
      </div>
      <div class="compare-grid">{''.join(cards)}</div>
    </div>
    """


def _execution_timeline(execution_log: list[dict[str, Any]]) -> str:
    if not execution_log:
        return "<p class=\"empty\">暂无执行记录。</p>"
    max_duration = max((_num(item.get("duration_sec")) or 0.0 for item in execution_log), default=0.0)
    items = []
    for item in execution_log:
        duration = _num(item.get("duration_sec")) or 0.0
        width = 6 if max_duration <= 0 else max(6, min(100, int(duration / max_duration * 100)))
        status = _fmt(item.get("status"))
        status_class = "ok" if status == "ok" else "failed"
        items.append(
            f"""
            <li class="{status_class}">
              <div class="timeline-main">
                <strong>{escape(_fmt(item.get("step")))}</strong>
                <span>{escape(_fmt(item.get("detail", "")))}</span>
              </div>
              <div class="timeline-time">
                <span>{escape(_fmt(duration, digits=4))}s</span>
                <i><b style="width:{width}%"></b></i>
              </div>
            </li>
            """
        )
    return f"<ol class=\"timeline\">{''.join(items)}</ol>"


def _candidate_cards(candidates: list[Candidate], leaderboard: pd.DataFrame) -> str:
    cards = []
    for candidate in candidates:
        row = _row_by_id(leaderboard, candidate.id) or {}
        rank = row.get("rank", "-")
        position_text = json.dumps(candidate.position_data, ensure_ascii=False, indent=2)
        metric_items = [
            ("score", row.get("score")),
            ("annual", row.get("annual_return")),
            ("sharpe", row.get("sharpe")),
            ("drawdown", row.get("max_drawdown")),
            ("trades", row.get("trade_count")),
        ]
        metrics = "".join(
            f"<span><em>{escape(label)}</em><strong>{escape(_fmt(value))}</strong></span>"
            for label, value in metric_items
        )
        cards.append(
            f"""
            <article class="candidate-card">
              <div class="candidate-top">
                <div>
                  <span class="eyebrow">rank {escape(_fmt(rank))}</span>
                  <h3>{escape(candidate.id)}</h3>
                </div>
                <span class="candidate-status">validated</span>
              </div>
              <p>{escape(candidate.hypothesis)}</p>
              <div class="candidate-metrics">{metrics}</div>
              <details>
                <summary>Position JSON</summary>
                <pre>{escape(position_text)}</pre>
              </details>
            </article>
            """
        )
    return "\n".join(cards) if cards else "<p class=\"empty\">无候选。</p>"


def _artifact_links(run_dir: Path, artifacts: list[Path]) -> str:
    cards = []
    for path in artifacts:
        if path.exists():
            rel = path.relative_to(run_dir)
            suffix = path.suffix.lstrip(".") or "file"
            cards.append(
                f"""
                <a class="artifact" href="{escape(rel.as_posix())}">
                  <span>{escape(suffix)}</span>
                  <strong>{escape(rel.as_posix())}</strong>
                  <em>{path.stat().st_size:,} bytes</em>
                </a>
                """
            )
    return f"<div class=\"artifact-grid\">{''.join(cards)}</div>" if cards else "<p class=\"empty\">无额外产物。</p>"


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
    baseline = _row_by_id(leaderboard, "baseline")
    rejected_rows = [[item.get("id", "<unknown>"), item.get("reason", "")] for item in rejected]
    bars_rows = [[symbol, count] for symbol, count in bars_summary.items()]
    total_duration = sum(_num(item.get("duration_sec")) or 0.0 for item in execution_log)

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(config.task_name)} - auto-czsc-quant report</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #667085;
      --line: #d9dee7;
      --surface: #ffffff;
      --canvas: #f3f5f7;
      --teal: #0f766e;
      --teal-soft: #d9f3ef;
      --amber: #a16207;
      --amber-soft: #fef3c7;
      --rose: #be123c;
      --rose-soft: #ffe4e6;
      --charcoal: #202124;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: var(--canvas);
      letter-spacing: 0;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .topbar {{
      background: var(--charcoal);
      color: #fff;
      border-bottom: 4px solid var(--teal);
    }}
    .topbar-inner {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px 28px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
    }}
    .topbar h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
    .topbar p {{ margin: 8px 0 0; color: #cdd5df; }}
    .run-meta {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 10px;
      border: 1px solid rgba(255,255,255,.22);
      border-radius: 999px;
      color: #eef2f6;
      font-size: 12px;
      white-space: nowrap;
    }}
    .layout {{
      max-width: 1380px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr);
      gap: 28px;
      padding: 28px;
    }}
    .sidebar {{
      position: sticky;
      top: 18px;
      align-self: start;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }}
    .sidebar a {{
      display: block;
      padding: 10px 12px;
      border-radius: 6px;
      color: #475467;
      font-size: 14px;
    }}
    .sidebar a:hover {{ background: #eef8f6; color: var(--teal); }}
    main {{ min-width: 0; }}
    .report-section {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 18px;
      padding: 22px;
      overflow: hidden;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 16px;
    }}
    h2 {{ margin: 0; font-size: 20px; line-height: 1.25; }}
    h3 {{ margin: 0; font-size: 17px; line-height: 1.25; }}
    .section-note {{ color: var(--muted); font-size: 13px; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
    }}
    .kpi {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcfd;
    }}
    .kpi span, .compare-item span, .candidate-metrics em {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
      margin-bottom: 6px;
    }}
    .kpi strong {{
      display: block;
      font-size: 22px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }}
    .good {{ color: var(--teal); }}
    .bad {{ color: var(--rose); }}
    .neutral {{ color: var(--ink); }}
    .compare-layout {{
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 2fr;
      gap: 18px;
      align-items: start;
    }}
    .eyebrow {{
      display: inline-block;
      color: var(--teal);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 6px;
    }}
    .compare-layout p {{
      margin: 8px 0 0;
      color: #475467;
      line-height: 1.55;
    }}
    .compare-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
    }}
    .compare-item {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
      min-width: 0;
    }}
    .compare-item strong {{ display: block; font-size: 18px; margin-bottom: 4px; }}
    .compare-item em {{ color: var(--muted); font-size: 12px; font-style: normal; overflow-wrap: anywhere; }}
    .data-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, .75fr);
      gap: 18px;
      align-items: start;
    }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 720px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 11px 12px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; color: #344054; font-weight: 700; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover td {{ background: #fbfcfd; }}
    .leaderboard td:nth-child(2) {{ min-width: 260px; }}
    .row-note {{
      display: block;
      margin-top: 5px;
      color: var(--muted);
      line-height: 1.45;
      max-width: 520px;
    }}
    .rank-badge {{
      display: inline-flex;
      min-width: 34px;
      justify-content: center;
      border-radius: 999px;
      padding: 4px 8px;
      background: var(--teal-soft);
      color: var(--teal);
      font-weight: 700;
    }}
    .score-cell {{ min-width: 118px; }}
    .metric-value {{ font-weight: 700; }}
    .score-track {{
      display: block;
      height: 7px;
      margin-top: 7px;
      background: #e8edf2;
      border-radius: 999px;
      overflow: hidden;
    }}
    .score-track span {{ display: block; height: 100%; background: var(--teal); border-radius: inherit; }}
    .timeline {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}
    .timeline li {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 180px;
      gap: 16px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--teal);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }}
    .timeline li.failed {{ border-left-color: var(--rose); background: #fff8f8; }}
    .timeline-main strong {{ display: block; margin-bottom: 4px; }}
    .timeline-main span {{ color: var(--muted); overflow-wrap: anywhere; }}
    .timeline-time span {{ display: block; font-weight: 700; text-align: right; margin-bottom: 7px; }}
    .timeline-time i {{ display: block; height: 7px; background: #e8edf2; border-radius: 999px; overflow: hidden; }}
    .timeline-time b {{ display: block; height: 100%; background: var(--amber); border-radius: inherit; }}
    .candidate-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }}
    .candidate-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: #fff;
      min-width: 0;
    }}
    .candidate-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; }}
    .candidate-status {{
      border-radius: 999px;
      padding: 4px 9px;
      color: var(--teal);
      background: var(--teal-soft);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .candidate-card p {{ color: #475467; line-height: 1.55; margin: 12px 0; }}
    .candidate-metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0;
    }}
    .candidate-metrics span {{
      border: 1px solid #e8edf2;
      border-radius: 6px;
      padding: 8px;
      min-width: 0;
      background: #fbfcfd;
    }}
    .candidate-metrics strong {{ display: block; overflow-wrap: anywhere; }}
    details {{ margin-top: 8px; }}
    summary {{
      cursor: pointer;
      color: var(--teal);
      font-weight: 700;
      min-height: 32px;
      display: flex;
      align-items: center;
    }}
    pre {{
      overflow: auto;
      background: #15191f;
      color: #eef2f6;
      padding: 14px;
      border-radius: 8px;
      font-size: 12px;
      line-height: 1.55;
    }}
    .artifact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
    }}
    .artifact {{
      display: grid;
      gap: 5px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
      min-width: 0;
    }}
    .artifact:hover {{ border-color: var(--teal); background: #fbfffe; }}
    .artifact span {{
      justify-self: start;
      border-radius: 999px;
      padding: 3px 8px;
      background: var(--amber-soft);
      color: var(--amber);
      font-size: 12px;
      font-weight: 700;
    }}
    .artifact strong {{ overflow-wrap: anywhere; }}
    .artifact em {{ color: var(--muted); font-size: 12px; font-style: normal; }}
    .empty {{ color: var(--muted); margin: 0; }}
    @media (max-width: 1040px) {{
      .layout {{ grid-template-columns: 1fr; padding: 20px; }}
      .sidebar {{ position: static; display: flex; flex-wrap: wrap; gap: 6px; }}
      .sidebar a {{ padding: 8px 10px; }}
      .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .compare-layout, .data-grid {{ grid-template-columns: 1fr; }}
      .compare-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    @media (max-width: 680px) {{
      .topbar-inner {{ grid-template-columns: 1fr; padding: 20px; }}
      .run-meta {{ justify-content: flex-start; }}
      .kpi-grid, .compare-grid, .candidate-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .timeline li {{ grid-template-columns: 1fr; }}
      .timeline-time span {{ text-align: left; }}
      .report-section {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <div>
        <h1>{escape(config.task_name)}</h1>
        <p>auto-czsc-quant 优化结果与执行记录</p>
      </div>
      <div class="run-meta">
        <span class="pill">{escape(config.data_source)}</span>
        <span class="pill">{escape(config.candidate_mode)}</span>
        <span class="pill">{escape(config.base_freq)}</span>
        <span class="pill">{escape(config.sdt)} / {escape(config.edt)}</span>
      </div>
    </div>
  </header>

  <div class="layout">
    <nav class="sidebar" aria-label="report sections">
      <a href="#overview">结果概览</a>
      <a href="#comparison">最佳对比</a>
      <a href="#execution">执行记录</a>
      <a href="#leaderboard">Leaderboard</a>
      <a href="#candidates">候选详情</a>
      <a href="#artifacts">产物索引</a>
    </nav>

    <main>
      <section class="report-section" id="overview">
        <div class="section-head">
          <h2>结果概览</h2>
          <span class="section-note">run directory: {escape(run_dir.name)}</span>
        </div>
        <div class="kpi-grid">
          <div class="kpi"><span>候选总数</span><strong>{raw_candidate_count}</strong></div>
          <div class="kpi"><span>通过校验</span><strong class="good">{len(candidates)}</strong></div>
          <div class="kpi"><span>拒绝 / 失败</span><strong class="{_metric_class(-len(rejected)) if rejected else 'neutral'}">{len(rejected)}</strong></div>
          <div class="kpi"><span>最佳候选</span><strong>{escape(_fmt(best.get("id") if best else "-"))}</strong></div>
          <div class="kpi"><span>最佳 score</span><strong class="{_metric_class(best.get("score") if best else None)}">{escape(_fmt(best.get("score") if best else "-"))}</strong></div>
          <div class="kpi"><span>总耗时</span><strong>{escape(_fmt(total_duration, digits=4))}s</strong></div>
        </div>
      </section>

      <section class="report-section" id="comparison">
        <div class="section-head">
          <h2>最佳对比</h2>
          <span class="section-note">best candidate vs baseline</span>
        </div>
        {_comparison_panel(best, baseline)}
      </section>

      <section class="report-section" id="config">
        <div class="section-head">
          <h2>配置与数据</h2>
          <span class="section-note">输入范围和行情加载结果</span>
        </div>
        <div class="data-grid">
          {_table(["key", "value"], config_rows)}
          {_table(["symbol", "bar_count"], bars_rows)}
        </div>
      </section>

      <section class="report-section" id="execution">
        <div class="section-head">
          <h2>执行记录</h2>
          <span class="section-note">每个阶段的状态、耗时和关键明细</span>
        </div>
        {_execution_timeline(execution_log)}
      </section>

      <section class="report-section" id="leaderboard">
        <div class="section-head">
          <h2>Leaderboard</h2>
          <span class="section-note">按综合 score 降序排列</span>
        </div>
        {_leaderboard_table(leaderboard)}
      </section>

      <section class="report-section" id="candidates">
        <div class="section-head">
          <h2>候选详情</h2>
          <span class="section-note">hypothesis、指标和 Position JSON</span>
        </div>
        <div class="candidate-list">
          {_candidate_cards(candidates, leaderboard)}
        </div>
      </section>

      <section class="report-section" id="rejected">
        <div class="section-head">
          <h2>拒绝与失败</h2>
          <span class="section-note">未进入 leaderboard 的候选原因</span>
        </div>
        {_table(["id", "reason"], rejected_rows)}
      </section>

      <section class="report-section" id="artifacts">
        <div class="section-head">
          <h2>产物索引</h2>
          <span class="section-note">本次 run 生成的可复盘文件</span>
        </div>
        {_artifact_links(run_dir, artifacts)}
      </section>
    </main>
  </div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
