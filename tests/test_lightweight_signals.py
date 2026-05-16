"""tests/test_lightweight_signals.py —— lightweight 信号叠加层单测 + 集成测试。

覆盖飞书评审方案 §9.1 单元（U1–U9）和 §9.2 集成（I1–I6）。
"""

from __future__ import annotations

import json  # noqa: F401  - 后续 task 使用
import math  # noqa: F401  - 后续 task 使用
import re  # noqa: F401  - 后续 task 使用
from typing import Any  # noqa: F401  - 后续 task 使用

import pandas as pd  # noqa: F401  - 后续 task 使用
import pytest  # noqa: F401  - 后续 task 使用

from czsc import Freq, format_standard_kline  # noqa: F401  - 后续 task 使用
from czsc.mock import generate_symbol_kines  # noqa: F401  - 后续 task 使用


class TestPaletteConstants:
    def test_palette_lengths_match(self):
        from czsc.utils.plotting.lightweight import _theme

        assert len(_theme.SIGNAL_PALETTE_LIGHT) >= 10
        assert len(_theme.SIGNAL_PALETTE_LIGHT) == len(_theme.SIGNAL_PALETTE_DARK)
        assert len(_theme.SIGNAL_SHAPES) >= 2
        assert len(_theme.SIGNAL_POSITIONS) == 2

    def test_palette_colors_are_hex(self):
        from czsc.utils.plotting.lightweight import _theme

        for color in _theme.SIGNAL_PALETTE_LIGHT + _theme.SIGNAL_PALETTE_DARK:
            assert isinstance(color, str)
            assert color.startswith("#") and len(color) == 7


class TestSignalsModuleSkeleton:
    def test_types_importable(self):
        from czsc.utils.plotting.lightweight._signals import (
            SignalMarker,
            SignalSeries,
        )

        marker: SignalMarker = {"time": 1, "value": "v1_v2_v3_0", "v1": "v1", "color": "#000000"}
        series = SignalSeries(
            key="30分钟_D1_X",
            short_label="X",
            color="#1F3C6E",
            shape="circle",
            position="aboveBar",
            markers=[marker],
        )
        assert series.key == "30分钟_D1_X"
        assert series.markers[0]["v1"] == "v1"


class TestDetectTransitions:
    """飞书评审 §9.1 U1–U5：transition 检测核心逻辑。"""

    @staticmethod
    def _df(values: list[str | float]) -> pd.DataFrame:
        """构造一个 dt + key 列的小 DataFrame。"""
        return pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=len(values), freq="30min"),
                "30分钟_D1_X": values,
            }
        )

    def test_u1_strict_switching(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["A_x_x_0", "A_x_x_0", "B_x_x_0", "B_x_x_0", "C_x_x_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        assert [m["v1"] for m in markers] == ["A", "B", "C"]
        assert [m["time"] for m in markers] == [
            int(df["dt"].iloc[i].timestamp()) for i in (0, 2, 4)
        ]

    def test_u2_other_filtered_by_default(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_0", "其他_任意_任意_0", "向上_任意_任意_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        # '其他' 既不画也不更新 prev_value → 仅首行触发，第 3 行不算切换
        assert len(markers) == 1
        assert markers[0]["v1"] == "向上"

    def test_u3_include_others(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_0", "其他_任意_任意_0", "向上_任意_任意_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=True)
        assert [m["v1"] for m in markers] == ["向上", "其他", "向上"]

    def test_u4_skip_non_string(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["A_x_x_0", float("nan"), "", 1.5, "B_x_x_0"])  # type: ignore[list-item]
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        # NaN/空串/数字都跳过且不更新 prev_value
        assert [m["v1"] for m in markers] == ["A", "B"]

    def test_u5_marker_full_value_preserved(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_3"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        assert markers[0]["value"] == "向上_任意_任意_3"
        assert markers[0]["v1"] == "向上"
