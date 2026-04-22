"""rs_czsc 信号执行桥接层。"""

from __future__ import annotations

from typing import Any

import pandas as pd
from rs_czsc import run_research


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


def _infer_base_freq(bars: Any, signals_config: list[dict]) -> str:
    if isinstance(bars, list) and bars:
        freq = getattr(getattr(bars[0], "freq", None), "value", None)
        if freq:
            return str(freq)

    for cfg in signals_config:
        freq = cfg.get("freq")
        if freq:
            return str(freq)
    return "日线"


def _placeholder_position(symbol: str) -> dict[str, Any]:
    return {
        "name": "_signals_only",
        "symbol": symbol,
        "opens": [],
        "exits": [],
        "interval": 0,
        "timeout": 0,
        "stop_loss": 0,
        "T0": True,
    }


def run_rs_signal_generation(
    bars: Any,
    signals_config: list[dict],
    *,
    sdt: str,
    symbol: str | None = None,
    bg_max_count: int = 5000,
    include_sdt_bar: bool | None = None,
) -> pd.DataFrame:
    """使用 rs_czsc 统一执行引擎生成信号 DataFrame。"""
    if not signals_config:
        return pd.DataFrame()

    bars_df = _bars_to_dataframe(bars, symbol=symbol)
    if bars_df.empty:
        return pd.DataFrame()

    symbol_ = str(symbol or bars_df["symbol"].iloc[-1])
    strategy: dict[str, Any] = {
        "name": f"{symbol_}-signals-only",
        "symbol": symbol_,
        "base_freq": _infer_base_freq(bars, signals_config),
        "signals_module": "czsc.signals",
        "signals_config": signals_config,
        "positions": [_placeholder_position(symbol_)],
        "market": "默认",
        "bg_max_count": int(bg_max_count),
    }
    if include_sdt_bar is not None:
        strategy["include_sdt_bar"] = bool(include_sdt_bar)

    res = run_research(bars_df, strategy, sdt=sdt, opts={"emit_signals": True})
    return res.signals_df()


def get_last_signal_map(
    bars: Any,
    signals_config: list[dict],
    *,
    symbol: str | None = None,
    bg_max_count: int = 5000,
    include_sdt_bar: bool | None = None,
) -> dict[str, Any]:
    """获取最新一根 K 线对应的信号字典。"""
    bars_df = _bars_to_dataframe(bars, symbol=symbol)
    if bars_df.empty:
        return {}

    first_dt = bars_df["dt"].iloc[0]
    df = run_rs_signal_generation(
        bars,
        signals_config,
        sdt=pd.to_datetime(first_dt).strftime("%Y-%m-%d %H:%M:%S"),
        symbol=symbol,
        bg_max_count=bg_max_count,
        include_sdt_bar=include_sdt_bar,
    )
    if df.empty:
        return {}
    return df.iloc[-1].to_dict()
