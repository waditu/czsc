"""验证 naive datetime 通过 RawBar 往返后小时数不变。

根因：parse_python_datetime 对 naive datetime 调 .timestamp()，
Python 按系统时区解释，UTC+8 上 15:00 → 07:00 UTC。
修复：naive datetime 改用 calendar.timegm，数值直接当 UTC。
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from czsc import Freq, RawBar


def _make_bar(dt_input) -> RawBar:
    return RawBar(
        symbol="test",
        dt=dt_input,
        freq=Freq.F5,
        open=1.0,
        close=1.0,
        high=1.0,
        low=1.0,
        vol=1.0,
        amount=1.0,
    )


@pytest.mark.parametrize(
    "dt_input",
    [
        datetime(2024, 1, 2, 15, 0),
        datetime(2024, 1, 2, 9, 30),
        datetime(2024, 1, 2, 0, 0),
        pd.Timestamp("2024-01-02 15:00:00"),
        pd.Timestamp("2024-01-02 09:30:00"),
    ],
    ids=["stdlib-15:00", "stdlib-09:30", "stdlib-00:00", "pd-15:00", "pd-09:30"],
)
def test_naive_datetime_preserves_hour(dt_input):
    """Naive datetime 经过 RawBar 往返后，小时和分钟必须与输入一致。"""
    bar = _make_bar(dt_input)
    assert bar.dt.hour == dt_input.hour, f"hour mismatch: input={dt_input.hour}, bar.dt={bar.dt.hour}"
    assert bar.dt.minute == dt_input.minute, f"minute mismatch: input={dt_input.minute}, bar.dt={bar.dt.minute}"


def test_aware_datetime_still_converts():
    """带时区信息的 datetime 仍应正确转换。"""
    cst = timezone(timedelta(hours=8))
    aware = datetime(2024, 1, 2, 15, 0, tzinfo=cst)
    bar = _make_bar(aware)
    # 15:00 CST = 07:00 UTC，出站 naive 输出应为 07:00
    assert bar.dt.hour == 7
    assert bar.dt.minute == 0


def test_integer_epoch_unchanged():
    """整数 epoch 输入行为不变。"""
    epoch = 1704067200  # 2024-01-01 00:00:00 UTC
    bar = _make_bar(epoch)
    assert bar.dt.hour == 0
    assert bar.dt.minute == 0
