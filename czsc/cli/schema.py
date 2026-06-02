"""schema 元命令：内省 typer app，吐出全部命令/参数 schema 供 LLM 自发现。"""

from __future__ import annotations

import typer

from czsc.cli import _io


def _walk(cmd, prefix):
    out = []
    # 命令组（Group）有 commands 属性；叶子命令没有 —— 用 duck-typing 兼容
    # typer 0.26 自带命令体系，不依赖顶层 click 模块。
    subcommands = getattr(cmd, "commands", None)
    if subcommands:
        for name, sub in subcommands.items():
            out += _walk(sub, prefix + [name])
    else:
        params = []
        for p in cmd.params:
            params.append(
                {
                    "name": p.name,
                    "opts": list(getattr(p, "opts", [])),
                    "type": getattr(p.type, "name", str(p.type)),
                    "required": bool(p.required),
                    "is_flag": bool(getattr(p, "is_flag", False)),
                    "default": p.default if not callable(p.default) else None,
                    "help": getattr(p, "help", None),
                }
            )
        out.append({"command": " ".join(prefix), "help": (cmd.help or "").strip(), "params": params})
    return out


def schema(
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """导出全部子命令与参数 schema。"""
    with _io.error_boundary(json_out):
        from czsc.cli import app as root_app

        cmd = typer.main.get_command(root_app)
        data = _walk(cmd, ["czsc"])

        def human(rows):
            for c in rows:
                typer.echo(f"{c['command']}  —  {c['help']}")
                for p in c["params"]:
                    typer.echo(f"    {p['opts'] or [p['name']]}  ({p['type']})  {p['help'] or ''}")

        _io.emit(data, json_out=json_out, human=human)
