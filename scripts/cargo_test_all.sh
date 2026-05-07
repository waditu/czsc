#!/usr/bin/env bash
# Run all Rust workspace tests on the business crates.
#
# czsc-python is excluded because it is the cdylib aggregator that opts
# into pyo3/extension-module + abi3-py310. Cargo unifies features across
# the build graph, so including it in `cargo test --workspace` re-enables
# `extension-module` for the business crates' lib tests, where pyo3 then
# refuses to link against libpython. The published wheel is exercised
# end-to-end by the Python pytest suite (test/smoke + test/unit), so
# excluding the cdylib-only crate from `cargo test` doesn't reduce
# coverage.
#
# Design doc §6 Q1 verification: this script is what CI runs.

set -euo pipefail

# Resolve a Python interpreter for pyo3-build to bind libpython.
if [[ -z "${PYO3_PYTHON:-}" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        export PYO3_PYTHON="$(pwd)/.venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        export PYO3_PYTHON="$(command -v python3)"
    else
        echo "PYO3_PYTHON unset and no python interpreter found" >&2
        exit 1
    fi
fi

echo "Using PYO3_PYTHON=$PYO3_PYTHON"
exec cargo test --workspace --exclude czsc-python --no-fail-fast "$@"
