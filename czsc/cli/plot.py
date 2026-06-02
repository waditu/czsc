"""plot 子命令组：缠论 / 信号 HTML 可视化。"""

from __future__ import annotations

import json

import typer

from czsc.cli import _io

app = typer.Typer(no_args_is_help=True)


@app.command("czsc")
def czsc_cmd(
    input: str = typer.Argument(..., help="标准行情文件"),
    freq: str = typer.Option("30分钟", "--freq", help="频率"),
    output: str = typer.Option("czsc.html", "-o", "--output", help="HTML 输出路径"),
    theme: str = typer.Option("light", "--theme", help="light/dark"),
    tail_bars: int = typer.Option(None, "--tail-bars", help="只画最后 N 根"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """单周期缠论结构 HTML（plot_czsc）。"""
    with _io.error_boundary(json_out):
        from czsc import CZSC, format_standard_kline
        from czsc.utils.plotting.lightweight import plot_czsc

        df = _io.load_bars_df(input)
        c = CZSC(format_standard_kline(df, _io.freq_to_cn(freq)))
        plot_czsc(c, output="html", path=output, theme=theme, tail_bars=tail_bars)  # type: ignore[arg-type]  # theme 为用户字符串，由 plot_czsc 内部校验
        _io.emit(
            {"output": output},
            json_out=json_out,
            human=lambda d: typer.echo(f"已写入 {d['output']}"),
        )


@app.command("signals")
def signals_cmd(
    input: str = typer.Argument(..., help="标准行情文件"),
    signals_config: str = typer.Option(..., "--signals-config", help="signals_config JSON 文件"),
    freq: str = typer.Option("30分钟", "--freq", help="频率"),
    output: str = typer.Option("signals.html", "-o", "--output", help="HTML 输出路径"),
    sdt: str = typer.Option("20170101", "--sdt", help="信号起始日期"),
    tail_bars: int = typer.Option(None, "--tail-bars", help="只画最后 N 根"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """信号叠加到 K 线主图 HTML（plot_czsc_signals）。"""
    with _io.error_boundary(json_out):
        from czsc import format_standard_kline
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        df = _io.load_bars_df(input)
        bars = format_standard_kline(df, _io.freq_to_cn(freq))
        with open(signals_config, encoding="utf-8") as fh:
            cfg = json.loads(fh.read())
        plot_czsc_signals(bars, signals_config=cfg, output="html", path=output, sdt=sdt, tail_bars=tail_bars)
        _io.emit(
            {"output": output},
            json_out=json_out,
            human=lambda d: typer.echo(f"已写入 {d['output']}"),
        )
