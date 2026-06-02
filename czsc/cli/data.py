"""data 子命令组：造数与质量校验。"""

from __future__ import annotations

import typer

from czsc.cli import _io

app = typer.Typer(no_args_is_help=True)


@app.command("mock")
def mock(
    symbol: str = typer.Option("000001", help="标的代码"),
    freq: str = typer.Option("30分钟", help="频率（中文或枚举名 F30）"),
    sdt: str = typer.Option("20200101", help="起始日期"),
    edt: str = typer.Option("20210101", help="结束日期"),
    seed: int = typer.Option(42, help="随机种子（可复现）"),
    output: str = typer.Option(None, "-o", "--output", help="输出 CSV 路径；缺省打印到 stdout"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """生成标准 OHLCV K 线（czsc.mock.generate_symbol_kines）。"""
    with _io.error_boundary(json_out):
        from czsc.mock import generate_symbol_kines

        df = generate_symbol_kines(symbol, _io.freq_to_cn(freq), sdt, edt, seed=seed)
        if output:
            df.to_csv(output, index=False)
            _io.emit(
                {"output": output, "rows": len(df)},
                json_out=json_out,
                human=lambda d: typer.echo(f"已写入 {d['output']}（{d['rows']} 行）"),
            )
        elif json_out:
            typer.echo(df.to_json(orient="records", force_ascii=False, date_format="iso"))
        else:
            typer.echo(df.to_string(index=False))


@app.command("quality")
def quality(
    input: str = typer.Argument(..., help="标准行情文件（CSV/parquet/feather）或 - 读 stdin"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """K 线质量校验（czsc.check_kline_quality）。"""
    with _io.error_boundary(json_out):
        import czsc

        df = _io.load_bars_df(input)
        report = czsc.check_kline_quality(df)
        slim = {sym: {k: v.get("description") for k, v in checks.items()} for sym, checks in report.items()}

        def human(d):
            for sym, checks in d.items():
                typer.echo(f"[{sym}]")
                for k, desc in checks.items():
                    typer.echo(f"  {k}: {desc}")

        _io.emit(slim, json_out=json_out, human=human)
