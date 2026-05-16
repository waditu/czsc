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

    def test_direction_constants_present(self):
        from czsc.utils.plotting.lightweight import _theme

        assert "向上" in _theme.SEMANTIC_UP
        assert "向下" in _theme.SEMANTIC_DOWN
        # 3 色都是 #RRGGBB
        for color in (_theme.MARKER_COLOR_UP, _theme.MARKER_COLOR_DOWN, _theme.MARKER_COLOR_NEUTRAL):
            assert color.startswith("#") and len(color) == 7
        assert _theme.classify_direction("向上") == "up"
        assert _theme.classify_direction("向下") == "down"
        assert _theme.classify_direction("XYZ") == "neutral"
        assert _theme.direction_color("up") == _theme.MARKER_COLOR_UP


class TestSignalsModuleSkeleton:
    def test_types_importable(self):
        from czsc.utils.plotting.lightweight._signals import (
            SignalMarker,
            SignalSeries,
        )

        marker: SignalMarker = {
            "time": 1,
            "value": "v1_v2_v3_0",
            "v1": "v1",
            "color": "#000000",
            "direction": "neutral",
            "vnum": 0,
        }
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
        assert [m["time"] for m in markers] == [int(df["dt"].iloc[i].timestamp()) for i in (0, 2, 4)]

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
        assert markers[0]["direction"] == "up"  # "向上" ∈ SEMANTIC_UP
        assert markers[0]["color"] == "#C03A2B"  # MARKER_COLOR_UP
        # vnum 是占位 0；正式编号在 build_signal_overlays 内回填
        assert markers[0]["vnum"] == 0

    def test_direction_classification(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_a_b_0", "向下_a_b_0", "未知_a_b_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        assert [m["direction"] for m in markers] == ["up", "down", "neutral"]
        assert markers[0]["color"] == "#C03A2B"
        assert markers[1]["color"] == "#2E7D32"
        assert markers[2]["color"] == "#888888"


class TestPaletteAssignment:
    def test_u6_stable_color_for_same_key(self):
        from czsc.utils.plotting.lightweight._signals import assign_palette
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        keys = ["30分钟_D1_A", "30分钟_D1_B", "30分钟_D1_C"]
        a = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        b = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        assert a == b
        # 同 palette 长度内不同 key 颜色互异
        assert len(set(a.values())) == len(keys)

    def test_u7_palette_cycles_when_exceeds(self):
        from czsc.utils.plotting.lightweight._signals import assign_palette
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        keys = [f"30分钟_D1_K{i}" for i in range(len(SIGNAL_PALETTE_LIGHT) + 1)]
        mapping = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        # 第 N+1 个 key 回到 palette[0]
        assert mapping[keys[-1]] == SIGNAL_PALETTE_LIGHT[0]


class TestBuildSignalOverlays:
    def test_u8_multi_freq_bucketing(self):
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=3, freq="30min"),
                "30分钟_D1_A": ["向上_任意_任意_0", "向下_任意_任意_0", "向下_任意_任意_0"],
                "30分钟_D1_B": ["多_任意_任意_0", "多_任意_任意_0", "空_任意_任意_0"],
                "日线_D1_C": ["持平_任意_任意_0", "持平_任意_任意_0", "持平_任意_任意_0"],
            }
        )
        out = build_signal_overlays(
            df,
            freqs=["30分钟", "日线"],
            palette=SIGNAL_PALETTE_LIGHT,
        )
        assert set(out.keys()) == {"30分钟", "日线"}
        keys_30m = [s.key for s in out["30分钟"]]
        keys_day = [s.key for s in out["日线"]]
        assert keys_30m == ["30分钟_D1_A", "30分钟_D1_B"]
        assert keys_day == ["日线_D1_C"]
        # 颜色独立分配（同 palette 池，同序号同色，但 series 在不同桶里）
        assert out["30分钟"][0].color in SIGNAL_PALETTE_LIGHT
        # 持平没有切换且仅 1 个值出现一次 → 第一条仍 trigger 一个 marker
        assert len(out["日线"][0].markers) == 1
        # short_label 去掉 freq 前缀
        assert out["30分钟"][0].short_label == "D1_A"

    def test_build_overlays_marker_color_from_direction(self):
        """marker.color 来自 direction（不再等于 SignalSeries.color）。"""
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import (
            MARKER_COLOR_DOWN,
            MARKER_COLOR_UP,
            SIGNAL_PALETTE_LIGHT,
        )

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=2, freq="30min"),
                "30分钟_D1_A": ["向上_v_v_0", "向下_v_v_0"],
            }
        )
        out = build_signal_overlays(df, freqs=["30分钟"], palette=SIGNAL_PALETTE_LIGHT)
        series = out["30分钟"][0]
        # legend chip 颜色仍来自 palette
        assert series.color == SIGNAL_PALETTE_LIGHT[0]
        # marker 颜色来自 direction
        assert series.markers[0]["color"] == MARKER_COLOR_UP
        assert series.markers[1]["color"] == MARKER_COLOR_DOWN

    def test_value_index_and_vnum(self):
        """每个 series 内 unique value 按首次出现顺序得到 1-based 编号；marker.vnum 与之对应。"""
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=5, freq="30min"),
                "30分钟_D1_A": [
                    "向上_a_a_0",
                    "向上_a_a_0",
                    "向下_a_a_0",
                    "向下_a_a_0",
                    "持平_a_a_0",
                ],
            }
        )
        out = build_signal_overlays(df, freqs=["30分钟"], palette=SIGNAL_PALETTE_LIGHT)
        s = out["30分钟"][0]
        # 首次出现顺序：向上_a_a_0 → 1，向下_a_a_0 → 2，持平_a_a_0 → 3
        assert s.value_index["向上_a_a_0"] == 1
        assert s.value_index["向下_a_a_0"] == 2
        assert s.value_index["持平_a_a_0"] == 3
        # marker.vnum 与 value_index 对齐
        assert [m["vnum"] for m in s.markers] == [1, 2, 3]

    def test_shape_cycles_per_signal_key(self):
        """每个 signal key 按 idx 循环 SIGNAL_SHAPES。"""
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT, SIGNAL_SHAPES

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=2, freq="30min"),
                "30分钟_D1_A": ["a_x_y_0", "b_x_y_0"],
                "30分钟_D1_B": ["c_x_y_0", "d_x_y_0"],
                "30分钟_D1_C": ["e_x_y_0", "f_x_y_0"],
                "30分钟_D1_D": ["g_x_y_0", "h_x_y_0"],
                "30分钟_D1_E": ["i_x_y_0", "j_x_y_0"],
            }
        )
        out = build_signal_overlays(df, freqs=["30分钟"], palette=SIGNAL_PALETTE_LIGHT)
        shapes = [s.shape for s in out["30分钟"]]
        # 5 个 key 在 4 个 shape 上循环：[circle, square, arrowUp, arrowDown, circle]
        assert shapes == [SIGNAL_SHAPES[i % len(SIGNAL_SHAPES)] for i in range(5)]


