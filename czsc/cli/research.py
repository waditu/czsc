"""research 子命令组：研究 / 回放 / 配置解析。"""

from __future__ import annotations

import json

import typer

from czsc.cli import _io

app = typer.Typer(no_args_is_help=True)


@app.command("config")
def config(
    signals: list[str] = typer.Argument(..., help="一个或多个信号字符串"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """由信号序列派生 signals_config 与所需频率。"""
    with _io.error_boundary(json_out):
        import czsc

        sc = czsc.get_signals_config(list(signals))
        freqs = czsc.get_signals_freqs(sc)
        out = {"signals_config": sc, "freqs": freqs}
        _io.emit(
            out,
            json_out=json_out,
            human=lambda d: typer.echo(json.dumps(d, ensure_ascii=False, indent=2)),
        )


@app.command("run")
def run(
    bars: str = typer.Argument(..., help="标准行情文件"),
    strategy: str = typer.Argument(..., help="strategy.json（含 symbol/positions/signals_config）"),
    sdt: str = typer.Option(None, "--sdt", help="起始时间覆盖"),
    output: str = typer.Option(None, "-o", "--output", help="holds 结果 CSV 落盘路径"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """内存研究（czsc.run_research）。"""
    with _io.error_boundary(json_out):
        import czsc

        df = _io.load_bars_df(bars)
        with open(strategy, encoding="utf-8") as fh:
            strat = json.loads(fh.read())
        res = czsc.run_research(df, strat, sdt=sdt)
        out = {"meta": res.meta}
        if output:
            res.holds_df().to_csv(output, index=False)
            out["holds_csv"] = output
        _io.emit(out, json_out=json_out, human=lambda d: typer.echo(json.dumps(d, ensure_ascii=False, indent=2)))


@app.command("replay")
def replay(
    bars: str = typer.Argument(..., help="标准行情文件"),
    strategy: str = typer.Argument(..., help="strategy.json"),
    res_path: str = typer.Option(..., "-o", "--output", help="回放结果落盘目录"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """落盘回放（czsc.run_replay）。"""
    with _io.error_boundary(json_out):
        import czsc

        df = _io.load_bars_df(bars)
        with open(strategy, encoding="utf-8") as fh:
            strat = json.loads(fh.read())
        res = czsc.run_replay(df, strat, res_path=res_path)
        _io.emit(
            {"meta": getattr(res, "meta", {}), "res_path": res_path},
            json_out=json_out,
            human=lambda d: typer.echo(f"回放完成 → {d['res_path']}"),
        )
