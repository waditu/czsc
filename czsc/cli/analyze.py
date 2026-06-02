"""analyze 命令：对一段 K 线跑缠论，输出分型 + 笔。"""

from __future__ import annotations

import typer

from czsc.cli import _io


def _fx_to_dict(fx) -> dict:
    return {
        "dt": fx.dt,
        "mark": str(fx.mark),
        "fx": fx.fx,
        "high": fx.high,
        "low": fx.low,
        "power_str": getattr(fx, "power_str", None),
    }


def _bi_to_dict(bi) -> dict:
    return {
        "sdt": bi.sdt,
        "edt": bi.edt,
        "direction": str(bi.direction),
        "high": bi.high,
        "low": bi.low,
        "length": bi.length,
        "power": bi.power,
    }


def analyze(
    input: str = typer.Argument(..., help="标准行情文件（CSV/parquet/feather）或 - 读 stdin"),
    freq: str = typer.Option("30分钟", "--freq", help="频率（中文或枚举名 F30）"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """缠论分型 + 笔识别（czsc.CZSC）。"""
    with _io.error_boundary(json_out):
        from czsc import CZSC, format_standard_kline

        df = _io.load_bars_df(input)
        cn = _io.freq_to_cn(freq)
        bars = format_standard_kline(df, cn)
        c = CZSC(bars)
        out = {
            "symbol": c.symbol,
            "freq": cn,
            "bars": len(c.bars_raw),
            "fx_list": [_fx_to_dict(fx) for fx in c.fx_list],
            "bi_list": [_bi_to_dict(bi) for bi in c.bi_list],
        }

        def human(d):
            typer.echo(f"{d['symbol']} {d['freq']}  bars={d['bars']}  分型={len(d['fx_list'])}  笔={len(d['bi_list'])}")
            for bi in d["bi_list"][-5:]:
                typer.echo(
                    f"  笔 {bi['direction']} {bi['sdt']}~{bi['edt']} "
                    f"[{bi['low']:.2f},{bi['high']:.2f}] len={bi['length']}"
                )

        _io.emit(out, json_out=json_out, human=human)
