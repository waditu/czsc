import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("configured", [False, True])
def test_importing_tests_preserves_czsc_environment(configured):
    environment = os.environ.copy()
    for name in ("CZSC_MIN_BI_LEN", "CZSC_BI_CHANGE_TH"):
        environment.pop(name, None)
        if configured:
            environment[name] = "external-value"
    code = "import os; before = dict(os.environ); import tests; assert dict(os.environ) == before"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_default_environment_tests_restore_external_configuration():
    environment = os.environ.copy()
    for name in (
        "CZSC_VERBOSE",
        "czsc_verbose",
        "CZSC_MIN_BI_LEN",
        "czsc_min_bi_len",
        "CZSC_MAX_BI_NUM",
        "czsc_max_bi_num",
    ):
        environment[name] = "9"
    cases = [
        "tests/test_envs.py::TestGetVerbose::test_default_false",
        "tests/test_envs.py::TestGetVerbose::test_parameter_override",
        "tests/test_envs.py::TestGetMinBiLen::test_default_value",
        "tests/test_envs.py::TestGetMaxBiNum::test_default_value",
    ]
    code = (
        "import os, pytest; "
        "before = {name: value for name, value in os.environ.items() if name.lower().startswith('czsc_')}; "
        f"status = pytest.main({cases!r}); assert status == 0; "
        "after = {name: value for name, value in os.environ.items() if name.lower().startswith('czsc_')}; "
        "assert after == before, (before, after)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
