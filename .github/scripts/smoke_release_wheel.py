import argparse
import hashlib
import importlib.metadata
import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from packaging.version import Version


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-machine", required=True)
    parser.add_argument("--wheel-dir", type=Path)
    arguments = parser.parse_args()
    installed_version = importlib.metadata.version("czsc")
    assert Version(installed_version) == Version(arguments.expected_version), f"Installed version: {installed_version}"
    aliases = {"arm64": "aarch64", "amd64": "x86_64"}
    actual_machine = platform.machine().lower()
    expected_machine = arguments.expected_machine.lower()
    assert aliases.get(actual_machine, actual_machine) == aliases.get(expected_machine, expected_machine), (
        f"Runner architecture: {actual_machine}, expected {expected_machine}"
    )

    import numpy as np
    import pandas as pd

    import czsc
    import czsc._native as native
    import czsc._native.ta as ta

    distribution = importlib.metadata.distribution("czsc")
    installed_package = Path(distribution.locate_file("czsc")).resolve()
    native_path = Path(native.__file__).resolve()
    assert Path(czsc.__file__).resolve().parent == installed_package
    assert native_path.parent == installed_package
    assert installed_package.is_relative_to(Path(sys.prefix).resolve()), installed_package
    assert native_path.suffix in (".so", ".pyd", ".dylib"), native_path
    assert Version(czsc.__version__) == Version(arguments.expected_version)
    if arguments.wheel_dir:
        wheels = list(arguments.wheel_dir.glob("czsc-*.whl"))
        assert len(wheels) == 1, wheels
        with ZipFile(wheels[0]) as archive:
            assert archive.read("czsc/" + native_path.name) == native_path.read_bytes()
        print("wheel:", wheels[0].name, hashlib.sha256(wheels[0].read_bytes()).hexdigest())

    bars = [
        czsc.RawBar(
            symbol="SMOKE",
            id=index,
            dt=datetime(2024, 1, 1) + timedelta(minutes=index),
            freq=czsc.Freq.F1,
            open=10.0 + index,
            close=10.5 + index,
            high=11.0 + index,
            low=9.0 + index,
            vol=100.0,
            amount=1000.0,
        )
        for index in range(12)
    ]
    analysis = czsc.CZSC(bars)
    assert analysis.symbol == "SMOKE" and analysis.freq == czsc.Freq.F1
    assert analysis.bars_raw[-1].id == 11
    signals = native.signals.call_signal("bar_operate_span_V221111", analysis)
    assert len(signals) == 1
    assert signals[0].key == "1分钟_T0935#1450_时间区间V221111"
    signal_text = f"{signals[0].key}_{signals[0].value}"
    config = czsc.get_signals_config([signal_text])
    assert config == [{"name": "bar_operate_span_V221111", "freq": "1分钟", "t1": "0935", "t2": "1450"}], config
    assert czsc.get_signals_config([signal_text.replace("时间区间V221111", "时间区间")]) == []
    np.testing.assert_allclose(ta.sma(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 3), [np.nan, np.nan, 2.0, 3.0, 4.0])
    for unit in ("s", "ms", "us", "ns"):
        frame = pd.DataFrame(
            {
                "dt": pd.date_range("2022-01-03", periods=3, freq="7D").astype(f"datetime64[{unit}]"),
                "value": [10, 20, 30],
            }
        )
        for trading_days in (True, False):
            daily = czsc.resample_to_daily(frame.copy(), only_trade_date=trading_days)
            assert str(daily["dt"].dtype) == "datetime64[ns]"
            assert daily["value"].iloc[0] == 10 and daily["value"].iloc[-1] == 30
    print(
        "python:",
        sys.version,
        "platform:",
        platform.platform(),
        "machine:",
        actual_machine,
        "libc:",
        platform.libc_ver(),
    )
    print("czsc:", installed_version, "pandas:", pd.__version__, "numpy:", np.__version__, "native:", native_path)
    print("PASS installed release wheel: version, core, migrated signal contract, SMA, eight timestamp combinations")


if __name__ == "__main__":
    main()
