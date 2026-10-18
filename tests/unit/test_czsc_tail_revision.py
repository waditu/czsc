"""Natural same-timestamp revision regression, shared with the Rust core tests."""

from __future__ import annotations

import copy
import json
import pickle
from datetime import datetime
from pathlib import Path

import pytest

import czsc


def _fixture():
    path = Path(__file__).resolve().parents[2] / "crates/czsc-core/tests/fixtures/tail_revision_605169_20260924.json"
    data = json.loads(path.read_text())

    def raw(row, freq, index):
        return czsc.RawBar(
            data["symbol"],
            datetime.fromisoformat(row["dt"]),
            freq,
            row["open"],
            row["close"],
            row["high"],
            row["low"],
            row["volume"],
            row["amount"],
            index,
        )

    prefix = [raw(row, czsc.Freq.F30, i) for i, row in enumerate(data["prefix_30f"])]
    bg = czsc.BarGenerator("5分钟", ["30分钟"], market="A股")
    versions = []
    for i, row in enumerate(data["tail_native_5m"]):
        bg.update(raw(row, czsc.Freq.F5, i))
        versions.append(bg.bars["30分钟"][-1])
    return prefix, versions


def _assert_same_analysis(actual, expected):
    assert actual.bars_raw == expected.bars_raw
    assert actual.bars_ubi == expected.bars_ubi
    assert actual.bi_list == expected.bi_list
    assert actual.fx_list == expected.fx_list


@pytest.mark.parametrize("limit", [1, 50, 1000])
def test_tail_revision_retracts_temporary_bi(limit):
    prefix, versions = _fixture()
    c = czsc.CZSC(prefix, max_bi_num=limit, min_bi_len=6)
    c.update(versions[4])
    assert len(c.bi_list) == 1
    assert (versions[4].high, versions[5].high) == (13.04, 13.05)
    for index in [5, 5, 0, 1, 2, 3, 4, 5]:
        c.update(versions[index])
        expected = czsc.CZSC(prefix + [versions[index]], max_bi_num=limit, min_bi_len=6)
        _assert_same_analysis(c, expected)
    assert not c.bi_list


@pytest.mark.parametrize("restore", [copy.copy, copy.deepcopy, lambda c: pickle.loads(pickle.dumps(c))])
def test_tail_revision_after_copy_or_pickle_preserves_pending_state(restore):
    prefix, versions = _fixture()
    original = czsc.CZSC(prefix + [versions[4]], max_bi_num=1, min_bi_len=6)
    assert len(original.bi_list) == 1
    restored = restore(original)
    _assert_same_analysis(restored, original)
    for index in [5, 4, 5]:
        restored.update(versions[index])
        expected = czsc.CZSC(prefix + [versions[index]], max_bi_num=1, min_bi_len=6)
        _assert_same_analysis(restored, expected)
    assert len(original.bi_list) == 1


@pytest.mark.parametrize("restore", [copy.copy, copy.deepcopy, lambda c: pickle.loads(pickle.dumps(c))])
def test_tail_revision_after_copy_or_pickle_preserves_pruned_state(restore):
    from czsc.mock import generate_symbol_kines

    data = generate_symbol_kines("000001", "30分钟", "20240101", "20240201", seed=42)
    bars = czsc.format_standard_kline(data, freq=czsc.Freq.F30)
    original = czsc.CZSC(bars, max_bi_num=1, min_bi_len=6)
    assert len(original.bars_raw) < len(bars)
    restored = restore(original)
    _assert_same_analysis(restored, original)
    last = bars[-1]
    revised = czsc.RawBar(
        last.symbol,
        last.dt,
        last.freq,
        last.open,
        last.close,
        last.high + 3,
        last.low - 3,
        last.vol,
        last.amount,
        last.id,
    )
    for version in [revised, last, revised]:
        restored.update(version)
        expected = czsc.CZSC(bars[:-1] + [version], max_bi_num=1, min_bi_len=6)
        _assert_same_analysis(restored, expected)


def test_setstate_rejects_empty_rust_state_without_mutating_analyzer():
    prefix, versions = _fixture()
    c = czsc.CZSC(prefix + [versions[4]], max_bi_num=1, min_bi_len=6)
    before = c.__getstate__()
    empty = json.loads(before)
    empty.update(bars_raw=[], bars_ubi=[], bi_list=[])
    empty["tail_update"] = {"bars_ubi": [], "bi_count": 0, "removed_bi": None, "pruned_bis": [], "pruned_raw": []}

    with pytest.raises(ValueError, match="non-empty bars_raw"):
        c.__setstate__(json.dumps(empty).encode())
    assert c.__getstate__() == before
    restored = pickle.loads(pickle.dumps(c))
    restored.update(versions[5])
    _assert_same_analysis(restored, czsc.CZSC(prefix + [versions[5]], max_bi_num=1, min_bi_len=6))
