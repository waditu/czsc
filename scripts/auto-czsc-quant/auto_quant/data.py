"""Market data loading for auto-czsc-quant experiments."""

from __future__ import annotations

from typing import Any

import pandas as pd

from auto_quant.schema import AutoQuantConfig
from czsc import format_standard_kline
from czsc.mock import generate_symbol_kines

REQUIRED_OHLCV = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
NUMERIC_OHLCV = ["open", "close", "high", "low", "vol", "amount"]


def normalize_bars_df(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a standard OHLCV DataFrame."""
    missing = [c for c in REQUIRED_OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"行情数据缺少必需列: {missing}；需要 {REQUIRED_OHLCV}")
    df = df[REQUIRED_OHLCV].copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df["symbol"] = df["symbol"].astype(str)
    df[NUMERIC_OHLCV] = df[NUMERIC_OHLCV].astype(float)
    return df.sort_values(["symbol", "dt"], ignore_index=True)


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


def load_feather_bars(path: str, symbols: list[str], *, freq: str) -> dict[str, Any]:
    """Load standard OHLCV bars from a feather/ipc file."""
    df = normalize_bars_df(pd.read_feather(path))
    wanted = set(symbols)
    if wanted:
        df = df[df["symbol"].isin(wanted)].copy()
    if df.empty:
        raise ValueError(f"feather 行情文件没有匹配标的: {symbols}")

    bars_by_symbol: dict[str, Any] = {}
    for symbol, g in df.groupby("symbol", sort=False):
        bars_by_symbol[str(symbol)] = format_standard_kline(g, freq=freq)
    return bars_by_symbol


def _load_dotenv_value(key: str) -> str:
    """Read a value from environment or repo-local .env without logging secrets."""
    import os
    from pathlib import Path

    value = os.environ.get(key, "")
    if value:
        return value

    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() == key:
            return v.strip().strip("'\"")
    return ""


def load_tushare_bars(config: AutoQuantConfig) -> dict[str, Any]:
    """Load bars directly from Tushare through the existing CZSC connector."""
    token = _load_dotenv_value(config.tushare_token_env)
    if not token:
        raise RuntimeError(f"未找到 {config.tushare_token_env}，请在环境变量或 .env 中配置 Tushare token")

    import tushare as ts

    import czsc as cz
    from czsc.connectors import ts_connector

    ts.set_token(token)
    cz.set_url_token(token=token, url=config.tushare_url)

    bars_by_symbol: dict[str, Any] = {}
    for symbol in config.symbols:
        ts_symbol = symbol if "#" in symbol else f"{symbol}#{config.tushare_asset}"
        bars = ts_connector.get_raw_bars(
            symbol=ts_symbol,
            freq=config.base_freq,
            sdt=config.sdt,
            edt=config.edt,
            fq=config.tushare_fq,
            raw_bar=True,
        )
        if not bars:
            raise ValueError(f"Tushare 未返回行情: {ts_symbol}")
        bars_by_symbol[ts_symbol] = bars
    return bars_by_symbol


def load_bars(config: AutoQuantConfig) -> dict[str, Any]:
    """Load bars using the configured data source."""
    if config.data_source == "mock":
        return load_mock_bars(
            config.symbols,
            freq=config.base_freq,
            sdt=config.sdt,
            edt=config.edt,
            seed=config.seed,
        )
    if config.data_source == "feather":
        if not config.feather_path:
            raise ValueError("data_source=feather 时必须配置 feather_path")
        return load_feather_bars(str(config.feather_path), config.symbols, freq=config.base_freq)
    if config.data_source == "tushare":
        return load_tushare_bars(config)
    raise ValueError(f"未知 data_source: {config.data_source}（支持 mock/tushare/feather）")
