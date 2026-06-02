import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_research_config_derives():
    r = runner.invoke(app, ["research", "config", "30分钟_D1_表里关系V230101_向上_任意_任意_0", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert "signals_config" in data and "freqs" in data
    assert data["freqs"] == ["30分钟"]
