from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def _bars_csv(tmp_path):
    from czsc.mock import generate_symbol_kines

    p = tmp_path / "k.csv"
    generate_symbol_kines("000001", "30分钟", "20230101", "20240101").to_csv(p, index=False)
    return p


def test_plot_czsc_writes_html(tmp_path):
    p = _bars_csv(tmp_path)
    out = tmp_path / "c.html"
    r = runner.invoke(app, ["plot", "czsc", str(p), "--freq", "30分钟", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert out.exists() and out.stat().st_size > 0


def test_plot_signals_writes_html(tmp_path):
    p = _bars_csv(tmp_path)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('[{"name": "30分钟_D1_表里关系V230101_向上_任意_任意_0"}]')
    out = tmp_path / "s.html"
    r = runner.invoke(
        app,
        ["plot", "signals", str(p), "--signals-config", str(cfg), "--freq", "30分钟", "-o", str(out)],
    )
    assert r.exit_code == 0, r.output
    assert out.exists() and out.stat().st_size > 0
