"""Market data loading for MVP experiments."""

from __future__ import annotations

from typing import Any

from czsc import format_standard_kline
from czsc.mock import generate_symbol_kines


def load_mock_bars(
    symbols: list[str],
    *,
    freq: str,
    sdt: str,
    edt: str,
    seed: int,
) -> dict[str, Any]:
    """Generate deterministic mock bars for every symbol."""
    bars_by_symbol: dict[str, Any] = {}
    for i, symbol in enumerate(symbols):
        df = generate_symbol_kines(symbol, freq, sdt=sdt, edt=edt, seed=seed + i)
        bars_by_symbol[symbol] = format_standard_kline(df, freq=freq)
    return bars_by_symbol
