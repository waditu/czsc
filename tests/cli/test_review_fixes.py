"""回归测试：覆盖 /code-review 发现并修复的缺陷。"""

import json

from typer.testing import CliRunner

from czsc.cli import _io, app

runner = CliRunner()


def _bars_csv(tmp_path, symbol="000001", sdt="20200101", edt="20240101"):
    from czsc.mock import generate_symbol_kines

    p = tmp_path / f"{symbol}.csv"
    generate_symbol_kines(symbol, "30分钟", sdt, edt).to_csv(p, index=False)
    return p


def test_load_bars_df_coerces_numeric_to_float(tmp_path):
    """mock CSV 的 vol 是 int64，load_bars_df 必须转 float，否则 research 透传 Rust 会崩。"""
    p = _bars_csv(tmp_path, sdt="20240101", edt="20240301")
    df = _io.load_bars_df(str(p))
    for col in ["open", "close", "high", "low", "vol", "amount"]:
        assert str(df[col].dtype) == "float64", col


def test_research_run_with_mock_csv(tmp_path, position_file):
    """data mock → research run 全链路：曾因 int64 vol 崩 Polars。"""
    from czsc import CzscStrategyBase, Position

    bars_csv = _bars_csv(tmp_path)
    pos = Position.from_json(position_file.read_text())

    class _S(CzscStrategyBase):
        @property
        def positions(self):
            return [pos]

    strat = _S(symbol="000001")
    strat_json = tmp_path / "strat.json"
    strat_json.write_text(
        json.dumps(
            {
                "symbol": "000001",
                "base_freq": strat.base_freq,
                "freqs": strat.freqs,
                "positions": [pos.dump()],
                "signals_config": strat.signals_config,
            },
            ensure_ascii=False,
        )
    )
    r = runner.invoke(app, ["research", "run", str(bars_csv), str(strat_json), "--json"])
    assert r.exit_code == 0, r.output
    assert "meta" in json.loads(r.stdout)


def test_data_quality_json_clean_on_bad_data(tmp_path):
    """含异常数据时 stdout 仍是纯 JSON（check_kline_quality 的 print 副作用被吞掉）。"""

    from czsc.mock import generate_symbol_kines

    df = generate_symbol_kines("000001", "30分钟", "20240101", "20240301")
    df.loc[df.index[0], "vol"] = -5  # 制造负成交量
    csv = tmp_path / "bad.csv"
    df.to_csv(csv, index=False)
    r = runner.invoke(app, ["data", "quality", str(csv), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)  # 不应抛 JSONDecodeError
    assert data["000001"]["volume_amount"]["n_bad_rows"] >= 1


def test_backtest_multi_symbol_labels_distinct(tmp_path, position_file):
    """多 symbol：每个 symbol 的标签用回测标的，而非 position 自带 symbol。"""
    import pandas as pd

    from czsc.mock import generate_symbol_kines

    a = generate_symbol_kines("AAAAAA", "30分钟", "20210101", "20240101")
    b = generate_symbol_kines("BBBBBB", "30分钟", "20210101", "20240101")
    csv = tmp_path / "two.csv"
    pd.concat([a, b], ignore_index=True).to_csv(csv, index=False)
    r = runner.invoke(app, ["backtest", str(position_file), "--bars", str(csv), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert set(data["symbols"]) == {"AAAAAA", "BBBBBB"}
    assert "品种数量" in data["portfolio"] or "年化收益" in data["portfolio"]
