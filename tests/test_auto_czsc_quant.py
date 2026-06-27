from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTO_QUANT = ROOT / "scripts" / "auto-czsc-quant"
sys.path.insert(0, str(AUTO_QUANT))

from auto_quant.goal_prompt import build_goal_prompt  # noqa: E402
from auto_quant.runner import run_experiment  # noqa: E402
from auto_quant.schema import AutoQuantConfig  # noqa: E402
from auto_quant.validate import load_valid_candidates  # noqa: E402


def _position_data(symbol: str = "000001") -> dict:
    return {
        "symbol": symbol,
        "name": "表里关系多头",
        "opens": [
            {
                "name": "开多_表里向上",
                "operate": "开多",
                "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"],
                "signals_any": [],
                "signals_not": [],
            }
        ],
        "exits": [
            {
                "name": "平多_表里向下",
                "operate": "平多",
                "signals_all": ["30分钟_D1_表里关系V230101_向下_任意_任意_0"],
                "signals_any": [],
                "signals_not": [],
            }
        ],
        "interval": 0,
        "timeout": 20,
        "stop_loss": 300,
        "t0": False,
    }


def test_load_valid_candidates_accepts_position_dict() -> None:
    rows = [{"id": "a", "hypothesis": "baseline", "position": _position_data()}]
    accepted, rejected = load_valid_candidates(rows, max_candidates=10)
    assert not rejected
    assert len(accepted) == 1
    assert accepted[0].position.name == "表里关系多头"


def test_load_valid_candidates_rejects_bad_rows() -> None:
    rows = [
        {"id": "a", "hypothesis": "", "position": _position_data()},
        {"id": "b", "hypothesis": "bad", "position": {"opens": []}},
    ]
    accepted, rejected = load_valid_candidates(rows, max_candidates=10)
    assert not accepted
    assert [x["id"] for x in rejected] == ["a", "b"]


def test_run_experiment_with_mock_data(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        json.dumps({"id": "baseline", "hypothesis": "mock smoke", "position": _position_data()}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    config = AutoQuantConfig(
        task_name="smoke",
        symbols=["000001"],
        base_freq="30分钟",
        sdt="20240101",
        edt="20240201",
        candidates_path=candidates,
        output_dir=tmp_path / "results",
        top_k=1,
    )
    result = run_experiment(config)
    assert result.leaderboard_path.exists()
    assert (result.run_dir / "journal.md").exists()
    assert (result.run_dir / "accepted.jsonl").exists()
    assert "leaderboard" in build_goal_prompt(result.run_dir)
