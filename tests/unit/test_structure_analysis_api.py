from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from czsc import (
    BI,
    CZSC,
    FX,
    Direction,
    Freq,
    Mark,
    NewBar,
    RawBar,
    check_gap_info,
    create_fake_bis,
    format_standard_kline,
    get_zs_seq,
    is_bis_down,
    is_bis_up,
    is_symmetry_zs,
)
from czsc.mock import generate_symbol_kines


def _fx(dt: datetime, mark: Mark, price: float) -> FX:
    high, low = (price, price - 1) if mark == Mark.G else (price + 1, price)
    return FX("000001", dt, mark, high, low, price, [])


def _bi(dt: datetime, start: float, end: float) -> BI:
    direction, mark_a, mark_b = (Direction.Up, Mark.D, Mark.G) if end > start else (Direction.Down, Mark.G, Mark.D)
    fx_a = _fx(dt, mark_a, start)
    fx_b = _fx(dt + timedelta(minutes=10), mark_b, end)
    bar = NewBar(
        "000001",
        dt,
        Freq.F30,
        (start + end) / 2,
        (start + end) / 2,
        max(start, end),
        min(start, end),
        100,
        1000,
    )
    return BI("000001", direction, fx_a, fx_b, [fx_a, fx_b], [bar])


def test_structure_analysis_functions_are_callable_on_empty_inputs() -> None:
    assert create_fake_bis([]) == []
    assert get_zs_seq([]) == []
    assert not is_symmetry_zs([])
    assert not is_bis_up([])
    assert not is_bis_down([])
    assert check_gap_info([]) == []


def test_czsc_exposes_zs_list_property() -> None:
    assert hasattr(CZSC, "zs_list")


def test_create_fake_bis_rejects_non_alternating_fxs() -> None:
    dt = datetime(2024, 1, 1)
    fxs = [
        FX("000001", dt, Mark.G, 10, 9, 10, []),
        FX("000001", dt + timedelta(minutes=1), Mark.G, 11, 10, 11, []),
    ]
    with pytest.raises(ValueError, match="相邻分型标记必须不同"):
        create_fake_bis(fxs)


def test_create_fake_bis_returns_expected_values_for_valid_fxs() -> None:
    dt = datetime(2024, 1, 1)
    fake_bis = create_fake_bis([_fx(dt, Mark.D, 9), _fx(dt + timedelta(minutes=1), Mark.G, 12)])
    assert len(fake_bis) == 1
    assert fake_bis[0].direction == Direction.Up
    assert (fake_bis[0].high, fake_bis[0].low, fake_bis[0].power) == (12, 9, 3)


def test_zs_symmetry_and_trend_functions_on_non_empty_bis() -> None:
    dt = datetime(2024, 1, 1)
    symmetric = [
        _bi(dt, 12, 9),
        _bi(dt + timedelta(minutes=20), 9, 12),
        _bi(dt + timedelta(minutes=40), 12, 9),
    ]
    zss = get_zs_seq(symmetric)
    assert len(zss) == 1
    assert len(zss[0].bis) == 3
    assert is_symmetry_zs(symmetric, th=0.01)

    up = [
        _bi(dt, 9, 12),
        _bi(dt + timedelta(minutes=20), 12, 10),
        _bi(dt + timedelta(minutes=40), 10, 14),
    ]
    assert is_bis_up(up)
    assert not is_bis_down(up)

    down = [
        _bi(dt, 14, 10),
        _bi(dt + timedelta(minutes=20), 10, 12),
        _bi(dt + timedelta(minutes=40), 12, 8),
    ]
    assert is_bis_down(down)
    assert not is_bis_up(down)


def test_czsc_zs_list_matches_finished_bis_analysis() -> None:
    df = generate_symbol_kines("000001", "30分钟", sdt="20240101", edt="20240201", seed=42)
    c = CZSC(format_standard_kline(df, Freq.F30))
    expected = get_zs_seq(c.finished_bis)
    assert len(c.zs_list) == len(expected)
    assert [len(zs.bis) for zs in c.zs_list] == [len(zs.bis) for zs in expected]


def test_check_gap_info_returns_compatible_dicts() -> None:
    dt = datetime(2024, 1, 1)
    bars = [
        RawBar("000001", dt, Freq.F30, 9.5, 9.5, 10, 9, 100, 1000, 1),
        RawBar("000001", dt + timedelta(minutes=30), Freq.F30, 11.5, 11.5, 12, 11, 100, 1000, 2),
        RawBar("000001", dt + timedelta(minutes=60), Freq.F30, 10, 10, 11, 9.5, 100, 1000, 3),
    ]
    gaps = check_gap_info(bars)
    assert len(gaps) == 1
    assert gaps[0]["kind"] == "向上缺口"
    assert gaps[0]["cover"] == "已补"
    assert gaps[0]["sdt"].to_pydatetime() == dt
    assert gaps[0]["edt"].to_pydatetime() == dt + timedelta(minutes=30)
    assert gaps[0]["high"] == 11.0
    assert gaps[0]["low"] == 10.0
    assert gaps[0]["delta"] == 0.1


def test_check_gap_info_handles_down_gap_and_no_gap() -> None:
    dt = datetime(2024, 1, 1)
    down_gap = [
        RawBar("000001", dt, Freq.F30, 11.5, 11.5, 12, 11, 100, 1000, 1),
        RawBar("000001", dt + timedelta(minutes=30), Freq.F30, 9.5, 9.5, 10, 9, 100, 1000, 2),
        RawBar("000001", dt + timedelta(minutes=60), Freq.F30, 10.5, 10.5, 11.5, 9.5, 100, 1000, 3),
    ]
    gaps = check_gap_info(down_gap)
    assert len(gaps) == 1
    assert gaps[0]["kind"] == "向下缺口"
    assert gaps[0]["cover"] == "已补"

    no_gap = [
        RawBar("000001", dt, Freq.F30, 9.5, 9.5, 10, 9, 100, 1000, 1),
        RawBar("000001", dt + timedelta(minutes=30), Freq.F30, 10, 10, 10.5, 9.5, 100, 1000, 2),
    ]
    assert check_gap_info(no_gap) == []
