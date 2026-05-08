#!/usr/bin/env bash
# Phase B.1 — RED test: workspace must contain 9 named crates and build cleanly.
# See docs/superpowers/specs/2026-05-03-rust-czsc-migration-design.md §1, §2.
set -euo pipefail

required=(
  czsc-core
  czsc-utils
  czsc-ta
  czsc-signals
  czsc-trader
  czsc-signal-macros
  error-macros
  error-support
  czsc-python
)

echo "[1/3] Checking crate file layout..."
for c in "${required[@]}"; do
  test -f "crates/$c/Cargo.toml" || { echo "  MISSING: crates/$c/Cargo.toml"; exit 1; }
  test -f "crates/$c/src/lib.rs" || { echo "  MISSING: crates/$c/src/lib.rs"; exit 1; }
done
echo "  OK: 9 crate file layouts present"

echo "[2/3] Checking cargo workspace metadata..."
cargo metadata --format-version 1 --no-deps 2>/dev/null \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
members = {pkg['name'] for pkg in data['packages']}
required = set('${required[*]}'.split())
missing = required - members
if missing:
    print(f'  MISSING from workspace: {sorted(missing)}', file=sys.stderr)
    sys.exit(1)
print(f'  OK: workspace registers {len(members)} crate(s)')
"

echo "[3/3] Running cargo build --workspace..."
cargo build --workspace --quiet
echo "  OK: cargo build --workspace passed"
