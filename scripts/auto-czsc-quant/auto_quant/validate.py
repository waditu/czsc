"""Candidate validation."""

from __future__ import annotations

import json
from typing import Any

from auto_quant.schema import IMMUTABLE_FIELD_NAMES, Candidate, lock_immutable_fields
from auto_quant.signals import event_signature
from czsc import Position, derive_signals_config


def _reject(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"id": row.get("id", "<missing>"), "reason": reason}


def _immutable_overrides(baseline_position: dict[str, Any] | None) -> dict[str, Any]:
    """从 baseline 提取不可变参数（缺字段回退安全默认值）。"""
    from auto_quant.schema import IMMUTABLE_POSITION_FIELDS

    overrides = dict(IMMUTABLE_POSITION_FIELDS)
    if baseline_position:
        for key in overrides:
            if key in baseline_position:
                overrides[key] = baseline_position[key]
    return overrides


def _detect_freq(position_data: dict[str, Any], baseline_position: dict[str, Any] | None) -> str:
    """从候选或 baseline 的首个信号推断目标周期（用于信号真实性校验）。"""
    for src in (position_data, baseline_position or {}):
        for ev in src.get("opens") or []:
            for sig in ev.get("signals_all") or []:
                text = sig.get("key", "") if isinstance(sig, dict) else str(sig)
                if "_" in text:
                    return text.split("_", 1)[0]
    return ""


def _flatten_event_signals(events: list[dict[str, Any]]) -> list[str]:
    """把 event 里的信号统一成字符串列表（兼容 str 与 {key,value} dict）。"""
    out: list[str] = []
    for ev in events or []:
        for field in ("signals_all", "signals_any", "signals_not"):
            for sig in ev.get(field) or []:
                if isinstance(sig, dict):
                    key = sig.get("key", "")
                    value = sig.get("value", "")
                    out.append(f"{key}_{value}" if value else str(key))
                else:
                    out.append(str(sig))
    return out


def load_valid_candidates(
    rows: list[dict[str, Any]],
    *,
    max_candidates: int,
    baseline_position: dict[str, Any] | None = None,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """Parse and validate JSONL candidate rows.

    校验规则：
    - interval / timeout / stop_loss / T0 不参与优化，强制覆盖。
    - opens/exits 的每个信号必须在 czsc 注册表中真实存在（derive_signals_config 可解析），
      否则拒绝——避免臆造信号导致 event 永不触发。
    - 候选的 event 信号签名必须与 baseline 不同（防止无效克隆，要求每次迭代真正改 event）。
    """
    immutable_overrides = _immutable_overrides(baseline_position)
    baseline_sig = event_signature((baseline_position or {}).get("opens", [])) | event_signature(
        (baseline_position or {}).get("exits", [])
    )
    accepted: list[Candidate] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_signatures: set[frozenset[str]] = set()

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

        # 信号真实性校验：每个 event 信号必须能被 derive_signals_config 解析。
        unknown = _unknown_signals(position_data, baseline_position)
        if unknown:
            rejected.append(_reject(row, f"contains unknown signal(s) not in registry: {unknown[:3]}"))
            continue

        # 有效变异校验：event 信号签名必须与 baseline 不同。
        cand_sig = event_signature(position_data.get("opens", [])) | event_signature(position_data.get("exits", []))
        if baseline_position and cand_sig and cand_sig == baseline_sig:
            rejected.append(_reject(row, "no-op clone: opens/exits signals identical to baseline"))
            continue
        if cand_sig in seen_signatures:
            rejected.append(_reject(row, "duplicate event signature (same as an earlier candidate)"))
            continue

        locked_position = lock_immutable_fields(position_data, overrides=immutable_overrides)
        try:
            position = Position.load(locked_position)
        except Exception as load_exc:  # noqa: BLE001 - validation should report load failures.
            try:
                position = Position.from_json(json.dumps(locked_position, ensure_ascii=False))
            except Exception as json_exc:  # noqa: BLE001
                rejected.append(
                    _reject(row, f"Position.load failed: {load_exc}; Position.from_json failed: {json_exc}")
                )
                continue

        if not position.opens:
            rejected.append(_reject(row, "position.opens must not be empty"))
            continue
        if not position.unique_signals:
            rejected.append(_reject(row, "position must contain at least one signal"))
            continue

        seen_signatures.add(cand_sig)
        accepted.append(
            Candidate(
                id=cid,
                hypothesis=hypothesis,
                position_data=position.dump(with_data=False),
                position=position,
                # 记录候选是否试图触碰不可变参数（用于报告透明展示）。
                touched_immutable=[
                    k
                    for k in IMMUTABLE_FIELD_NAMES.split(" / ")
                    if _raw_value(position_data, k) != immutable_overrides.get(k)
                ],
            )
        )

    if len(accepted) > max_candidates:
        overflow = accepted[max_candidates:]
        accepted = accepted[:max_candidates]
        rejected.extend({"id": c.id, "reason": f"over max_candidates={max_candidates}"} for c in overflow)

    return accepted, rejected


def _unknown_signals(position_data: dict[str, Any], baseline_position: dict[str, Any] | None) -> list[str]:
    """返回候选里无法被 derive_signals_config 解析的信号（即注册表中不存在）。"""
    freq = _detect_freq(position_data, baseline_position)
    unknown: list[str] = []
    for sig in _flatten_event_signals(position_data.get("opens", [])) + _flatten_event_signals(
        position_data.get("exits", [])
    ):
        try:
            ok = bool(derive_signals_config([sig]))
        except Exception:  # noqa: BLE001
            ok = False
        if (
            not ok
            and freq
            and sig
            not in _flatten_event_signals((baseline_position or {}).get("opens", []))
            + _flatten_event_signals((baseline_position or {}).get("exits", []))
        ):
            # baseline 里的信号视为已知（即便 skill 文档没覆盖）。
            unknown.append(sig)
    return unknown


def _raw_value(position_data: dict[str, Any], key: str) -> Any:
    # 候选里 T0 可能写成 t0。
    if key in position_data:
        return position_data[key]
    if key == "T0" and "t0" in position_data:
        return position_data["t0"]
    return None
