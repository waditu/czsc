import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_signals_list_json_has_entries():
    r = runner.invoke(app, ["signals", "list", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 100
    assert {"name", "param_template", "category", "namespace"} <= set(data[0])


def test_signals_doc_known_name():
    listing = json.loads(runner.invoke(app, ["signals", "list", "--json"]).stdout)
    name = listing[0]["name"]
    r = runner.invoke(app, ["signals", "doc", name, "--json"])
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)
    assert doc["name"] == name
    assert "param_template" in doc


def test_signals_doc_unknown_name_fails():
    r = runner.invoke(app, ["signals", "doc", "不存在的信号xyz", "--json"])
    assert r.exit_code != 0
    assert json.loads(r.stderr)["error"]["message"]
