"""Candidate validation."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from auto_quant.schema import Candidate
from czsc import Position


def _reject(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"id": row.get("id", "<missing>"), "reason": reason}


def _normalize_position_data(data: dict[str, Any]) -> dict[str, Any]:
    """Accept common hand-written keys and return data suitable for Position.load."""
    normalized = deepcopy(data)
    if "t0" in normalized and "T0" not in normalized:
        normalized["T0"] = normalized.pop("t0")
    return normalized


def load_valid_candidates(
    rows: list[dict[str, Any]],
    *,
    max_candidates: int,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """Parse and validate JSONL candidate rows."""
    accepted: list[Candidate] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for row in rows:
        cid = str(row.get("id", "")).strip()
        hypothesis = str(row.get("hypothesis", "")).strip()
        position_data = row.get("position")

        if not cid:
            rejected.append(_reject(row, "id is required"))
            continue
        if cid in seen_ids:
            rejected.append(_reject(row, "duplicate id"))
            continue
        seen_ids.add(cid)
        if not hypothesis:
            rejected.append(_reject(row, "hypothesis is required"))
            continue
        if not isinstance(position_data, dict):
            rejected.append(_reject(row, "position must be an object"))
            continue

        normalized_position = _normalize_position_data(position_data)
        try:
            position = Position.load(normalized_position)
        except Exception as load_exc:  # noqa: BLE001 - validation should report load failures.
            try:
                position = Position.from_json(json.dumps(normalized_position, ensure_ascii=False))
            except Exception as json_exc:  # noqa: BLE001
                rejected.append(_reject(row, f"Position.load failed: {load_exc}; Position.from_json failed: {json_exc}"))
                continue

        if not position.opens:
            rejected.append(_reject(row, "position.opens must not be empty"))
            continue
        if not position.unique_signals:
            rejected.append(_reject(row, "position must contain at least one signal"))
            continue

        accepted.append(
            Candidate(
                id=cid,
                hypothesis=hypothesis,
                position_data=position.dump(with_data=False),
                position=position,
            )
        )

    if len(accepted) > max_candidates:
        overflow = accepted[max_candidates:]
        accepted = accepted[:max_candidates]
        rejected.extend({"id": c.id, "reason": f"over max_candidates={max_candidates}"} for c in overflow)

    return accepted, rejected
