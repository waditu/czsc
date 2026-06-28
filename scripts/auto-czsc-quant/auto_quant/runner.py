"""Experiment orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from auto_quant.backtest import backtest_position
from auto_quant.data import load_bars
from auto_quant.html_report import write_html_report
from auto_quant.journal import write_journal
from auto_quant.llm import generate_llm_candidates
from auto_quant.schema import AutoQuantConfig, Candidate, dump_json, read_jsonl
from auto_quant.scorer import score_portfolio
from auto_quant.validate import load_valid_candidates


@dataclass(frozen=True)
class RunResult:
    run_dir: Path
    leaderboard_path: Path
    report_path: Path
    accepted_count: int
    rejected_count: int


def _new_run_dir(config: AutoQuantConfig) -> Path:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / config.task_name / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "best_positions").mkdir()
    return run_dir


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


def _candidate_rows(candidates: list[Candidate]) -> list[dict[str, Any]]:
    return [{"id": c.id, "hypothesis": c.hypothesis, "position": c.position_data} for c in candidates]


def _record_step(
    execution_log: list[dict[str, Any]],
    step: str,
    status: str,
    started_at: float,
    detail: str = "",
) -> None:
    execution_log.append(
        {
            "step": step,
            "status": status,
            "duration_sec": round(perf_counter() - started_at, 4),
            "detail": detail,
        }
    )


def _load_candidate_rows(
    config: AutoQuantConfig,
    run_dir: Path,
    execution_log: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    started_at = perf_counter()
    rows: list[dict[str, Any]] = []
    if config.include_baseline:
        if not config.baseline_position_path:
            raise ValueError("include_baseline=true 时必须配置 baseline_position_path")
        baseline = json.loads(config.baseline_position_path.read_text(encoding="utf-8"))
        rows.append({"id": "baseline", "hypothesis": "基准 Position 配置", "position": baseline})

    if config.candidate_mode == "file":
        if not config.candidates_path:
            raise ValueError("candidate_mode=file 时必须配置 candidates_path")
        rows.extend(read_jsonl(config.candidates_path))
        _record_step(execution_log, "load_candidates", "ok", started_at, f"file rows={len(rows)}")
        return rows

    if config.candidate_mode == "llm":
        llm_rows, raw = generate_llm_candidates(config)
        (run_dir / "llm_raw.txt").write_text(raw, encoding="utf-8")
        _write_jsonl(run_dir / "llm_candidates.jsonl", llm_rows)
        rows.extend(llm_rows)
        _record_step(execution_log, "load_candidates", "ok", started_at, f"llm rows={len(rows)}")
        return rows

    raise ValueError(f"未知 candidate_mode: {config.candidate_mode}（支持 file/llm）")


def _load_baseline_position(config: AutoQuantConfig) -> dict[str, Any] | None:
    if not config.baseline_position_path:
        return None
    return json.loads(config.baseline_position_path.read_text(encoding="utf-8"))


def run_experiment(config: AutoQuantConfig) -> RunResult:
    """Run validation, mock backtests, scoring, and artifact writing."""
    execution_log: list[dict[str, Any]] = []
    started_at = perf_counter()
    run_dir = _new_run_dir(config)
    dump_json(run_dir / "config.json", config.to_dict())
    _record_step(execution_log, "init_run_dir", "ok", started_at, str(run_dir))

    raw_candidates = _load_candidate_rows(config, run_dir, execution_log)
    baseline_position = _load_baseline_position(config)
    started_at = perf_counter()
    candidates, rejected = load_valid_candidates(
        raw_candidates,
        max_candidates=config.max_candidates,
        baseline_position=baseline_position,
    )
    _write_jsonl(run_dir / "accepted.jsonl", _candidate_rows(candidates))
    _record_step(
        execution_log,
        "validate_candidates",
        "ok",
        started_at,
        f"accepted={len(candidates)} rejected={len(rejected)}",
    )

    started_at = perf_counter()
    bars_by_symbol = load_bars(config)
    bars_summary = {symbol: len(bars) for symbol, bars in bars_by_symbol.items()}
    _record_step(execution_log, "load_bars", "ok", started_at, json.dumps(bars_summary, ensure_ascii=False))

    rows: list[dict[str, Any]] = []
    curves_dir = run_dir / "curves"
    curves_dir.mkdir(exist_ok=True)
    curves_by_id: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        started_at = perf_counter()
        try:
            symbol_results, portfolio_stats, portfolio_weights, daily_return = backtest_position(
                candidate.position,
                bars_by_symbol,
                fee_rate=config.fee_rate,
                yearly_days=config.yearly_days,
            )
            score_row = score_portfolio(portfolio_stats, symbol_results, portfolio_weights)
            rows.append(
                {
                    "id": candidate.id,
                    "hypothesis": candidate.hypothesis,
                    **score_row,
                    "stats": json.dumps(portfolio_stats, ensure_ascii=False, default=str),
                }
            )
            # 曲线序列化失败不应让整个候选被拒（曲线仅用于报告可视化）。
            try:
                curve_records = [
                    {"date": d.strftime("%Y-%m-%d"), "return": float(r)}
                    for d, r in zip(daily_return["date"], daily_return["return"], strict=True)
                ]
                curves_by_id[candidate.id] = curve_records
                dump_json(curves_dir / f"{candidate.id}.json", curve_records)
            except Exception as curve_exc:  # noqa: BLE001
                _record_step(execution_log, f"curve:{candidate.id}", "failed", started_at, str(curve_exc))
            _record_step(execution_log, f"score:{candidate.id}", "ok", started_at, f"weights={len(portfolio_weights)}")
        except Exception as exc:  # noqa: BLE001 - experiment runners must record candidate failures.
            rejected.append({"id": candidate.id, "reason": f"backtest failed: {exc}"})
            _record_step(execution_log, f"score:{candidate.id}", "failed", started_at, str(exc))

    started_at = perf_counter()
    leaderboard = pd.DataFrame(rows)
    if not leaderboard.empty:
        leaderboard = leaderboard.sort_values("score", ascending=False).reset_index(drop=True)
        leaderboard.insert(0, "rank", range(1, len(leaderboard) + 1))
        best_ids = set(leaderboard.head(config.top_k)["id"].tolist())
        for candidate in candidates:
            if candidate.id in best_ids:
                dump_json(run_dir / "best_positions" / f"{candidate.id}.json", candidate.position_data)

    leaderboard_path = run_dir / "leaderboard.csv"
    leaderboard.to_csv(leaderboard_path, index=False)
    _write_jsonl(run_dir / "rejected.jsonl", rejected)
    write_journal(run_dir / "journal.md", config=config, leaderboard=leaderboard, rejected=rejected)
    _record_step(execution_log, "write_core_artifacts", "ok", started_at, "leaderboard/journal/jsonl")

    started_at = perf_counter()
    report_path = run_dir / "report.html"
    artifacts = [
        run_dir / "config.json",
        run_dir / "accepted.jsonl",
        run_dir / "rejected.jsonl",
        leaderboard_path,
        run_dir / "journal.md",
        run_dir / "llm_candidates.jsonl",
        run_dir / "llm_raw.txt",
    ]
    artifacts.extend(sorted((run_dir / "best_positions").glob("*.json")))
    artifacts.extend(sorted((run_dir / "curves").glob("*.json")))

    # top-k 的收益曲线，用于报告叠加对比。
    top_k_curves: list[dict[str, Any]] = []
    if not leaderboard.empty:
        for _, lb_row in leaderboard.head(config.top_k).iterrows():
            cid = str(lb_row["id"])
            if cid in curves_by_id:
                top_k_curves.append(
                    {
                        "id": cid,
                        "rank": int(lb_row.get("rank", 0)),
                        "score": lb_row.get("score"),
                        "annual_return": lb_row.get("annual_return"),
                        "curve": curves_by_id[cid],
                    }
                )

    write_html_report(
        report_path,
        config=config,
        run_dir=run_dir,
        leaderboard=leaderboard,
        rejected=rejected,
        candidates=candidates,
        raw_candidate_count=len(raw_candidates),
        bars_summary=bars_summary,
        execution_log=execution_log,
        artifacts=artifacts,
        top_k_curves=top_k_curves,
    )
    _record_step(execution_log, "write_html_report", "ok", started_at, str(report_path.name))

    return RunResult(
        run_dir=run_dir,
        leaderboard_path=leaderboard_path,
        report_path=report_path,
        accepted_count=len(candidates),
        rejected_count=len(rejected),
    )
