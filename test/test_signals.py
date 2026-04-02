"""基于 rs_czsc 统一执行引擎的信号生成测试。"""

import pytest

import czsc
from czsc import mock
from czsc.core import format_standard_kline


def get_bars(symbol="000001", freq="日线", sdt="20200101", edt="20250101", seed=42):
    """生成用于信号测试的标准 RawBar 序列。"""
    df = mock.generate_symbol_kines(symbol=symbol, freq=freq, sdt=sdt, edt=edt, seed=seed)
    bars = format_standard_kline(df, freq=freq)
    return [bar for bar in bars if bar.vol > 0]


def test_generate_czsc_signals_returns_dataframe():
    bars = get_bars(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
    if len(bars) < 200:
        pytest.skip("数据不足，跳过测试")

    signals_config = [
        {"name": "czsc.signals.vol_single_ma_V230214", "freq": "30分钟", "di": 1, "ma_type": "SMA", "timeperiod": 5}
    ]
    df = czsc.generate_czsc_signals(bars, signals_config=signals_config, sdt="20210101", df=True)

    assert not df.empty
    assert "symbol" in df.columns
    assert "dt" in df.columns
    assert any(col.startswith("30分钟_D1VOL#SMA#5_分类V230214") for col in df.columns)


def test_generate_czsc_signals_returns_records():
    bars = get_bars(symbol="000001", freq="日线", sdt="20200101", edt="20250101")
    signals_config = [
        {"name": "czsc.signals.vol_single_ma_V230214", "freq": "日线", "di": 1, "ma_type": "SMA", "timeperiod": 5}
    ]
    records = czsc.generate_czsc_signals(bars, signals_config=signals_config, sdt="20210101", df=False)

    assert isinstance(records, list)
    assert records
    assert isinstance(records[0], dict)


def test_generate_czsc_signals_supports_multiple_configs():
    bars = get_bars(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
    if len(bars) < 200:
        pytest.skip("数据不足，跳过测试")

    signals_config = [
        {"name": "czsc.signals.vol_single_ma_V230214", "freq": "30分钟", "di": 1, "ma_type": "SMA", "timeperiod": 5},
        {"name": "czsc.signals.cxt_bi_base_V230228", "freq": "30分钟", "bi_init_length": 9},
    ]
    df = czsc.generate_czsc_signals(bars, signals_config=signals_config, sdt="20210101", df=True)
    signal_cols = [col for col in df.columns if len(col.split("_")) == 3]

    assert len(signal_cols) >= 2