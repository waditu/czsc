import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def _bars_csv(tmp_path, symbol="000001"):
    from czsc.mock import generate_symbol_kines

    p = tmp_path / f"{symbol}.csv"
    generate_symbol_kines(symbol, "30分钟", "20200101", "20240101").to_csv(p, index=False)
    return p


def test_backtest_with_bars_file_json(tmp_path, position_file):
    bars = _bars_csv(tmp_path)
    r = runner.invoke(app, ["backtest", str(position_file), "--bars", str(bars), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert "symbols" in data and "portfolio" in data
    assert "000001" in data["symbols"]
    assert "年化收益" in data["portfolio"]


def test_backtest_html_report(tmp_path, position_file):
    bars = _bars_csv(tmp_path)
    out = tmp_path / "report.html"
    r = runner.invoke(app, ["backtest", str(position_file), "--bars", str(bars), "--html", str(out), "--json"])
    assert r.exit_code == 0, r.output
    assert out.exists() and out.stat().st_size > 0


def test_backtest_requires_data_source(position_file):
    r = runner.invoke(app, ["backtest", str(position_file), "--json"])
    assert r.exit_code != 0
    assert json.loads(r.stderr)["error"]["message"]
