# Retained API Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the retained public API surface across `czsc/__init__.py`, `czsc/__init__.pyi`, `README.md`, and shipped examples so they all describe the same currently-supported package surface.

**Architecture:** Treat `czsc/__init__.py` as the runtime source of truth, add a small contract test that locks in the retained root-level API, then make the type stub, README quick start, and examples match that surface. Remove or rewrite examples that still reference deleted optimize / CTA research workflows instead of reintroducing those capabilities.

**Tech Stack:** Python, pytest, package stubs (`.pyi`), Markdown docs

---

### Task 1: Lock The Retained Root API Surface

**Files:**
- Create: `test/test_api_surface.py`
- Modify: `czsc/__init__.py`

- [ ] **Step 1: Write the failing contract test**

```python
import czsc


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest test\test_api_surface.py -q`
Expected: FAIL because the current root package still leaks at least some removed legacy names through docs / stubs drift or missing checks.

- [ ] **Step 3: Adjust runtime exports to the retained surface**

```python
# Keep only supported, high-frequency shortcuts in __all__
# Keep lazy attrs/modules only for supported retained entry points
# Remove root-level legacy names that no longer exist in this trimmed codebase
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest test\test_api_surface.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add test/test_api_surface.py czsc/__init__.py
git commit -m "test: lock retained root api surface"
```

### Task 2: Mirror Runtime Exports In The Type Stub

**Files:**
- Modify: `czsc/__init__.pyi`

- [ ] **Step 1: Write the stub alignment target**

```python
# __init__.pyi must expose the same retained names as __init__.py
# No removed optimize / sensors / calendar / py fallback symbols remain here
```

- [ ] **Step 2: Update the stub to mirror the runtime surface**

```python
# Keep imports and __all__ entries only for retained runtime symbols
# Remove stale names such as CTAResearch, DummyBacktest, OpensOptimize,
# ExitsOptimize, PairsPerformance, sensors, rwc, calendar helpers, and py-only helpers
```

- [ ] **Step 3: Run targeted import verification**

Run: `.\.venv\Scripts\python.exe -m pytest test\test_import_performance.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add czsc/__init__.pyi
git commit -m "refactor: align root stub with retained api"
```

### Task 3: Rewrite README Quick Start Around The Retained Surface

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace stale top-level usage guidance**

```md
## Retained API Surface

The root package keeps a compact set of high-frequency shortcuts:
- core objects and enums
- trader entry points
- common utils and report helpers
- lazy modules: `mock`, `svc`, `fsa`, `aphorism`, `cwc`

Removed legacy workflows are no longer documented from the root package.
```

- [ ] **Step 2: Add a minimal, accurate quick-start import example**

```python
import czsc
from czsc import CZSC, Freq, RawBar, format_standard_kline
from czsc import CzscTrader, SignalsParser
from czsc.mock import generate_symbol_kines
```

- [ ] **Step 3: Link to the retained API rules**

```md
See `docs/RETAINED_API.md` for the root package shortcut list and recommended submodule imports.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: refresh readme for retained api surface"
```

### Task 4: Clean Example Entry Points

**Files:**
- Create: `docs/RETAINED_API.md`
- Modify: `examples/use_backtest_report.py`
- Modify: `examples/use_html_report_builder.py`
- Delete: `examples/use_optimize.py`
- Delete: `examples/use_cta_research.py`

- [ ] **Step 1: Document the retained root imports**

```md
# Retained API

## Root-level shortcuts
- core objects
- trader entry points
- selected utils
- retained lazy modules / attrs

## Import from submodules instead
- reporting helpers
- plotting helpers
- specialized data / analysis / IO helpers
```

- [ ] **Step 2: Rewrite examples to import only retained public symbols**

```python
# use_backtest_report.py
from czsc import generate_backtest_report
from czsc.utils.backtest_report import generate_pdf_backtest_report

# use_html_report_builder.py
from czsc import mock
from czsc.utils.html_report_builder import HtmlReportBuilder
from czsc import generate_backtest_report
```

- [ ] **Step 3: Remove examples that only demonstrate deleted workflows**

```text
Delete examples/use_optimize.py
Delete examples/use_cta_research.py
```

- [ ] **Step 4: Run a focused regression slice**

Run: `.\.venv\Scripts\python.exe -m pytest test\test_import_performance.py test\test_backtest_report.py test\test_html_report_builder.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/RETAINED_API.md README.md examples/use_backtest_report.py examples/use_html_report_builder.py examples/use_optimize.py examples/use_cta_research.py
git commit -m "docs: unify examples around retained api"
```

### Task 5: Final Verification

**Files:**
- Modify: `czsc/__init__.py`
- Modify: `czsc/__init__.pyi`
- Modify: `README.md`
- Modify: `examples/use_backtest_report.py`
- Modify: `examples/use_html_report_builder.py`
- Modify: `docs/RETAINED_API.md`
- Modify: `test/test_api_surface.py`

- [ ] **Step 1: Run the focused retained-surface checks**

Run: `.\.venv\Scripts\python.exe -m pytest test\test_api_surface.py test\test_import_performance.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `.\.venv\Scripts\python.exe -m pytest -o addopts="-q"`
Expected: PASS

- [ ] **Step 3: Review diff**

Run: `git diff --stat HEAD~1..HEAD`
Expected: shows runtime exports, stubs, docs, and examples converging without reintroducing deleted modules

- [ ] **Step 4: Commit**

```bash
git add czsc/__init__.py czsc/__init__.pyi README.md docs/RETAINED_API.md examples/use_backtest_report.py examples/use_html_report_builder.py test/test_api_surface.py
git commit -m "refactor: unify retained api surface"
```
