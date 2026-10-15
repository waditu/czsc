import platform
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".github/scripts/smoke_release_wheel.py"
WORKFLOW = ROOT / ".github/workflows/python-publish.yml"


@pytest.mark.parametrize("job", ["smoke-test", "smoke-musllinux"])
def test_workflow_version_command_reads_utf8_under_windows_default(job, monkeypatch, capsys):
    workflow = WORKFLOW.read_text(encoding="utf-8")
    section = workflow.split(f"  {job}:", 1)[1].split("\n  #", 1)[0].split("\n  smoke-musllinux:", 1)[0]
    command = re.search(r"VERSION=\$\(python3? -c '(.*?)'\)", section).group(1)
    original_read_text = Path.read_text

    def read_with_windows_default(path, encoding=None, errors=None):
        return original_read_text(path, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(Path, "read_text", read_with_windows_default)
    exec(command, {})
    assert capsys.readouterr().out.strip() == "1.0.2"


def test_installed_wheel_runs_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--expected-version", "1.0.2", "--expected-machine", platform.machine()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS installed release wheel" in result.stdout
    assert "migrated signal contract" in result.stdout


def test_incorrect_release_version_is_rejected(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--expected-version", "0.0.0", "--expected-machine", platform.machine()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "Installed version" in result.stderr


def test_wrong_architecture_is_rejected(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--expected-version", "1.0.2", "--expected-machine", "wrong-architecture"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "Runner architecture" in result.stderr


def test_release_smoke_covers_native_arm_and_intel_runners():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    smoke = workflow.split("  smoke-test:", 1)[1].split("  publish-to-testpypi:", 1)[0]
    assert "ubuntu-24.04-arm" in smoke
    assert "macos-15-intel" in smoke
    assert 'python: ["3.10", "3.11", "3.12", "3.13"]' in smoke
    assert "smoke-musllinux:" in smoke
    assert "python:${{ matrix.python }}-alpine" in smoke
    assert "--no-deps" not in smoke


def test_upload_jobs_still_require_explicit_publish_events():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert (
        "if: github.event_name == 'workflow_dispatch' && github.event.inputs.publish_to_testpypi == 'true'" in workflow
    )
    assert workflow.count("if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')") == 2
    assert workflow.count("needs: [build-wheels, build-sdist, smoke-test, smoke-musllinux]") == 2


def test_musl_full_install_provisions_source_build_tools_before_pip():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    musl = workflow.split("  smoke-musllinux:", 1)[1].split("  publish-to-testpypi:", 1)[0]
    packages = re.search(r"apk add --no-cache ([^\n]+)", musl)
    assert packages is not None, "Alpine must provision wbt source-build prerequisites"
    assert {"build-base", "libgcc", "libstdc++", "rustup", "pkgconf", "openssl-dev"} <= set(packages.group(1).split())
    assert musl.index("apk add") < musl.index("rustup-init -y --profile minimal --default-toolchain stable")
    assert musl.index("cargo --version") < musl.index("python -m venv") < musl.index("-m pip install")
    assert 'export PATH="$HOME/.cargo/bin:$PATH"' in musl
    assert "CARGO_BUILD_JOBS=2" in musl
    assert "sh -ec" in musl
    assert "--no-cache-dir --index-url https://pypi.org/simple" in musl
    assert musl.index("-m pip install") < musl.index("-m pip check") < musl.index("/smoke/smoke_release_wheel.py")
