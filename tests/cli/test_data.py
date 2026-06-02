import json

from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_data_mock_writes_csv(tmp_path):
    out = tmp_path / "k.csv"
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
            "20240101",
            "--edt",
            "20240201",
            "-o",
            str(out),
        ],
    )
    assert r.exit_code == 0, r.output
    assert out.exists()
    import pandas as pd

    df = pd.read_csv(out)
    assert {"dt", "symbol", "open", "close", "high", "low", "vol", "amount"} <= set(df.columns)


def test_data_quality_json(tmp_path):
    csv = tmp_path / "k.csv"
    from czsc.mock import generate_symbol_kines

    generate_symbol_kines("000001", "30分钟", "20240101", "20240201").to_csv(csv, index=False)
    r = runner.invoke(app, ["data", "quality", str(csv), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert "000001" in data
