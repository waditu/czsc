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
    output_dir: Path
    data_source: str = "mock"
    candidates_path: Path | None = None
    candidate_mode: str = "file"
    baseline_position_path: Path | None = None
    include_baseline: bool = False
    feather_path: Path | None = None
    tushare_asset: str = "E"
    tushare_fq: str = "后复权"
    tushare_url: str = "http://api.tushare.pro"
    tushare_token_env: str = "TUSHARE_TOKEN"
    llm_base_url_env: str = "ANTHROPIC_BASE_URL"
    llm_api_key_env: str = "ANTHROPIC_API_KEY"
    llm_model_env: str = "ANTHROPIC_MODEL"
    llm_model: str = ""
    llm_candidate_count: int = 3
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.2
    llm_timeout: int = 120
    llm_extra_prompt: str = ""
    fee_rate: float = 2e-4
    yearly_days: int = 252
    seed: int = 42
    max_candidates: int = 20
    top_k: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path) -> AutoQuantConfig:
        required = ["task_name", "symbols", "base_freq", "sdt", "edt"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"config missing required fields: {', '.join(missing)}")

        symbols = list(data["symbols"])
        if not symbols:
            raise ValueError("symbols must not be empty")

        def resolve_path(value: str | Path, default: str | None = None) -> Path:
            raw = Path(value or default or "")
            return raw if raw.is_absolute() else (base_dir / raw).resolve()

        def optional_path(key: str) -> Path | None:
            value = data.get(key)
            if not value:
                return None
            return resolve_path(value)

        return cls(
            task_name=str(data["task_name"]),
            symbols=[str(x) for x in symbols],
            base_freq=str(data["base_freq"]),
            sdt=str(data["sdt"]),
            edt=str(data["edt"]),
            output_dir=resolve_path(data.get("output_dir", "results")),
            data_source=str(data.get("data_source", "mock")),
            candidates_path=optional_path("candidates_path"),
            candidate_mode=str(data.get("candidate_mode", "file")),
            baseline_position_path=optional_path("baseline_position_path"),
            include_baseline=bool(data.get("include_baseline", False)),
            feather_path=optional_path("feather_path"),
            tushare_asset=str(data.get("tushare_asset", "E")),
            tushare_fq=str(data.get("tushare_fq", "后复权")),
            tushare_url=str(data.get("tushare_url", "http://api.tushare.pro")),
            tushare_token_env=str(data.get("tushare_token_env", "TUSHARE_TOKEN")),
            llm_base_url_env=str(data.get("llm_base_url_env", "ANTHROPIC_BASE_URL")),
            llm_api_key_env=str(data.get("llm_api_key_env", "ANTHROPIC_API_KEY")),
            llm_model_env=str(data.get("llm_model_env", "ANTHROPIC_MODEL")),
            llm_model=str(data.get("llm_model", "")),
            llm_candidate_count=int(data.get("llm_candidate_count", 3)),
            llm_max_tokens=int(data.get("llm_max_tokens", 4096)),
            llm_temperature=float(data.get("llm_temperature", 0.2)),
            llm_timeout=int(data.get("llm_timeout", 120)),
            llm_extra_prompt=str(data.get("llm_extra_prompt", "")),
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
            "output_dir": str(self.output_dir),
            "data_source": self.data_source,
            "candidates_path": str(self.candidates_path) if self.candidates_path else None,
            "candidate_mode": self.candidate_mode,
            "baseline_position_path": str(self.baseline_position_path) if self.baseline_position_path else None,
            "include_baseline": self.include_baseline,
            "feather_path": str(self.feather_path) if self.feather_path else None,
            "tushare_asset": self.tushare_asset,
            "tushare_fq": self.tushare_fq,
            "tushare_url": self.tushare_url,
            "tushare_token_env": self.tushare_token_env,
            "llm_base_url_env": self.llm_base_url_env,
            "llm_api_key_env": self.llm_api_key_env,
            "llm_model_env": self.llm_model_env,
            "llm_model": self.llm_model,
            "llm_candidate_count": self.llm_candidate_count,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_temperature": self.llm_temperature,
            "llm_timeout": self.llm_timeout,
            "llm_extra_prompt": self.llm_extra_prompt,
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