class TestFreqPayloadSignalsField:
    def test_u9_signals_defaults_empty(self):
        from czsc import CZSC, Freq, format_standard_kline
        from czsc.utils.plotting.lightweight import _data

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20230301", seed=42)
        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        payload = _data.build_from_czsc(c)
        assert payload.panes[0].signals == []
        # asdict 序列化不抛
        d = payload.to_dict()
        assert d["panes"][0]["signals"] == []


SIGNALS_CONFIG_DEMO = [
    {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    {"name": "cxt_bi_status_V230101", "freq": "日线"},
]


@pytest.fixture(scope="module")
def _bars_demo():
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20230601", seed=42)
    return format_standard_kline(df, freq=Freq.F30)


class TestPlotCzscSignalsPayload:
    def test_i3_multi_freq_bucketing(self, _bars_demo):
        """日线 key 不出现在 30 分钟 pane.signals，反之亦然。"""
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        assert isinstance(html, str)
        # 提取 PAYLOAD JSON 检查 signals 分桶
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        assert m is not None
        payload = json.loads(m.group(1))
        for pane in payload["panes"]:
            for series in pane["signals"]:
                key = series["key"]
                assert key.startswith(pane["freq_label"] + "_"), f"key {key} 落到了错误的 pane {pane['freq_label']}"

    def test_i4_transition_count_matches_direct_calc(self, _bars_demo):
        """plot 输出的 marker 数应当全部来自直接 detect_transitions 的结果。"""
        from czsc.traders import generate_czsc_signals
        from czsc.utils.plotting.lightweight import plot_czsc_signals
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "30分钟"}],
            output="html",
            tail_bars=200,
        )
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))

        df = generate_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "30分钟"}],
            df=True,
        )
        signal_col = next(c for c in df.columns if "表里关系" in c)
        plot_marker_times = {
            m_["time"] for pane in payload["panes"] for series in pane["signals"] for m_ in series["markers"]
        }
        direct = detect_transitions(df, signal_col, include_others=False)
        # 对齐+去重后 plot markers 一定 ≤ direct transitions 数量
        assert len(plot_marker_times) <= len({m_["time"] for m_ in direct})
        assert len(plot_marker_times) > 0  # 至少要有 marker


