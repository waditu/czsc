"""Experiment orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from auto_quant.backtest import backtest_position
from auto_quant.data import load_mock_bars
from auto_quant.journal import write_journal
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
    return [
        {"id": c.id, "hypothesis": c.hypothesis, "position": c.position_data}
        for c in candidates
    ]


def run_experiment(config: AutoQuantConfig) -> RunResult:
    """Run validation, mock backtests, scoring, and artifact writing."""
    run_dir = _new_run_dir(config)
    dump_json(run_dir / "config.json", config.to_dict())

    raw_candidates = read_jsonl(config.candidates_path)
    candidates, rejected = load_valid_candidates(raw_candidates, max_candidates=config.max_candidates)
    _write_jsonl(run_dir / "accepted.jsonl", _candidate_rows(candidates))

    bars_by_symbol = load_mock_bars(
        config.symbols,
        freq=config.base_freq,
        sdt=config.sdt,
        edt=config.edt,
        seed=config.seed,
    )

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
