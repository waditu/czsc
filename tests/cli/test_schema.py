import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_schema_json_lists_commands():
    r = runner.invoke(app, ["schema", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    cmds = {c["command"] for c in data}
    assert "czsc signals list" in cmds
    assert "czsc backtest" in cmds
    entry = next(c for c in data if c["command"] == "czsc signals list")
    assert entry["params"]
