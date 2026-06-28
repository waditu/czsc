"""Backtest helpers for candidate positions."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import pandas as pd

from czsc import CzscStrategyBase, Position, WeightBacktest


class _PositionsStrategy(CzscStrategyBase):
    """Inject a concrete Position list into CzscStrategyBase."""

    def __init__(self, positions: list[Position], **kwargs: Any):
        self._positions = positions
        super().__init__(**kwargs)

    @property
    def positions(self) -> list[Position]:
        return self._positions


@dataclass(frozen=True)
class SymbolBacktestResult:
    symbol: str
    stats: dict[str, Any]
    holds: pd.DataFrame
    weights: pd.DataFrame


def position_for_symbol(position: Position, symbol: str) -> Position:
    """Clone a position and bind it to the symbol under test."""
    data = copy.deepcopy(position.dump(with_data=False))
    data["symbol"] = symbol
    return Position.load(data)


def holds_to_weight(holds: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Convert ResearchResult.holds_df() to WeightBacktest input."""
    cols = ["dt", "symbol", "weight", "price"]
    if holds is None or holds.empty:
        return pd.DataFrame(columns=pd.Index(cols))

    w = holds.groupby("dt", as_index=False).agg(weight=("pos", "mean"), price=("price", "first"))
    w["symbol"] = symbol
    return w[cols]


def backtest_position(
    position: Position,
    bars_by_symbol: dict[str, Any],
    *,
    fee_rate: float,
    yearly_days: int,
) -> tuple[list[SymbolBacktestResult], dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Run one candidate over every configured symbol.

    返回 (symbol_results, portfolio_stats, portfolio_weights, portfolio_daily_return)。
    portfolio_daily_return 是组合日收益序列 (date, return)，供报告叠加收益曲线。
    """
    symbol_results: list[SymbolBacktestResult] = []
    weight_frames: list[pd.DataFrame] = []

    for symbol, bars in bars_by_symbol.items():
        pos = position_for_symbol(position, symbol)
        strategy = _PositionsStrategy([pos], symbol=symbol)
        if not strategy.signals_config:
            raise ValueError("position 未解析出任何有效信号")

        res = strategy.backtest(bars)
        holds = res.holds_df()
        weights = holds_to_weight(holds, symbol)
        stats = {"warning": "无成交"}
        if not weights.empty:
            stats = WeightBacktest(weights, fee_rate=fee_rate, yearly_days=yearly_days).stats
            weight_frames.append(weights)
        symbol_results.append(SymbolBacktestResult(symbol=symbol, stats=stats, holds=holds, weights=weights))

    if weight_frames:
        portfolio_weights = pd.concat(weight_frames, ignore_index=True)
        wb = WeightBacktest(portfolio_weights, fee_rate=fee_rate, yearly_days=yearly_days)
        portfolio_stats = wb.stats
        portfolio_daily_return = _daily_return_total(wb.daily_return)
    else:
        portfolio_weights = pd.DataFrame(columns=pd.Index(["dt", "symbol", "weight", "price"]))
        portfolio_stats = {"warning": "全部 symbol 无成交"}
        portfolio_daily_return = pd.DataFrame(columns=pd.Index(["date", "return"]))

    return symbol_results, portfolio_stats, portfolio_weights, portfolio_daily_return


def _daily_return_total(daily: pd.DataFrame) -> pd.DataFrame:
    """从 daily_return 宽表提取 (date, return)，兼容 date 作为列或作为索引。"""
    ret_col = "total" if "total" in daily.columns else daily.columns[0]
    if "date" in daily.columns:
        out = daily[["date", ret_col]].rename(columns={ret_col: "return"}).copy()
    else:
        out = daily[[ret_col]].rename(columns={ret_col: "return"}).reset_index(names="date")
    out["date"] = pd.to_datetime(out["date"])
    return out.sort_values("date").reset_index(drop=True)[["date", "return"]]
