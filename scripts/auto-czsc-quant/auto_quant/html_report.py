"""Self-contained HTML report rendering for experiment results."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.schema import AutoQuantConfig, Candidate

# --- formatting helpers -----------------------------------------------------


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    """Render a ratio as a percentage with one decimal (e.g. 0.4375 -> 43.75%)."""
    number = _num(value)
    if number is None:
        return ""
    return f"{number * 100:.2f}%"


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
        return f'<p class="empty">{escape(empty)}</p>'
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


def _parse_stats(row: dict[str, Any]) -> dict[str, Any]:
    """Decode the JSON ``stats`` column (may be missing / invalid)."""
    raw = row.get("stats")
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _score_width(score: Any, min_score: float, max_score: float) -> int:
    value = _num(score)
    if value is None:
        return 0
    if abs(max_score - min_score) < 1e-12:
        return 100
    return max(4, min(100, int((value - min_score) / (max_score - min_score) * 100)))


# --- section renderers ------------------------------------------------------


# High-signal stats surfaced from the portfolio stats blob. ``invert`` means a
# smaller number is better (e.g. drawdown, volatility).
_STAT_FIELDS: list[tuple[str, str]] = [
    ("夏普比率", "夏普"),
    ("卡玛比率", "卡玛"),
    ("最大回撤", "回撤"),
    ("年化波动率", "年化波动"),
    ("下行波动率", "下行波动"),
    ("年化收益", "年化"),
    ("交易胜率", "交易胜率"),
    ("日胜率", "日胜"),
    ("周胜率", "周胜"),
    ("月胜率", "月胜"),
    ("季胜率", "季胜"),
    ("年胜率", "年胜"),
    ("单笔盈亏比", "盈亏比"),
    ("单笔收益", "单笔(BP)"),
    ("绝对收益", "绝对"),
    ("新高占比", "新高占比"),
    ("年化交易次数", "年化换手"),
    ("多头占比", "多头占比"),
    ("空头占比", "空头占比"),
]

# Stats where a lower value reads as better (used for color coding).
_INVERTED_STATS = {"最大回撤", "年化波动率", "下行波动率", "新高间隔"}


def _leaderboard_table(leaderboard: pd.DataFrame) -> str:
    if leaderboard.empty:
        return '<p class="empty">没有候选通过评分。</p>'

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
        stats = _parse_stats(row.to_dict())
        calmar = stats.get("卡玛比率")
        win_rate = stats.get("交易胜率")
        rows.append(
            f"""
            <tr>
              <td><span class="rank-badge rank-{min(rank, 3)}">#{rank}</span></td>
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
              <td><span class="metric-value {_metric_class(annual)}">{escape(_pct(annual))}</span></td>
              <td><span class="metric-value {_metric_class(sharpe)}">{escape(_fmt(sharpe))}</span></td>
              <td><span class="metric-value {_metric_class(calmar)}">{escape(_fmt(calmar))}</span></td>
              <td><span class="metric-value {_metric_class(drawdown, invert=True)}">{escape(_pct(drawdown))}</span></td>
              <td><span class="metric-value neutral">{escape(_pct(win_rate))}</span></td>
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
            <th>年化</th>
            <th>夏普</th>
            <th>卡玛</th>
            <th>回撤</th>
            <th>胜率</th>
            <th>trades</th>
            <th>coverage</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """


def _comparison_panel(best: dict[str, Any] | None, baseline: dict[str, Any] | None) -> str:
    if not best:
        return '<p class="empty">暂无可比较结果。</p>'

    metrics = [
        ("score", "score", False),
        ("annual_return", "年化收益", False),
        ("sharpe", "夏普", False),
        ("max_drawdown", "回撤", True),
        ("trade_count", "交易次数", False),
    ]
    best_stats = _parse_stats(best)
    base_stats = _parse_stats(baseline) if baseline else {}

    cards = []
    for key, label, invert in metrics:
        best_value = best.get(key)
        base_value = baseline.get(key) if baseline else None
        delta = None
        delta_better = None
        if base_value is not None and _num(best_value) is not None and _num(base_value) is not None:
            delta = _num(best_value) - _num(base_value)  # type: ignore[operator]
            delta_better = (delta > 0) if not invert else (delta < 0)
        delta_cls = ""
        delta_arrow = ""
        if delta is not None and abs(delta) > 1e-12:
            delta_cls = "good" if delta_better else "bad"
            delta_arrow = "▲" if delta > 0 else "▼"
        base_label = f"基线 {escape(_fmt(base_value))}" if baseline else "无基线"
        delta_label = (
            f'<span class="delta {delta_cls}">{delta_arrow} {escape(_fmt(abs(delta)))}</span>'
            if delta is not None
            else ""
        )
        cards.append(
            f"""
            <div class="compare-item">
              <span>{escape(label)}</span>
              <strong class="{_metric_class(best_value, invert=invert)}">{escape(_fmt(best_value))}</strong>
              <em>{base_label} {delta_label}</em>
            </div>
            """
        )

    # Best vs baseline on a few derived stats too.
    extra_rows = []
    for stat_key, label in [("卡玛比率", "卡玛比率"), ("年化波动率", "年化波动率"), ("交易胜率", "交易胜率")]:
        best_s = best_stats.get(stat_key)
        base_s = base_stats.get(stat_key) if base_stats else None
        delta_s = None
        if base_s is not None and _num(best_s) is not None and _num(base_s) is not None:
            delta_s = _num(best_s) - _num(base_s)  # type: ignore[operator]
        extra_rows.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{escape(_fmt(best_s))}</td>"
            f"<td>{escape(_fmt(base_s))}</td>"
            f'<td class="{_metric_class(delta_s)}">{escape(_fmt(delta_s))}</td>'
            "</tr>"
        )
    extra_table = (
        '<div class="compare-extra"><h4>补充统计对比</h4>'
        '<table class="mini"><thead><tr><th>指标</th><th>best</th><th>baseline</th><th>delta</th></tr></thead>'
        f"<tbody>{''.join(extra_rows)}</tbody></table></div>"
    )

    return f"""
    <div class="compare-layout">
      <div>
        <span class="eyebrow">best candidate</span>
        <h3>{escape(_fmt(best.get("id")))}</h3>
        <p>{escape(_fmt(best.get("hypothesis")))}</p>
        {extra_table}
      </div>
      <div class="compare-grid">{"".join(cards)}</div>
    </div>
    """


def _execution_timeline(execution_log: list[dict[str, Any]]) -> str:
    if not execution_log:
        return '<p class="empty">暂无执行记录。</p>'
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
              <span class="timeline-dot"></span>
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
    return f'<ol class="timeline">{"".join(items)}</ol>'


def _candidate_cards(candidates: list[Candidate], leaderboard: pd.DataFrame) -> str:
    cards = []
    for candidate in candidates:
        row = _row_by_id(leaderboard, candidate.id) or {}
        rank = row.get("rank", "-")
        position_text = json.dumps(candidate.position_data, ensure_ascii=False, indent=2)
        stats = _parse_stats(row)
        # Top-line metrics row.
        metric_items = [
            ("score", row.get("score")),
            ("年化", row.get("annual_return")),
            ("夏普", row.get("sharpe")),
            ("卡玛", stats.get("卡玛比率")),
            ("回撤", row.get("max_drawdown")),
            ("胜率", stats.get("交易胜率")),
        ]
        is_inverted = {"回撤"}
        metrics = "".join(
            f"<span><em>{escape(label)}</em>"
            f'<strong class="{_metric_class(value, invert=label in is_inverted)}">'
            f"{escape(_pct(value) if label in {'年化', '回撤', '胜率'} else _fmt(value))}"
            "</strong></span>"
            for label, value in metric_items
        )
        # Full stats grid (everything the backtest actually computed).
        stat_cells = []
        for stat_key, label in _STAT_FIELDS:
            value = stats.get(stat_key)
            if value is None or value == "":
                continue
            display = _pct(value) if "胜率" in stat_key or "占比" in stat_key or "新高占比" in stat_key else _fmt(value)
            stat_cells.append(
                f'<div class="stat-cell {_metric_class(value, invert=stat_key in _INVERTED_STATS)}">'
                f"<span>{escape(label)}</span><strong>{escape(display)}</strong></div>"
            )
        stats_grid = f'<div class="stats-grid">{"".join(stat_cells)}</div>' if stat_cells else ""
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
              {stats_grid}
              <details>
                <summary>Position JSON</summary>
                <pre>{escape(position_text)}</pre>
              </details>
            </article>
            """
        )
    return "\n".join(cards) if cards else '<p class="empty">无候选。</p>'


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
    return f'<div class="artifact-grid">{"".join(cards)}</div>' if cards else '<p class="empty">无额外产物。</p>'


