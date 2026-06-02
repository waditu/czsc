"""signals 子命令组：信号目录与文档。"""

from __future__ import annotations

import typer

from czsc.cli import _io

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_(
    category: str = typer.Option(None, "--category", help="按 category 过滤"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """列出全部信号函数（czsc._native.list_all_signals）。"""
    with _io.error_boundary(json_out):
        import czsc._native as native

        items = native.list_all_signals()  # type: ignore[attr-defined]  # 运行时存在，stub 未声明
        if category:
            items = [it for it in items if it.get("category") == category]

        def human(rows):
            for it in rows:
                typer.echo(f"{it['name']:40s} [{it['category']}] {it['param_template']}")
            typer.echo(f"共 {len(rows)} 个信号")

        _io.emit(items, json_out=json_out, human=human)


@app.command("doc")
def doc(
    name: str = typer.Argument(..., help="信号函数名"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """单个信号的参数模板与分类（来自 list_all_signals 条目）。"""
    with _io.error_boundary(json_out):
        import czsc._native as native

        entry = next((it for it in native.list_all_signals() if it["name"] == name), None)  # type: ignore[attr-defined]
        if entry is None:
            raise ValueError(f"未找到信号: {name}")

        def human(d):
            typer.echo(f"名称: {d['name']}")
            typer.echo(f"分类: {d['category']}  命名空间: {d['namespace']}")
            typer.echo(f"参数模板: {d['param_template']}")

        _io.emit(entry, json_out=json_out, human=human)