class TestPlotCzscSignalsHTML:
    def test_i1_html_contains_signal_blocks(self, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        # JS 必含 setMarkers 调用 + SIGNALS tooltip 段标题
        assert "setMarkers" in html
        assert "SIGNALS · @CURRENT BAR" in html
        # short_label 渲染到图例区
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))
        any_signals = any(pane["signals"] for pane in payload["panes"])
        assert any_signals


class TestStreamlitMarkers:
    def test_build_groups_passes_markers_to_candle(self):
        from czsc.utils.plotting.lightweight._data import build_from_czsc
        from czsc.utils.plotting.lightweight._signals import SignalMarker, SignalSeries
        from czsc.utils.plotting.lightweight._streamlit_renderer import _build_groups
        from czsc.utils.plotting.lightweight._theme import get_theme

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20230201", seed=42)
        from czsc import CZSC, Freq, format_standard_kline

        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        payload = build_from_czsc(c)
        freq = payload.panes[0]
        freq.signals = [
            SignalSeries(
                key="30分钟_D1_X",
                short_label="D1_X",
                color="#1F3C6E",
                shape="circle",
                position="aboveBar",
                markers=[
                    SignalMarker(
                        time=int(freq.main.candles[10]["time"]),
                        value="A_x_x_0",
                        v1="A",
                        color="#1F3C6E",
                        direction="neutral",
                        vnum=0,
                    ),
                ],
            )
        ]
        groups = _build_groups(freq, get_theme("light"), visible=None)
        candle_cfg = groups[0]["series"][0]
        markers = candle_cfg.get("markers", [])
        assert any(m["time"] == int(freq.main.candles[10]["time"]) for m in markers)
        assert markers[0]["color"] == "#1F3C6E"
        assert markers[0]["text"] == "A"

    def test_render_signal_kpi_callable(self):
        """signal KPI 仅做"无 markers / 无 candles"两条早返路径的导入/早返冒烟。"""
        from czsc.utils.plotting.lightweight._data import (
            FreqPayload,
            MacdPane,
            MainPane,
            VolumePane,
        )
        from czsc.utils.plotting.lightweight._streamlit_renderer import render_signal_kpi

        # 无 signals → 直接 return，不会触发 streamlit 调用
        empty = FreqPayload(freq_label="30分钟", main=MainPane(), volume=VolumePane(), macd=MacdPane())
        render_signal_kpi(empty)  # 不抛


class TestCase15HtmlPersistence:
    def test_i2_writes_html_file(self, tmp_path, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        out = tmp_path / "15_lwc_signals.html"
        ret = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            path=out,
            tail_bars=200,
        )
        assert str(ret) == str(out)
        assert out.exists()
        assert out.stat().st_size > 50 * 1024  # > 50KB
        html = out.read_text(encoding="utf-8")
        # 自包含 + 关键 JS hook 存在
        assert html.startswith("<!DOCTYPE html")
        assert "setMarkers" in html


