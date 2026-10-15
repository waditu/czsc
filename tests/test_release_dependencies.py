from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@pytest.mark.parametrize(
    ("lockfile", "package", "minimum"),
    [
        ("Cargo.lock", "pyo3", "0.29.0"),
        ("Cargo.lock", "quinn-proto", "0.11.15"),
        ("Cargo.lock", "xxhash-rust", "0.8.16"),
        ("uv.lock", "anyio", "4.14.2"),
        ("uv.lock", "urllib3", "2.8.0"),
        ("uv.lock", "jupyterlab", "4.5.11"),
        ("uv.lock", "notebook", "7.6.3"),
        ("uv.lock", "tornado", "6.5.9"),
        ("uv.lock", "cryptography", "50.0.0"),
        ("uv.lock", "soupsieve", "2.9.0"),
        ("uv.lock", "mistune", "3.3.3"),
        ("uv.lock", "setuptools", "83.0.0"),
    ],
)
def test_release_lock_excludes_reviewed_vulnerable_versions(lockfile, package, minimum):
    root = Path(__file__).resolve().parents[1]
    locked = tomllib.loads((root / lockfile).read_text())
    versions = [entry["version"] for entry in locked["package"] if entry["name"] == package]
    assert versions or package == "setuptools", f"Missing reviewed dependency: {package}"
    assert all(Version(version) >= Version(minimum) for version in versions), versions


def test_runtime_installs_require_patched_urllib3():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    requirements = [Requirement(value) for value in project["dependencies"]]
    urllib3 = next((requirement for requirement in requirements if requirement.name == "urllib3"), None)
    assert urllib3 is not None
    assert Version("2.7.0") not in urllib3.specifier
    assert Version("2.8.0") in urllib3.specifier


def test_release_102_workspace_and_exact_dependencies_are_consistent():
    root = Path(__file__).resolve().parents[1]
    workspace = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))["workspace"]
    version = workspace["package"]["version"]
    assert version == "1.0.2"
    internal = {
        name: dependency
        for name, dependency in workspace["dependencies"].items()
        if isinstance(dependency, dict) and "path" in dependency
    }
    assert len(internal) == 8
    for name, dependency in internal.items():
        assert dependency["version"] == f"={version}", name
    locked = tomllib.loads((root / "Cargo.lock").read_text(encoding="utf-8"))["package"]
    packages = {package["name"]: package for package in locked if package["name"] in {*internal, "czsc-python"}}
    assert len(packages) == 9
    assert all(package["version"] == version for package in packages.values())
    for manifest in (root / "crates").glob("*/Cargo.toml"):
        package = tomllib.loads(manifest.read_text(encoding="utf-8"))["package"]
        assert package["version"] == {"workspace": True}, manifest
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "version" in project["dynamic"]
    assert "version" not in project
