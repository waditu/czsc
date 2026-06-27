"""Experiment orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.backtest import backtest_position
from auto_quant.data import load_bars
from auto_quant.journal import write_journal
from auto_quant.llm import generate_llm_candidates
from auto_quant.schema import AutoQuantConfig, Candidate, dump_json, read_jsonl
from auto_quant.scorer import score_portfolio
from auto_quant.validate import load_valid_candidates


@dataclass(frozen=True)
class RunResult:
    run_dir: Path
    leaderboard_path: Path
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


def _load_candidate_rows(config: AutoQuantConfig, run_dir: Path) -> list[dict[str, Any]]:
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
        return rows

    if config.candidate_mode == "llm":
        llm_rows, raw = generate_llm_candidates(config)
        (run_dir / "llm_raw.txt").write_text(raw, encoding="utf-8")
        _write_jsonl(run_dir / "llm_candidates.jsonl", llm_rows)
        rows.extend(llm_rows)
        return rows

    raise ValueError(f"未知 candidate_mode: {config.candidate_mode}（支持 file/llm）")


def run_experiment(config: AutoQuantConfig) -> RunResult:
    """Run validation, mock backtests, scoring, and artifact writing."""
    run_dir = _new_run_dir(config)
    dump_json(run_dir / "config.json", config.to_dict())

    raw_candidates = _load_candidate_rows(config, run_dir)
    candidates, rejected = load_valid_candidates(raw_candidates, max_candidates=config.max_candidates)
    _write_jsonl(run_dir / "accepted.jsonl", _candidate_rows(candidates))

    bars_by_symbol = load_bars(config)

    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            symbol_results, portfolio_stats, portfolio_weights = backtest_position(
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
        except Exception as exc:  # noqa: BLE001 - experiment runners must record candidate failures.
            rejected.append({"id": candidate.id, "reason": f"backtest failed: {exc}"})

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

    return RunResult(
        run_dir=run_dir,
        leaderboard_path=leaderboard_path,
        accepted_count=len(candidates),
        rejected_count=len(rejected),
    )
