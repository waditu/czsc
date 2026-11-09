"""A higher-frequency input cannot supply lower-frequency observations."""

import copy
import pickle
from datetime import datetime

import pytest

import czsc
from czsc.mock import generate_symbol_kines
from czsc.research import run_research
from czsc.traders import generate_czsc_signals


@pytest.mark.parametrize(
    "base,target",
    [
        (czsc.Freq.F1, czsc.Freq.Tick),
        (czsc.Freq.F5, czsc.Freq.F1),
        (czsc.Freq.F30, czsc.Freq.F5),
        (czsc.Freq.D, czsc.Freq.F360),
        (czsc.Freq.W, czsc.Freq.D),
        (czsc.Freq.M, czsc.Freq.W),
        (czsc.Freq.S, czsc.Freq.M),
        (czsc.Freq.Y, czsc.Freq.S),
    ],
)
def test_rejects_target_below_base_for_enum_and_string_arguments(base, target):
    for b, f in [(base, target), (str(base), str(target))]:
        with pytest.raises(Exception, match=f"目标周期 {target} 不能小于基础周期 {base}"):
            czsc.BarGenerator(b, ["年线", f], market="A股")


@pytest.mark.parametrize(
    "base,target", [("3分钟", "5分钟"), ("6分钟", "10分钟"), ("20分钟", "30分钟"), ("240分钟", "360分钟")]
)
def test_rejects_minute_targets_that_split_base_bars(base, target):
    with pytest.raises(Exception, match=f"目标分钟周期 {target} 必须是基础周期 {base} 的整数倍"):
        czsc.BarGenerator(base, [target], market="A股")


def test_daily_base_keeps_equal_and_higher_aggregation_through_pickle():
    frame = generate_symbol_kines("000001", "日线", "20260105", "20260109", seed=42).iloc[:2]
    bars = czsc.format_standard_kline(frame, freq=czsc.Freq.D)
    assert len(bars) == 2
    bg = czsc.BarGenerator("日线", ["日线", "周线", "月线", "季线", "年线"], market="A股")
    bg.update(bars[0])
    restored = pickle.loads(pickle.dumps(bg))
    for owner in [bg, restored]:
        owner.update(bars[1])
        assert len(owner.bars["日线"]) == 2
        for freq, end in [
            ("周线", datetime(2026, 1, 9)),
            ("月线", datetime(2026, 1, 31)),
            ("季线", datetime(2026, 3, 31)),
            ("年线", datetime(2026, 12, 31)),
        ]:
            assert len(owner.bars[freq]) == 1
            output = owner.bars[freq][0]
            assert output.dt == end
            assert (output.open, output.high, output.low, output.close) == (
                bars[0].open,
                max(b.high for b in bars),
                min(b.low for b in bars),
                bars[-1].close,
            )
            assert (output.vol, output.amount) == (sum(b.vol for b in bars), sum(b.amount for b in bars))
    assert bg.bars == restored.bars


@pytest.mark.parametrize("base,target", [("5分钟", "1分钟"), ("3分钟", "5分钟")])
def test_restoring_invalid_frequency_fails_without_mutating_existing_generator(base, target):
    bg = czsc.BarGenerator(base, ["30分钟"], market="A股")
    before = bg.__reduce__()
    invalid = copy.deepcopy(before[2])
    invalid["market"] = "默认"
    invalid["freq_bars"][target] = []
    with pytest.raises(Exception, match=f"目标.*{target}.*基础周期 {base}"):
        bg.__setstate__(invalid)
    assert bg.__reduce__() == before


@pytest.mark.parametrize(
    "config",
    [
        {"name": "tas_macd_bc_V230804", "freq": "1分钟"},
        # 联合信号的默认周期发现不在本次修复内，这里显式写出它实际使用的低周期。
        {"name": "cat_macd_V230518", "freq1": "5分钟", "freq2": "1分钟"},
    ],
)
def test_signal_generation_propagates_explicit_and_default_lower_frequency_errors(config):
    frame = generate_symbol_kines("000001", "5分钟", "20260105", "20260105", seed=42)
    bars = czsc.format_standard_kline(frame, freq=czsc.Freq.F5)
    with pytest.raises(ValueError, match="目标周期 1分钟 不能小于基础周期 5分钟"):
        generate_czsc_signals(bars, [config], init_n=1)


@pytest.mark.parametrize(
    "config",
    [
        {"name": "tas_macd_bc_V230804", "freq": "1分钟"},
        {"name": "cat_macd_V230518", "freq1": "5分钟", "freq2": "1分钟"},
    ],
)
def test_compiled_research_propagates_explicit_and_default_lower_frequency_errors(config):
    frame = generate_symbol_kines("000001", "5分钟", "20260105", "20260105", seed=42)
    frame["vol"] = frame["vol"].astype(float)
    strategy = {
        "symbol": "000001",
        "base_freq": "5分钟",
        "signals_config": [config],
        "positions": [
            {
                "name": "inactive",
                "symbol": "000001",
                "opens": [],
                "exits": [],
                "interval": 0,
                "timeout": 1,
                "stop_loss": 0.0,
                "T0": False,
            }
        ],
        "market": "A股",
    }
    with pytest.raises(RuntimeError, match="目标周期 1分钟 不能小于基础周期 5分钟"):
        run_research(frame, strategy)
