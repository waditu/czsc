"""human 模式（非 --json）渲染路径覆盖：确认退出码 0 且关键文本出现。"""

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def _bars_csv(tmp_path, symbol="000001"):
    from czsc.mock import generate_symbol_kines

    p = tmp_path / f"{symbol}.csv"
    generate_symbol_kines(symbol, "30分钟", "20200101", "20240101").to_csv(p, index=False)
    return p


def test_signals_list_human():
    r = runner.invoke(app, ["signals", "list"])
    assert r.exit_code == 0, r.output
    assert "共" in r.output and "个信号" in r.output


def test_signals_doc_human():
    listing = runner.invoke(app, ["signals", "list", "--json"])
    import json

    name = json.loads(listing.stdout)[0]["name"]
    r = runner.invoke(app, ["signals", "doc", name])
    assert r.exit_code == 0, r.output
    assert "参数模板" in r.output


def test_analyze_human(tmp_path):
    p = _bars_csv(tmp_path)
    r = runner.invoke(app, ["analyze", str(p), "--freq", "30分钟"])
    assert r.exit_code == 0, r.output
    assert "分型=" in r.output and "笔=" in r.output


def test_data_quality_human(tmp_path):
    p = _bars_csv(tmp_path)
    r = runner.invoke(app, ["data", "quality", str(p)])
    assert r.exit_code == 0, r.output
    assert "[000001]" in r.output


def test_backtest_human(tmp_path, position_file):
    p = _bars_csv(tmp_path)
    r = runner.invoke(app, ["backtest", str(position_file), "--bars", str(p)])
    assert r.exit_code == 0, r.output
    assert "组合绩效" in r.output and "年化收益" in r.output


def test_schema_human():
    r = runner.invoke(app, ["schema"])
    assert r.exit_code == 0, r.output
    assert "czsc backtest" in r.output


def test_bench_human():
    r = runner.invoke(app, ["bench", "--years", "1", "--freq", "30分钟"])
    assert r.exit_code == 0, r.output
    assert "bars/s" in r.output
