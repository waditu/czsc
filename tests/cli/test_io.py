import json

import pytest
import typer

from czsc.cli import _io
from czsc.mock import generate_symbol_kines


def test_load_bars_df_csv(tmp_path):
    df = generate_symbol_kines("000001", "30分钟", "20240101", "20240105")
    p = tmp_path / "k.csv"
    df.to_csv(p, index=False)
    out = _io.load_bars_df(str(p))
    for col in ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]:
        assert col in out.columns


def test_load_bars_df_missing_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="缺少必需列"):
        _io.load_bars_df(str(p))


def test_emit_json(capsys):
    _io.emit({"k": 1}, json_out=True, human=lambda d: None)
    out = capsys.readouterr().out
    assert json.loads(out) == {"k": 1}


def test_fail_json_raises_exit(capsys):
    with pytest.raises(typer.Exit):
        _io.fail("boom", json_out=True, err_type="ValueError")
    err = capsys.readouterr().err
    assert json.loads(err)["error"]["message"] == "boom"


def test_freq_to_cn():
    assert _io.freq_to_cn("F30") == "30分钟"
    assert _io.freq_to_cn("30分钟") == "30分钟"
    assert _io.freq_to_cn("D") == "日线"
