"""Joint indicators consume the same native per-frequency owner as kline signals."""

import pickle

import pytest

import czsc
from czsc.mock import generate_symbol_kines
from czsc.traders import derive_signals_freqs


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("cat_macd_V230518", ["1分钟", "5分钟"]),
        ("cat_macd_V230520", ["1分钟", "5分钟"]),
        ("cxt_zhong_shu_gong_zhen_V221221", ["60分钟", "日线"]),
    ],
)
def test_joint_signal_frequency_discovery_uses_signal_defaults(name, expected):
    assert derive_signals_freqs([{"name": name}]) == expected
    assert derive_signals_freqs([{"name": name, "freq1": "30分钟", "freq2": "5分钟"}]) == ["5分钟", "30分钟"]


@pytest.fixture(scope="module")
def bars():
    data = generate_symbol_kines("000001", "5分钟", "20260105", "20260301", seed=42)
    return czsc.format_standard_kline(data, freq=czsc.Freq.F5)[:1600]


def _configs():
    return [{"name": name, "freq1": "30分钟", "freq2": "5分钟"} for name in ["cat_macd_V230518", "cat_macd_V230520"]]


def _trader(prefix, configs):
    bg = czsc.BarGenerator("5分钟", ["30分钟"], market="A股", max_count=2000)
    for bar in prefix:
        bg.update(bar)
    return czsc.CzscTrader(bg, [], configs)


def _joint(signals):
    return {key: value for key, value in signals.items() if "_联立V" in key}


def test_cat_only_and_kline_plus_cat_produce_the_same_joint_values(bars):
    configs = _configs()
    combined = [
        {"name": name, "freq": freq}
        for freq in ["30分钟", "5分钟"]
        for name in ["tas_macd_bc_V230804", "tas_macd_base_V221028"]
    ] + configs
    cat = _trader(bars[:299], configs)
    mixed = _trader(bars[:299], combined)
    non_neutral = set()
    for bar in bars[299:]:
        cat.update(bar)
        mixed.update(bar)
        values = _joint(cat.s)
        assert len(values) == 2
        assert values == _joint(mixed.s)
        non_neutral.update(key for key, value in values.items() if not value.startswith("其他_"))
    assert len(non_neutral) == 2


def test_joint_dependencies_after_hot_restore_and_fresh_pickle(bars):
    configs = _configs()
    original = _trader(bars[:299], configs)
    for bar in bars[299:500]:
        original.update(bar)
    hot = czsc.CzscTrader.restore_state(original.dump_state())
    # Pickle intentionally reconstructs from BG/config; dump_state preserves warm caches.
    pickled = pickle.loads(pickle.dumps(original))
    fresh = _trader(bars[:500], configs)
    revised_high_tails = 0
    last_high_dt = original.kas["30分钟"].bars_raw[-1].dt
    for bar in bars[500:540]:
        for _ in range(2):
            for trader in [original, hot, pickled, fresh]:
                trader.update(bar)
            assert original.s == hot.s
            assert pickled.s == fresh.s
            assert len(_joint(hot.s)) == 2
        current = hot.kas["30分钟"].bars_raw[-1].dt
        revised_high_tails += current == last_high_dt
        last_high_dt = current
    assert revised_high_tails > 20
