"""tests/test_lightweight_signals.py —— lightweight 信号叠加层单测 + 集成测试。

覆盖飞书评审方案 §9.1 单元（U1–U9）和 §9.2 集成（I1–I6）。
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd
import pytest

from czsc import Freq, format_standard_kline
from czsc.mock import generate_symbol_kines


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
