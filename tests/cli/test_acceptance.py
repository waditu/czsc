"""端到端验收：模拟 LLM 用 schema 发现 → 调用核心命令全链路。"""

import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_schema_then_call_chain(tmp_path, position_file):
    # 1. schema 自发现
    schema = json.loads(runner.invoke(app, ["schema", "--json"]).stdout)
    cmds = {c["command"] for c in schema}
    assert {"czsc signals list", "czsc analyze", "czsc backtest", "czsc data mock"} <= cmds

    # 2. 造数
    csv = tmp_path / "k.csv"
    r = runner.invoke(
        app,
        [
            "data",
            "mock",
            "--symbol",
            "000001",
            "--freq",
            "30分钟",
            "--sdt",
            "20200101",
            "--edt",
            "20240101",
            "-o",
            str(csv),
        ],
    )
    assert r.exit_code == 0

    # 3. analyze
    a = json.loads(runner.invoke(app, ["analyze", str(csv), "--freq", "30分钟", "--json"]).stdout)
    assert a["fx_list"] and a["bi_list"]

    # 4. backtest
    b = json.loads(runner.invoke(app, ["backtest", str(position_file), "--bars", str(csv), "--json"]).stdout)
    assert "年化收益" in b["portfolio"]