# --- main entry -------------------------------------------------------------


def _top_k_curve_block(top_k_curves: list[dict[str, Any]]) -> str:
    """Render a self-contained inline-SVG cumulative-return comparison for top-k.

    参考 wbt.plot_cumulative_returns：日收益累加得到累计收益曲线，多策略叠加对比。
    完全内联 SVG，不依赖任何外部 JS，离线可看。
    """
    if not top_k_curves:
        return '<p class="empty">没有可对比的收益曲线（候选未产生成交）。</p>'

    palette = ["#0d9488", "#2563eb", "#b45309", "#7c3aed", "#db2777", "#0891b2", "#ca8a04", "#475569"]

    # 收集所有日期，计算每条曲线累计收益（%）。
    all_dates: list[str] = []
    seen: set[str] = set()
    series: list[dict[str, Any]] = []
    for item in top_k_curves:
        idx_map: dict[str, float] = {p["date"]: float(p["return"]) for p in item["curve"]}
        for d in idx_map:
            if d not in seen:
                seen.add(d)
                all_dates.append(d)
        series.append({"id": item["id"], "rank": item.get("rank", 0), "idx": idx_map})
    all_dates.sort()

    cum_series: list[list[float]] = []
    for s in series:
        cum = 0.0
        ys = []
        for d in all_dates:
            cum += s["idx"].get(d, 0.0)
            ys.append(cum * 100.0)
        cum_series.append(ys)

    if not all_dates:
        return '<p class="empty">收益曲线无有效日期。</p>'

    width, height = 980, 360
    pad_l, pad_r, pad_t, pad_b = 56, 16, 16, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    y_min = min((min(ys) for ys in cum_series), default=0.0)
    y_max = max((max(ys) for ys in cum_series), default=0.0)
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0
    y_min = min(y_min, 0.0)
    y_max = max(y_max, 0.0)

    n = len(all_dates)

    def xpx(i: int) -> float:
        return pad_l + (0.0 if n == 1 else i / (n - 1) * plot_w)

    def ypx(v: float) -> float:
        return pad_t + plot_h - (v - y_min) / (y_max - y_min) * plot_h

    def path_for(ys: list[float]) -> str:
        return " ".join(f"{xpx(i):.1f},{ypx(v):.1f}" for i, v in enumerate(ys))

    # y 轴网格与刻度（5 档）。
    grid = []
    for k in range(5):
        frac = k / 4
        val = y_min + frac * (y_max - y_min)
        y = ypx(val)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
            f'stroke="#eef2f7" stroke-width="1"/>'
            f'<text x="{pad_l - 8}" y="{y + 3:.1f}" text-anchor="end" '
            f'font-size="10" fill="#94a3b8">{val:.1f}%</text>'
        )
    # 零线加粗。
    if y_min < 0 < y_max:
        yz = ypx(0.0)
        grid.append(
            f'<line x1="{pad_l}" y1="{yz:.1f}" x2="{width - pad_r}" y2="{yz:.1f}" stroke="#cbd5e1" stroke-width="1.2"/>'
        )
    # x 轴刻度（首/中/尾日期）。
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        i = int(round(frac * (n - 1)))
        x = xpx(i)
        grid.append(
            f'<text x="{x:.1f}" y="{height - pad_b + 18}" text-anchor="middle" '
            f'font-size="10" fill="#94a3b8">{all_dates[i]}</text>'
        )

    polylines = []
    legend_items = []
    for s, ys, color in zip(series, cum_series, palette, strict=False):
        rank = s["rank"]
        sid = s["id"]
        pid = f"curve-{escape(str(rank))}-{escape(sid)}"
        polylines.append(
            f'<polyline id="{pid}" fill="none" stroke="{color}" stroke-width="2" points="{path_for(ys)}"/>'
        )
        legend_items.append(
            f'<span class="legend-chip" data-target="{pid}" style="--c:{color}">'
            f'<i style="background:{color}"></i>#{rank} {escape(sid)}</span>'
        )

    return f"""
    <div class="curve-panel">
      <svg viewBox="0 0 {width} {height}" class="curve-svg" preserveAspectRatio="xMidYMid meet" role="img"
           aria-label="top-k 累计收益对比">
        {"".join(grid)}
        {"".join(polylines)}
      </svg>
      <div class="curve-legend">{"".join(legend_items)}</div>
      <p class="curve-hint">日收益累加为累计收益（%）；点击图例可切换显示。</p>
    </div>
    <script>
    document.querySelectorAll('.curve-legend .legend-chip').forEach(function (chip) {{
      chip.addEventListener('click', function () {{
        var el = document.getElementById(chip.getAttribute('data-target'));
        if (el) {{
          var off = el.style.opacity === '0.15';
          el.style.opacity = off ? '1' : '0.15';
          chip.classList.toggle('off', !off);
        }}
      }});
    }});
    </script>
    """


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
    top_k_curves: list[dict[str, Any]] | None = None,
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
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --line-soft: #eef2f7;
      --surface: #ffffff;
      --canvas: #f1f5f9;
      --teal: #0d9488;
      --teal-strong: #0f766e;
      --teal-soft: #ccfbf1;
      --amber: #b45309;
      --amber-soft: #fef3c7;
      --rose: #e11d48;
      --rose-soft: #ffe4e6;
      --charcoal: #0b1220;
      --slate: #1e293b;
      --gold: #ca8a04;
      --silver: #64748b;
      --bronze: #b45309;
      --code-bg: #0b1220;
      --shadow: 0 1px 2px rgba(15,23,42,.04), 0 4px 12px rgba(15,23,42,.04);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: var(--canvas);
      -webkit-font-smoothing: antialiased;
      line-height: 1.5;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .topbar {{
      background: linear-gradient(135deg, var(--charcoal) 0%, var(--slate) 100%);
      color: #fff;
      position: relative;
      overflow: hidden;
    }}
    .topbar::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(800px 200px at 80% -40%, rgba(13,148,136,.35), transparent 70%);
      pointer-events: none;
    }}
    .topbar-inner {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 28px 28px 26px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
      position: relative;
    }}
    .topbar h1 {{ margin: 0; font-size: 30px; line-height: 1.15; letter-spacing: -.01em; }}
    .topbar .subtitle {{ margin: 10px 0 0; color: #94a3b8; font-size: 14px; }}
    .run-meta {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 30px;
      padding: 6px 12px;
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 999px;
      color: #e2e8f0;
      font-size: 12.5px;
      white-space: nowrap;
      background: rgba(255,255,255,.04);
    }}
    .pill::before {{
      content: "";
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--teal);
    }}
    .layout {{
      max-width: 1380px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: 28px;
      padding: 28px;
    }}
    .sidebar {{
      position: sticky;
      top: 18px;
      align-self: start;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      box-shadow: var(--shadow);
    }}
    .sidebar a {{
      display: block;
      padding: 9px 12px;
      border-radius: 8px;
      color: #475569;
      font-size: 13.5px;
      font-weight: 500;
      transition: background .12s, color .12s;
    }}
    .sidebar a:hover {{ background: #f0fdfa; color: var(--teal-strong); }}
    main {{ min-width: 0; }}
    .report-section {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 12px;
      margin-bottom: 18px;
      padding: 24px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line-soft);
    }}
    h2 {{ margin: 0; font-size: 19px; line-height: 1.25; letter-spacing: -.01em; }}
    h3 {{ margin: 0; font-size: 17px; line-height: 1.25; }}
    h4 {{ margin: 0 0 10px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }}
    .section-note {{ color: var(--muted); font-size: 12.5px; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
    }}
    .kpi {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    }}
    .kpi span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .kpi strong {{
      display: block;
      font-size: 22px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }}
    .good {{ color: var(--teal-strong); }}
    .bad {{ color: var(--rose); }}
    .neutral {{ color: var(--ink); }}
    .compare-layout {{
      display: grid;
      grid-template-columns: minmax(240px, 1fr) 2fr;
      gap: 20px;
      align-items: start;
    }}
    .eyebrow {{
      display: inline-block;
      color: var(--teal-strong);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-bottom: 6px;
    }}
    .compare-layout p {{ margin: 8px 0 0; color: #475569; line-height: 1.55; }}
    .compare-extra {{ margin-top: 16px; }}
    .compare-extra .mini {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
    .compare-extra .mini th, .compare-extra .mini td {{ text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line-soft); }}
    .compare-extra .mini th {{ color: var(--muted); font-weight: 600; }}
    .compare-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
    }}
    .compare-item {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      background: #fff;
      min-width: 0;
    }}
    .compare-item span {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
    .compare-item strong {{ display: block; font-size: 19px; margin-bottom: 6px; }}
    .compare-item em {{ color: var(--muted); font-size: 11.5px; font-style: normal; overflow-wrap: anywhere; }}
    .delta {{ font-weight: 700; }}
    .delta.good {{ color: var(--teal-strong); }}
    .delta.bad {{ color: var(--rose); }}
    .data-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, .75fr);
      gap: 18px;
      align-items: start;
    }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 720px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 11px 12px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; color: #334155; font-weight: 700; position: sticky; top: 0; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover td {{ background: #fbfdff; }}
    .leaderboard td:nth-child(2) {{ min-width: 260px; }}
    .row-note {{
      display: block;
      margin-top: 5px;
      color: var(--muted);
      line-height: 1.45;
      max-width: 520px;
      font-size: 12px;
    }}
    .rank-badge {{
      display: inline-flex;
      min-width: 34px;
      justify-content: center;
      border-radius: 999px;
      padding: 4px 9px;
      font-weight: 700;
      font-size: 12px;
    }}
    .rank-1 {{ background: #fef3c7; color: var(--gold); }}
    .rank-2 {{ background: #eef2f7; color: var(--silver); }}
    .rank-3 {{ background: #fde4cf; color: var(--bronze); }}
    .score-cell {{ min-width: 118px; }}
    .metric-value {{ font-weight: 700; }}
    .score-track {{
      display: block;
      height: 6px;
      margin-top: 7px;
      background: #e8edf2;
      border-radius: 999px;
      overflow: hidden;
    }}
    .score-track span {{ display: block; height: 100%; background: linear-gradient(90deg, var(--teal), var(--teal-strong)); border-radius: inherit; }}
    .timeline {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 8px;
    }}
    .timeline li {{
      display: grid;
      grid-template-columns: 14px minmax(0, 1fr) 180px;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px 14px;
      background: #fff;
      align-items: center;
    }}
    .timeline-dot {{
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--teal);
      box-shadow: 0 0 0 3px var(--teal-soft);
      margin-top: 4px;
    }}
    .timeline li.failed {{ background: #fff8f8; border-color: #fecdd3; }}
    .timeline li.failed .timeline-dot {{ background: var(--rose); box-shadow: 0 0 0 3px var(--rose-soft); }}
    .timeline-main strong {{ display: block; margin-bottom: 3px; }}
    .timeline-main span {{ color: var(--muted); overflow-wrap: anywhere; font-size: 12.5px; }}
    .timeline-time span {{ display: block; font-weight: 700; text-align: right; margin-bottom: 7px; font-size: 13px; }}
    .timeline-time i {{ display: block; height: 6px; background: #e8edf2; border-radius: 999px; overflow: hidden; }}
    .timeline-time b {{ display: block; height: 100%; background: var(--amber); border-radius: inherit; }}
    .candidate-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px; }}
    .candidate-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 18px;
      background: #fff;
      min-width: 0;
      box-shadow: var(--shadow);
    }}
    .candidate-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; }}
    .candidate-status {{
      border-radius: 999px;
      padding: 4px 10px;
      color: var(--teal-strong);
      background: var(--teal-soft);
      font-size: 11.5px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .candidate-card p {{ color: #475569; line-height: 1.55; margin: 10px 0 12px; font-size: 13px; }}
    .candidate-metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }}
    .candidate-metrics span {{
      border: 1px solid var(--line-soft);
      border-radius: 8px;
      padding: 8px;
      min-width: 0;
      background: #f8fafc;
    }}
    .candidate-metrics em {{ display: block; color: var(--muted); font-size: 10.5px; font-style: normal; margin-bottom: 3px; }}
    .candidate-metrics strong {{ display: block; font-size: 13px; overflow-wrap: anywhere; }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
      gap: 6px;
      margin-bottom: 12px;
    }}
    .stat-cell {{
      border: 1px solid var(--line-soft);
      border-radius: 6px;
      padding: 6px 8px;
      background: #fcfdfe;
      min-width: 0;
    }}
    .stat-cell span {{ display: block; color: var(--muted); font-size: 10px; margin-bottom: 2px; }}
    .stat-cell strong {{ display: block; font-size: 12.5px; font-weight: 600; overflow-wrap: anywhere; }}
    details {{ margin-top: 8px; }}
    summary {{
      cursor: pointer;
      color: var(--teal-strong);
      font-weight: 700;
      font-size: 13px;
      min-height: 32px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    summary::before {{ content: "▸"; transition: transform .12s; }}
    details[open] summary::before {{ transform: rotate(90deg); }}
    pre {{
      overflow: auto;
      background: var(--code-bg);
      color: #e2e8f0;
      padding: 14px;
      border-radius: 8px;
      font-size: 12px;
      line-height: 1.55;
      font-family: "SFMono-Regular", "JetBrains Mono", Consolas, monospace;
      max-height: 420px;
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
      border-radius: 10px;
      padding: 12px;
      background: #fff;
      min-width: 0;
      transition: border-color .12s, background .12s, transform .12s;
    }}
    .artifact:hover {{ border-color: var(--teal); background: #fcfffe; transform: translateY(-1px); }}
    .artifact span {{
      justify-self: start;
      border-radius: 999px;
      padding: 3px 9px;
      background: var(--amber-soft);
      color: var(--amber);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .artifact strong {{ overflow-wrap: anywhere; font-size: 13px; }}
    .artifact em {{ color: var(--muted); font-size: 11.5px; font-style: normal; }}
    .empty {{ color: var(--muted); margin: 0; }}
    .curve-panel {{ border: 1px solid var(--line); border-radius: 10px; padding: 14px; background: #fbfdff; }}
    .curve-svg {{ width: 100%; height: auto; display: block; }}
    .curve-legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 6px; }}
    .legend-chip {{
      display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
      border: 1px solid var(--line); border-radius: 999px; padding: 5px 11px;
      font-size: 12.5px; background: #fff; user-select: none; transition: opacity .12s;
    }}
    .legend-chip i {{ width: 12px; height: 12px; border-radius: 3px; background: var(--c, var(--teal)); }}
    .legend-chip.off {{ opacity: .4; }}
    .curve-hint {{ color: var(--muted); font-size: 12px; margin: 6px 0 0; }}
    @media (max-width: 1040px) {{
      .layout {{ grid-template-columns: 1fr; padding: 20px; }}
      .sidebar {{ position: static; display: flex; flex-wrap: wrap; gap: 4px; }}
      .sidebar a {{ padding: 8px 11px; }}
      .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .compare-layout, .data-grid {{ grid-template-columns: 1fr; }}
      .compare-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    @media (max-width: 680px) {{
      .topbar-inner {{ grid-template-columns: 1fr; padding: 20px; }}
      .run-meta {{ justify-content: flex-start; }}
      .kpi-grid, .compare-grid, .candidate-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .timeline li {{ grid-template-columns: 14px 1fr; }}
      .timeline-time {{ grid-column: 2; }}
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
        <p class="subtitle">auto-czsc-quant · 策略优化结果与执行记录</p>
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
      <a href="#curves">收益曲线对比</a>
      <a href="#comparison">最佳对比</a>
      <a href="#config">配置与数据</a>
      <a href="#execution">执行记录</a>
      <a href="#leaderboard">Leaderboard</a>
      <a href="#candidates">候选详情</a>
      <a href="#rejected">拒绝与失败</a>
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
          <div class="kpi"><span>拒绝 / 失败</span><strong class="{_metric_class(-len(rejected)) if rejected else "neutral"}">{len(rejected)}</strong></div>
          <div class="kpi"><span>最佳候选</span><strong>{escape(_fmt(best.get("id") if best else "-"))}</strong></div>
          <div class="kpi"><span>最佳 score</span><strong class="{_metric_class(best.get("score") if best else None)}">{escape(_fmt(best.get("score") if best else "-"))}</strong></div>
          <div class="kpi"><span>总耗时</span><strong>{escape(_fmt(total_duration, digits=4))}s</strong></div>
        </div>
      </section>

      <section class="report-section" id="curves">
        <div class="section-head">
          <h2>Top-K 策略收益曲线对比</h2>
          <span class="section-note">参考 wbt 累计收益叠加图</span>
        </div>
        {_top_k_curve_block(top_k_curves or [])}
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
          <span class="section-note">hypothesis、完整统计指标与 Position JSON</span>
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