class TestBackwardCompat:
    def test_i5_case13_module_importable(self):
        """跑案例 13 的模块 import，确认 demo 函数仍可调用。"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "case13",
            "docs/examples/13_lightweight_charts_html.py",
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # 案例 13 的关键 demo 函数仍存在
        assert callable(getattr(mod, "demo_single", None))
        assert callable(getattr(mod, "demo_multi", None))


class TestSignalTimelinePane:
    def test_html_contains_signal_timeline(self, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        assert "row-sig" in html
        assert "SIGNAL TIMELINE" in html
        assert "sigRowSeriesByKey" in html
        assert "siglabels-" in html


class TestHoverHighlight:
    def test_html_contains_hover_handlers(self, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        # mouseenter handler 出现
        assert "mouseenter" in html
        assert "highlightedKey" in html
        assert "hexToRgba" in html
        assert ".legend--hover" in html
        assert "applyRowMarkers" in html


class TestCrossPaneCrosshair:
    def test_html_contains_cross_tab_crosshair_logic(self, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        # 跨 tab crosshair 关键标识
        assert "crosshairTime" in html
        assert "applyCrosshairToTab" in html
        assert "setCrosshairPosition" in html


@pytest.mark.slow
class TestStreamlitSlow:
    def test_i6_streamlit_app_smoke(self):
        """通过 streamlit.testing.v1.AppTest 启动案例 16，确保不抛异常。"""
        try:
            from streamlit.testing.v1 import AppTest  # noqa: PLC0415
        except ImportError:
            pytest.skip("当前环境无 streamlit.testing.v1.AppTest")
            return
        at = AppTest.from_file("docs/examples/16_streamlit_signals.py", default_timeout=30)
        at.run()
        # 若无异常，通过；若因 streamlit-lightweight-charts 缺失而异常，skip
        if at.exception:
            exc_msg = str(at.exception[0].message) if at.exception else ""
            if "streamlit-lightweight-charts" in exc_msg:
                pytest.skip("当前环境无 streamlit-lightweight-charts，无法完整运行案例 16")
            else:
                raise AssertionError(f"案例 16 执行异常: {exc_msg}")


class TestMarkerTimeAlignment:
    def test_daily_signal_marker_aligned_to_daily_candle(self, _bars_demo):
        """日线信号 marker 时间戳必须 == 某根日线 candle.time。"""
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "日线"}],
            output="html",
            tail_bars=200,
        )
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))
        # 找到日线 pane
        daily = next((p for p in payload["panes"] if p["freq_label"] == "日线"), None)
        assert daily is not None, "日线 pane 应该存在"
        candle_times = {c["time"] for c in daily["main"]["candles"]}
        for series in daily["signals"]:
            for marker in series["markers"]:
                assert marker["time"] in candle_times, (
                    f"日线 signal marker.time={marker['time']} 未对齐到任何日线 candle.time"
                )

    def test_dedup_within_same_candle(self, _bars_demo):
        """同一根 candle.time 上一个 series 最多一个 marker。"""
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "日线"}],
            output="html",
            tail_bars=200,
        )
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))
        daily = next((p for p in payload["panes"] if p["freq_label"] == "日线"), None)
        assert daily is not None
        for series in daily["signals"]:
            times = [marker["time"] for marker in series["markers"]]
            assert len(times) == len(set(times)), f"{series['key']} 存在同 candle 重复 marker"


class TestSignalTimelineSync:
    def test_html_has_cross_pane_timescale_subscription_for_sig(self, _bars_demo):
        """HTML 中 cSig 必须有 timescale 和 crosshair 的双向订阅，确保滚轮/平移同步。"""
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        # cSig 自己订阅 timescale 变化（往外推）
        assert "cSig.timeScale().subscribeVisibleLogicalRangeChange" in html
        # cSig 被其他 chart 推到（接受来自 main/vol/macd 的变化）
        assert "cSig.timeScale().setVisibleLogicalRange" in html
        # cSig 与其他 chart 双向 crosshair
        assert "cSig.subscribeCrosshairMove" in html
        assert "cSig.setCrosshairPosition" in html
