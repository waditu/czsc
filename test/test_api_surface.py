from __future__ import annotations

import ast
from pathlib import Path

import czsc


ROOT_DIR = Path(__file__).resolve().parents[1]


def _read_dunder_all(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    raise AssertionError(f"__all__ not found in {path}")


def test_root_api_surface_retains_supported_shortcuts():
    expected = {
        "CZSC",
        "Freq",
        "RawBar",
        "CzscTrader",
        "SignalsParser",
        "DataClient",
        "DiskCache",
        "mock",
        "svc",
        "CzscStrategyBase",
        "KlineChart",
        "generate_backtest_report",
    }
    missing = sorted(name for name in expected if not hasattr(czsc, name))
    assert not missing


def test_root_api_surface_drops_removed_legacy_exports():
    removed = {
        "CTAResearch",
        "DummyBacktest",
        "OpensOptimize",
        "ExitsOptimize",
        "PairsPerformance",
        "sensors",
        "rwc",
    }
    leaked = sorted(name for name in removed if hasattr(czsc, name))
    assert not leaked


def test_runtime_and_stub_dunder_all_are_aligned():
    runtime_all = sorted(czsc.__all__)
    stub_all = sorted(_read_dunder_all(ROOT_DIR / "czsc" / "__init__.pyi"))
    assert stub_all == runtime_all


def test_examples_do_not_reference_removed_workflows():
    removed_markers = ["CTAResearch", "OpensOptimize", "ExitsOptimize"]
    offenders: list[str] = []

    for path in (ROOT_DIR / "examples").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in removed_markers):
            offenders.append(path.name)

    assert offenders == []
