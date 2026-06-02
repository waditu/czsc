"""CLI 共享层：输入加载、输出渲染、错误边界、连接器分发。"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from czsc import Freq, format_standard_kline

REQUIRED_OHLCV = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
_NUMERIC_OHLCV = ["open", "close", "high", "low", "vol", "amount"]

# ccxt 连接器只认 ccxt 周期串（1m/1h/1d…），需把中文频率映射过去
_CN_TO_CCXT = {
    "1分钟": "1m",
    "5分钟": "5m",
    "15分钟": "15m",
    "30分钟": "30m",
    "60分钟": "1h",
    "120分钟": "2h",
    "240分钟": "4h",
    "360分钟": "6h",
    "日线": "1d",
}


def freq_to_cn(freq: str) -> str:
    """把 Freq 枚举名（F30/D…）或中文（30分钟）统一成中文频率字符串。

    直接走 ``czsc.Freq`` 构造器：它同时接受枚举名与中文值，非法值抛 ValueError，
    与 Rust 端的频率定义保持单一来源，避免在 Python 侧手抄枚举清单造成漂移。
    """
    try:
        return Freq(freq).value
    except (ValueError, KeyError) as e:
        raise ValueError(f"无法识别的频率: {freq}；可用枚举名如 F30/D 或中文如 30分钟") from e


def load_bars_df(path: str) -> pd.DataFrame:
    """从 CSV/parquet/feather 或 stdin(-) 读标准 OHLCV DataFrame 并校验。"""
    # symbol 必须按字符串读，否则像 "000001" 这类代码会被解析成整数丢掉前导零
    if path == "-":
        df = pd.read_csv(sys.stdin, dtype={"symbol": str})
    else:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(p, dtype={"symbol": str})
        elif suffix in (".parquet", ".pq"):
            df = pd.read_parquet(p)
        elif suffix in (".feather", ".ipc"):
            df = pd.read_feather(p)
        else:
            raise ValueError(f"不支持的行情文件类型: {suffix}（支持 .csv/.parquet/.feather）")
    missing = [c for c in REQUIRED_OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"行情数据缺少必需列: {missing}；需要 {REQUIRED_OHLCV}")
    df["dt"] = pd.to_datetime(df["dt"])
    # symbol 统一为字符串（避免 000001 被当整数）；OHLCV 数值列统一为 float —— 否则
    # run_research / run_replay 透传给 Rust(Polars) 时 int64 的 vol 会被拒（要求 Float64）。
    df["symbol"] = df["symbol"].astype(str)
    df[_NUMERIC_OHLCV] = df[_NUMERIC_OHLCV].astype(float)
    return df


def emit(data: Any, *, json_out: bool, human: Callable[[Any], None]) -> None:
    """统一输出：json_out 时 stdout 纯 JSON；否则调 human 渲染。"""
    if json_out:
        typer.echo(json.dumps(data, ensure_ascii=False, default=str))
    else:
        human(data)


def fail(message: str, *, json_out: bool, err_type: str = "error", code: int = 1) -> None:
    """统一错误：json_out → stderr JSON；否则红字；退出非零。"""
    if json_out:
        typer.echo(json.dumps({"error": {"type": err_type, "message": message}}, ensure_ascii=False), err=True)
    else:
        typer.secho(f"错误: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


@contextmanager
def error_boundary(json_out: bool):
    """命令体统一异常边界：未捕获异常 → fail()。"""
    try:
        yield
    except typer.Exit:
        raise
    except Exception as e:  # noqa: BLE001
        fail(str(e), json_out=json_out, err_type=type(e).__name__)


def resolve_bars_for_symbol(symbol: str, *, source: str, freq: str, sdt: str, edt: str):
    """按 source 懒加载连接器，返回该 symbol 的 list[RawBar]。"""
    cn = freq_to_cn(freq)
    if source == "local":
        from czsc.connectors import local_data

        return local_data.get_raw_bars(symbol, cn, sdt, edt)
    if source == "tushare":
        from czsc.connectors import ts_connector

        return ts_connector.get_raw_bars(symbol, cn, sdt, edt)
    if source == "ccxt":
        from czsc.connectors import ccxt_connector

        ccxt_period = _CN_TO_CCXT.get(cn)
        if ccxt_period is None:
            raise ValueError(f"ccxt 数据源不支持频率 {cn}；支持 {sorted(_CN_TO_CCXT)}")
        df = ccxt_connector.get_raw_bars(symbol=symbol, period=ccxt_period, sdt=sdt, edt=edt)
        if "symbol" not in df.columns:
            df = df.assign(symbol=symbol)
        return format_standard_kline(df, cn)
    raise ValueError(f"未知数据源: {source}（支持 local/tushare/ccxt）")
