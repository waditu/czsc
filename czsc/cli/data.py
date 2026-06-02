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
        else:
            _io.emit(
                df.to_dict("records"),
                json_out=json_out,
                human=lambda d: typer.echo(df.to_string(index=False)),
            )


@app.command("quality")
def quality(
    input: str = typer.Argument(..., help="标准行情文件（CSV/parquet/feather）或 - 读 stdin"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """K 线质量校验（czsc.check_kline_quality）。"""
    with _io.error_boundary(json_out):
        import contextlib
        import io

        import czsc

        df = _io.load_bars_df(input)
        # check_kline_quality 在发现问题时会把问题行 print 到 stdout，会污染 --json
        # 的纯 JSON 契约 —— 重定向吃掉这个副作用，问题行数从返回结构里另行给出。
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report = czsc.check_kline_quality(df)
        slim = {}
        for sym, checks in report.items():
            slim[sym] = {}
            for k, v in checks.items():
                rows = v.get("rows")
                slim[sym][k] = {
                    "description": v.get("description"),
                    "n_bad_rows": int(len(rows)) if rows is not None else 0,
                }

        def human(d):
            for sym, checks in d.items():
                typer.echo(f"[{sym}]")
                for k, info in checks.items():
                    flag = "" if info["n_bad_rows"] == 0 else f"  ⚠️ {info['n_bad_rows']} 行异常"
                    typer.echo(f"  {k}: {info['description']}{flag}")

        _io.emit(slim, json_out=json_out, human=human)
