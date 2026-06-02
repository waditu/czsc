import json

import pytest
from typer.testing import CliRunner

from czsc.cli import app

runner = CliRunner()


@pytest.mark.slow
def test_bench_json_reports_throughput():
    r = runner.invoke(app, ["bench", "--years", "1", "--freq", "30分钟", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.stdout)
    assert data["czsc_construct"]["bars_per_sec"] > 0
