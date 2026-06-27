"""Config and candidate schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from czsc import Position


@dataclass(frozen=True)
class AutoQuantConfig:
    task_name: str
    symbols: list[str]
    base_freq: str
    sdt: str
    edt: str
    candidates_path: Path
    output_dir: Path
    fee_rate: float = 2e-4
    yearly_days: int = 252
    seed: int = 42
    max_candidates: int = 20
    top_k: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path) -> AutoQuantConfig:
        required = ["task_name", "symbols", "base_freq", "sdt", "edt", "candidates_path"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"config missing required fields: {', '.join(missing)}")

        symbols = list(data["symbols"])
        if not symbols:
            raise ValueError("symbols must not be empty")

        def resolve_path(value: str | Path, default: str | None = None) -> Path:
            raw = Path(value or default or "")
            return raw if raw.is_absolute() else (base_dir / raw).resolve()

        return cls(
            task_name=str(data["task_name"]),
            symbols=[str(x) for x in symbols],
            base_freq=str(data["base_freq"]),
            sdt=str(data["sdt"]),
            edt=str(data["edt"]),
            candidates_path=resolve_path(data["candidates_path"]),
            output_dir=resolve_path(data.get("output_dir", "results")),
            fee_rate=float(data.get("fee_rate", 2e-4)),
            yearly_days=int(data.get("yearly_days", 252)),
            seed=int(data.get("seed", 42)),
            max_candidates=int(data.get("max_candidates", 20)),
            top_k=int(data.get("top_k", 3)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "symbols": self.symbols,
            "base_freq": self.base_freq,
            "sdt": self.sdt,
            "edt": self.edt,
            "candidates_path": str(self.candidates_path),
            "output_dir": str(self.output_dir),
            "fee_rate": self.fee_rate,
            "yearly_days": self.yearly_days,
            "seed": self.seed,
            "max_candidates": self.max_candidates,
            "top_k": self.top_k,
        }


@dataclass(frozen=True)
class Candidate:
    id: str
    hypothesis: str
    position_data: dict[str, Any]
    position: Position


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML config requires PyYAML; use JSON or install pyyaml") from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")
    return data


def load_config(path: Path) -> AutoQuantConfig:
    return AutoQuantConfig.from_dict(_load_mapping(path), base_dir=path.parent)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = json.loads(stripped)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: each JSONL row must be an object")
        rows.append(item)
    return rows


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
