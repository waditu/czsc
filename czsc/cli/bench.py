"""bench 命令：CZSC 吞吐量基准（沿用 examples/17 逻辑）。"""

from __future__ import annotations

import time

import typer

from czsc.cli import _io


def bench(
    years: int = typer.Option(20, "--years", help="模拟数据年数"),
    freq: str = typer.Option("5分钟", "--freq", help="频率"),
    symbol: str = typer.Option("000001", "--symbol", help="标的"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """本地复现 CZSC 单周期吞吐量（bars/s）。"""
    with _io.error_boundary(json_out):
        from czsc import CZSC, format_standard_kline
        from czsc.mock import generate_symbol_kines

        end_year = 2024
        sdt = f"{end_year - years:04d}0101"
        edt = f"{end_year:04d}0101"
        cn = _io.freq_to_cn(freq)
        df = generate_symbol_kines(symbol, cn, sdt, edt)
        bars = format_standard_kline(df, cn)
        n = len(bars)

        t0 = time.perf_counter()
        CZSC(bars)
        construct_sec = time.perf_counter() - t0

        t1 = time.perf_counter()
        c2 = CZSC(bars[:1])
        for bar in bars[1:]:
            c2.update(bar)
        update_sec = time.perf_counter() - t1

        out = {
            "symbol": symbol,
            "freq": cn,
            "bars": n,
            "czsc_construct": {"sec": round(construct_sec, 4), "bars_per_sec": round(n / construct_sec)},
            "czsc_update": {"sec": round(update_sec, 4), "bars_per_sec": round(n / update_sec)},
        }

        def human(d):
            typer.echo(f"{d['symbol']} {d['freq']}  bars={d['bars']}")
            typer.echo(f"  构造:    {d['czsc_construct']['bars_per_sec']:>12,} bars/s")
            typer.echo(f"  增量推进: {d['czsc_update']['bars_per_sec']:>12,} bars/s")

        _io.emit(out, json_out=json_out, human=human)
