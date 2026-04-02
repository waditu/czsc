"""rs_czsc 信号执行桥接层。"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _bars_to_dataframe(bars: Any, symbol: str | None = None) -> pd.DataFrame:
    if isinstance(bars, pd.DataFrame):
        df = bars.copy()
    else:
        rows = []
        for bar in bars:
            rows.append(
                {
                    "symbol": getattr(bar, "symbol", symbol),
                    "dt": getattr(bar, "dt", None),
                    "open": getattr(bar, "open", None),
                    "close": getattr(bar, "close", None),
                    "high": getattr(bar, "high", None),
                    "low": getattr(bar, "low", None),
                    "vol": getattr(bar, "vol", None),
                    "amount": getattr(bar, "amount", None),
                }
            )
        df = pd.DataFrame(rows)

    if "symbol" not in df.columns:
        df["symbol"] = symbol
    elif symbol:
        df["symbol"] = df["symbol"].fillna(symbol)

    required = ["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"bars 缺少列：{col}")

    df = df[required].copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df["symbol"] = df["symbol"].astype(str)
    for col in ["open", "close", "high", "low", "vol", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df = df.dropna(subset=required)
    df = df.sort_values("dt").drop_duplicates(subset=["dt"], keep="last").reset_index(drop=True)
    return df


def run_rs_signal_generation(
    bars: Any,
    signals_config: list[dict],
    *,
    sdt: str,
    symbol: str | None = None,
    bg_max_count: int = 5000,
    include_sdt_bar: bool | None = None,
) -> pd.DataFrame:
    """当前版本不再依赖已删除的研究执行链，保留兼容空信号表结构。"""
    del signals_config, bg_max_count, include_sdt_bar

    bars_df = _bars_to_dataframe(bars, symbol=symbol)
    if bars_df.empty:
        return pd.DataFrame()

    mask = bars_df["dt"] >= pd.to_datetime(sdt)
    base_cols = ["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]
    return bars_df.loc[mask, base_cols].reset_index(drop=True)


def get_last_signal_map(
    bars: Any,
    signals_config: list[dict],
    *,
    symbol: str | None = None,
    bg_max_count: int = 5000,
    include_sdt_bar: bool | None = None,
) -> dict[str, Any]:
    """当前版本不再生成附加信号，保持空字典兼容。"""
    del bars, signals_config, symbol, bg_max_count, include_sdt_bar
    return {}
