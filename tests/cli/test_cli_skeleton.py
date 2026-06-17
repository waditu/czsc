from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


def test_app_help_lists_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in ["signals", "analyze", "backtest", "research", "data", "plot", "bench", "schema"]:
        assert name in result.output
