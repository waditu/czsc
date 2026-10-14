import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".github/scripts/smoke_release_wheel.py"
WORKFLOW = ROOT / ".github/workflows/python-publish.yml"


def test_installed_wheel_runs_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--expected-version", "2.0.0", "--expected-machine", platform.machine()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS installed release wheel" in result.stdout


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
        [sys.executable, str(SCRIPT), "--expected-version", "2.0.0", "--expected-machine", "wrong-architecture"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "Runner architecture" in result.stderr


def test_release_smoke_covers_native_arm_and_intel_runners():
    workflow = WORKFLOW.read_text()
    smoke = workflow.split("  smoke-test:", 1)[1].split("  publish-to-testpypi:", 1)[0]
    assert "ubuntu-24.04-arm" in smoke
    assert "macos-15-intel" in smoke
    assert 'python: ["3.10", "3.11", "3.12", "3.13"]' in smoke
    assert "smoke-musllinux:" in smoke
    assert "python:${{ matrix.python }}-alpine" in smoke
    assert "--no-deps" not in smoke


def test_upload_jobs_still_require_explicit_publish_events():
    workflow = WORKFLOW.read_text()
    assert (
        "if: github.event_name == 'workflow_dispatch' && github.event.inputs.publish_to_testpypi == 'true'" in workflow
    )
    assert workflow.count("if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')") == 2
    assert workflow.count("needs: [build-wheels, build-sdist, smoke-test, smoke-musllinux]") == 2
