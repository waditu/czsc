import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def _mock_csv(tmp_path):
    from czsc.mock import generate_symbol_kines

    p = tmp_path / "k.csv"
    generate_symbol_kines("000001", "30分钟", "20230101", "20240101").to_csv(p, index=False)
    return p


def test_analyze_json_has_fx_and_bi(tmp_path):
    p = _mock_csv(tmp_path)
    r = runner.invoke(app, ["analyze", str(p), "--freq", "30分钟", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert data["symbol"] == "000001"
    assert len(data["fx_list"]) > 0
    assert len(data["bi_list"]) > 0
    assert {"dt", "mark", "fx"} <= set(data["fx_list"][0])
    assert {"sdt", "edt", "direction", "high", "low"} <= set(data["bi_list"][0])
