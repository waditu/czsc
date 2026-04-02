"""
Signal parsing helpers adapted to the currently available rs_czsc surface.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from parse import parse

try:
    from rs_czsc import derive_signals_config, derive_signals_freqs, list_all_signals
except ImportError:
    derive_signals_config = None
    derive_signals_freqs = None
    list_all_signals = None


def _normalize_template(template: str) -> str:
    """Normalize signal templates so line breaks do not break parsing."""
    text = re.sub(r"\s+", " ", template or "").strip()
    text = text.replace(" _", "_").replace("_ ", "_")
    return text


def _prefix_name(name: str, signals_module: str) -> str:
    return name if "." in str(name) else f"{signals_module}.{name}"


def _extract_signal_key(signal: Any) -> str:
    if isinstance(signal, str):
        parts = signal.split("_")
        return "_".join(parts[:3]) if len(parts) >= 3 else ""
    return str(getattr(signal, "key", "") or "")


class SignalsParser:
    """Parse signal strings into the flattened config structure used in czsc."""

    def __init__(self, signals_module: str = "czsc.signals"):
        self.signals_module = signals_module

        sig_pats_map: dict[str, str] = {}
        sig_k3_map: dict[str, str] = {}
        signal_defs = []

        if list_all_signals is not None:
            try:
                signal_defs = list_all_signals(include_kline=True, include_trader=True)
            except Exception as exc:
                logger.warning(f"list_all_signals unavailable, using empty parser registry: {exc}")

        for item in signal_defs:
            name = str(item.get("name", "")).strip()
            template = _normalize_template(str(item.get("param_template", "")).strip())
            if not name or not template:
                continue

            sig_pats_map[name] = template
            parts = template.split("_")
            if len(parts) >= 3:
                sig_k3_map[name] = parts[2].strip()

        self.sig_pats_map = sig_pats_map
        self.sig_k3_map = sig_k3_map
        self.sig_name_map = {k: [v] for k, v in sig_k3_map.items()}

    def parse_params(self, name: str, signal: str | Any):
        """Parse a signal string into its function parameters."""
        key = _extract_signal_key(signal)
        if not key:
            return None

        short_name = str(name).split(".")[-1]
        pats = self.sig_pats_map.get(short_name)
        if not pats:
            return None

        try:
            res = parse(pats, key)
            if not res:
                return None

            params = dict(res.named)
            if "di" in params:
                params["di"] = int(params["di"])
            params["name"] = _prefix_name(short_name, self.signals_module)
            return params
        except Exception as exc:
            logger.error(f"failed to parse signal params for {signal} - {name}: {exc}")
            return None

    def get_function_name(self, signal: str):
        """Guess the signal function name from a signal string."""
        key = _extract_signal_key(signal)
        if not key:
            return None

        parts = key.split("_")
        if len(parts) < 3:
            return None

        k3 = parts[2].strip()
        matches = [name for name, tk3 in self.sig_k3_map.items() if tk3 == k3]
        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            logger.error(f"signal {signal} matched multiple functions: {matches}")
            return None

        if derive_signals_config is not None:
            try:
                conf = derive_signals_config([signal])
                if conf:
                    return str(conf[0]["name"]).split(".")[-1]
            except Exception:
                pass
        return None

    def config_to_keys(self, config: list[dict]):
        """Convert signal configs back to signal keys when templates are available."""
        keys = []
        for conf in config:
            name = str(conf.get("name", "")).split(".")[-1]
            pats = self.sig_pats_map.get(name)
            if not pats:
                continue
            try:
                keys.append(pats.format(**conf))
            except Exception:
                continue
        return keys

    def parse(self, signal_seq: list[str]):
        """Parse a signal sequence into flattened configs."""
        if not signal_seq or derive_signals_config is None:
            return []

        try:
            conf = derive_signals_config(signal_seq)
        except Exception as exc:
            logger.error(f"derive_signals_config failed: {exc}")
            return []

        out: list[dict[str, Any]] = []
        for row in conf:
            raw = dict(row)
            item: dict[str, Any] = {
                "name": _prefix_name(str(raw.get("name", "")), self.signals_module),
            }
            if raw.get("freq"):
                item["freq"] = raw.get("freq")
            params = raw.get("params") or {}
            if isinstance(params, dict):
                item.update(params)
            for key, value in raw.items():
                if key not in {"name", "freq", "params"}:
                    item[key] = value
            if item not in out:
                out.append(item)
        return out


def get_signals_config(signals_seq: list[str], signals_module: str = "czsc.signals") -> list[dict]:
    """Get signal configs from a signal sequence."""
    return SignalsParser(signals_module=signals_module).parse(signals_seq)


def get_signals_freqs(signals_seq: list) -> list[str]:
    """Get unique frequencies referenced by a signal sequence."""
    if not signals_seq:
        return []

    if derive_signals_freqs is not None and derive_signals_config is not None:
        try:
            if isinstance(signals_seq[0], dict):
                return list(derive_signals_freqs(signals_seq))
            conf = derive_signals_config(signals_seq)
            return list(derive_signals_freqs(conf))
        except Exception:
            pass

    from czsc.utils import sorted_freqs

    freqs: list[str] = []
    for signal in signals_seq:
        freqs.extend(re.findall("|".join(sorted_freqs), str(signal)))
    return [freq for freq in sorted_freqs if freq in freqs]
