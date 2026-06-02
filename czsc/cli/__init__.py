"""CZSC 命令行工具入口。

通过 ``czsc <子命令>`` 调用；所有命令支持 ``--json`` 输出（LLM 友好）。
"""

from __future__ import annotations

import typer

from czsc.cli import analyze, backtest, bench, data, plot, research, schema, signals

app = typer.Typer(
    help="CZSC 缠论技术分析命令行工具",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(signals.app, name="signals", help="信号目录与文档")
app.add_typer(research.app, name="research", help="策略研究 / 回放 / 配置解析")
app.add_typer(data.app, name="data", help="造数与质量校验")
app.add_typer(plot.app, name="plot", help="缠论 / 信号 HTML 可视化")
app.command("analyze", help="对一段 K 线跑缠论，输出分型 + 笔")(analyze.analyze)
app.command("backtest", help="传入 Position 对象 + 数据源，产出回测结果")(backtest.backtest)
app.command("bench", help="CZSC 吞吐量基准")(bench.bench)
app.command("schema", help="吐出全部命令/参数 schema 供 LLM 自发现")(schema.schema)


if __name__ == "__main__":
    app()
