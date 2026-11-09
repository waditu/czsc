"""Natural QMT opening-minute regression shared with the Rust utility tests.

605169.SH, 2026-09-29: yuan prices/amounts and share volumes. These are recorded
market bars, not synthetic fixture prices; 09:30 carries the opening auction.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

import czsc


def _bars():
    path = Path(__file__).resolve().parents[2] / "crates/czsc-utils/tests/fixtures/qmt_opening_1m.csv"
    with path.open() as stream:
        return [
            czsc.RawBar(
                "605169.SH",
                datetime.fromisoformat(row["dt"]),
                czsc.Freq.F1,
                *[float(row[k]) for k in ("open", "close", "high", "low", "volume", "amount")],
                i,
            )
            for i, row in enumerate(csv.DictReader(stream))
        ]


@pytest.mark.parametrize("market", ["A股", "默认", "期货"])
def test_opening_minutes_keep_identity_and_aggregate_once(market):
    bars = _bars()
    bg = czsc.BarGenerator("1分钟", ["5分钟", "30分钟"], market=market)
    for bar in bars:
        bg.update(bar)
        bg.update(bar)
    assert bg.bars["1分钟"] == bars
    for freq, hour, minute in [("5分钟", 9, 35), ("30分钟", 10, 0)]:
        derived = bg.bars[freq]
        assert len(derived) == (1 if market == "A股" else 2)
        if market != "A股":
            assert derived[0].dt == datetime(2026, 9, 29, 9, 30)
            assert (derived[0].vol, derived[0].amount) == (11700, 153270)
        last = derived[-1]
        assert last.dt == datetime(2026, 9, 29, hour, minute)
        assert (last.open, last.high, last.low, last.close) == (13.10, 13.14, 12.98, 13.09)
        assert (last.vol, last.amount) == ((474500, 6192515) if market == "A股" else (462800, 6039245))


@pytest.mark.parametrize("freq,stamp", [(czsc.Freq.F1, "2026-09-29T09:31:20"), (czsc.Freq.F5, "2026-09-29T09:36:00")])
def test_minute_base_keeps_supplied_label_without_changing_derived_calendar(freq, stamp):
    source = _bars()[0]
    bar = czsc.RawBar(
        source.symbol,
        datetime.fromisoformat(stamp),
        freq,
        source.open,
        source.close,
        source.high,
        source.low,
        source.vol,
        source.amount,
        0,
    )
    bg = czsc.BarGenerator(str(freq), ["30分钟"], market="A股")
    bg.update(bar)
    assert bg.bars[str(freq)][0].dt == bar.dt
    assert bg.bars["30分钟"][0].dt == datetime(2026, 9, 29, 10, 0)


@pytest.mark.parametrize(
    "freq,day", [(czsc.Freq.D, "2026-09-29"), (czsc.Freq.W, "2026-10-02"), (czsc.Freq.M, "2026-09-30")]
)
def test_calendar_bases_keep_existing_date_normalization(freq, day):
    source = _bars()[0]
    bar = czsc.RawBar(
        source.symbol,
        datetime(2026, 9, 29, 15),
        freq,
        source.open,
        source.close,
        source.high,
        source.low,
        source.vol,
        source.amount,
        0,
    )
    bg = czsc.BarGenerator(str(freq), ["年线"], market="A股")
    bg.update(bar)
    assert bg.bars[str(freq)][0].dt == datetime.fromisoformat(day)
    assert bg.bars["年线"][0].dt == datetime(2026, 12, 31)
