"""Candidate scoring."""

from __future__ import annotations

from typing import Any

import pandas as pd

from auto_quant.backtest import SymbolBacktestResult


def _num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100
        except ValueError:
            return default
    try:
        return float(text)
    except ValueError:
        return default


def score_portfolio(
    portfolio_stats: dict[str, Any],
    symbol_results: list[SymbolBacktestResult],
    portfolio_weights: pd.DataFrame,
) -> dict[str, Any]:
    """Compute a compact score row from WeightBacktest stats and weights."""
    annual = _num(portfolio_stats.get("年化收益"))
    sharpe = _num(portfolio_stats.get("夏普比率"))
    max_drawdown = abs(_num(portfolio_stats.get("最大回撤")))
    turnover = _num(portfolio_stats.get("年化换手率"), _num(portfolio_stats.get("换手率")))

    if portfolio_weights.empty:
        trade_count = 0
    else:
        changed = portfolio_weights.sort_values(["symbol", "dt"]).groupby("symbol")["weight"].diff().fillna(0).abs()
        trade_count = int((changed > 1e-12).sum())

    covered = sum(1 for item in symbol_results if not item.weights.empty)
    coverage = covered / max(len(symbol_results), 1)

    hard_penalty = 0.0
    if trade_count < 3:
        hard_penalty += 1.0
    if coverage < 0.5:
        hard_penalty += 1.0

    score = sharpe * 0.35 + annual * 0.30 - max_drawdown * 0.25 - turnover * 0.10 + coverage * 0.10
    score -= hard_penalty

    return {
        "score": round(score, 6),
        "annual_return": annual,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "turnover": turnover,
        "trade_count": trade_count,
        "symbol_coverage": coverage,
    }
