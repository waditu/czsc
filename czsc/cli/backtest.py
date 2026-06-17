"""backtest 命令：传入 Position 对象 + 数据源，产出回测结果。"""

from __future__ import annotations

import json as _json

import pandas as pd
import typer

from czsc import CzscStrategyBase, Position, WeightBacktest, format_standard_kline
from czsc.cli import _io


class _PositionsStrategy(CzscStrategyBase):
    """把外部传入的 positions 注入抽象基类（基类 positions 为抽象属性）。"""

    def __init__(self, position_list, **kwargs):
        self._position_list = position_list
        super().__init__(**kwargs)

    @property
    def positions(self):
        return self._position_list


def _holds_to_weight(holds: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """holds_df -> 权重表 {dt,symbol,weight,price}；多 position 按 dt 等权聚合。

    holds 为空（该 symbol 零成交）时返回空表；symbol 列强制用回测标的，避免
    被 position 自带的 symbol 串味（holds_df 的 symbol 取自 position.symbol）。
    """
    cols = ["dt", "symbol", "weight", "price"]
    if holds is None or holds.empty:
        return pd.DataFrame(columns=pd.Index(cols))
    # groupby().agg() 在 pandas stub 下被推断为 DataFrame|Series union，这里实为 DataFrame
    w = holds.groupby("dt", as_index=False).agg(weight=("pos", "mean"), price=("price", "first"))
    w["symbol"] = symbol  # type: ignore[index]
    return w[cols]  # type: ignore[return-value]


def _backtest_symbol(positions, bars, symbol: str) -> pd.DataFrame:
    strat = _PositionsStrategy(positions, symbol=symbol)
    if not strat.signals_config:
        raise ValueError("position 未解析出任何有效信号（请检查 Position JSON 里的信号名是否正确）")
    res = strat.backtest(bars)
    return _holds_to_weight(res.holds_df(), symbol)


def backtest(
    positions: list[str] = typer.Argument(..., help="一个或多个 Position JSON 文件"),
    symbol: list[str] = typer.Option(None, "--symbol", help="标的（可重复或逗号分隔，支持多 symbol）"),
    source: str = typer.Option("local", "--source", help="数据源 local/tushare/ccxt"),
    freq: str = typer.Option("30分钟", "--freq", help="频率"),
    sdt: str = typer.Option("20200101", "--sdt", help="起始日期"),
    edt: str = typer.Option("20240101", "--edt", help="结束日期"),
    bars_file: str = typer.Option(None, "--bars", help="标准行情文件（可含多 symbol）；与 --symbol 二选一"),
    html: str = typer.Option(None, "--html", help="生成 wbt HTML 回测报告路径"),
    output: str = typer.Option(None, "-o", "--output", help="结果 JSON 落盘路径"),
    fee_rate: float = typer.Option(2e-4, "--fee-rate", help="手续费率"),
    json_out: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    """positions + 数据源 → 逐 symbol 回测 + 组合聚合（czsc 回测 + WeightBacktest）。"""
    with _io.error_boundary(json_out):
        pos_objs = []
        for p in positions:
            with open(p, encoding="utf-8") as fh:
                pos_objs.append(Position.from_json(fh.read()))

        weight_frames: dict[str, pd.DataFrame] = {}
        if bars_file:
            df = _io.load_bars_df(bars_file)
            for sym, g in df.groupby("symbol"):
                bars = format_standard_kline(g, _io.freq_to_cn(freq))
                weight_frames[str(sym)] = _backtest_symbol(pos_objs, bars, str(sym))
        else:
            syms: list[str] = []
            for s in symbol or []:
                syms.extend(x for x in s.split(",") if x)
            if not syms:
                raise ValueError("必须提供 --symbol（可多个）或 --bars 行情文件之一")
            for sym in syms:
                bars = _io.resolve_bars_for_symbol(sym, source=source, freq=freq, sdt=sdt, edt=edt)
                weight_frames[sym] = _backtest_symbol(pos_objs, bars, sym)

        # 零成交的 symbol 不进 WeightBacktest（空权重表会抛底层转换错），单独标注
        per_symbol = {}
        for sym, w in weight_frames.items():
            per_symbol[sym] = {"warning": "无成交"} if w.empty else WeightBacktest(w, fee_rate=fee_rate).stats

        nonempty = [w for w in weight_frames.values() if not w.empty]
        if nonempty:
            portfolio_w = pd.concat(nonempty, ignore_index=True)
            portfolio = WeightBacktest(portfolio_w, fee_rate=fee_rate).stats
        else:
            portfolio_w = pd.DataFrame(columns=pd.Index(["dt", "symbol", "weight", "price"]))
            portfolio = {"warning": "全部 symbol 无成交"}

        html_written = None
        if html and not portfolio_w.empty:
            from wbt import generate_backtest_report

            generate_backtest_report(portfolio_w, output_path=html, title="CZSC 回测报告")
            html_written = html

        result = {"symbols": per_symbol, "portfolio": portfolio, "html": html_written}
        if output:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(_json.dumps(result, ensure_ascii=False, default=str))

        def human(d):
            typer.echo("== 组合绩效 ==")
            for k in ["年化收益", "夏普比率", "最大回撤", "日胜率"]:
                typer.echo(f"  {k}: {d['portfolio'].get(k)}")
            for sym, st in d["symbols"].items():
                typer.echo(f"  [{sym}] 年化={st.get('年化收益')} 夏普={st.get('夏普比率')}")
            if d["html"]:
                typer.echo(f"HTML 报告: {d['html']}")

        _io.emit(result, json_out=json_out, human=human)
