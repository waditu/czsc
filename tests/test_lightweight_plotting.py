"""tests/test_lightweight_plotting.py —— lightweight_charts 子包 L1 + L2 单测。

覆盖 §10.4 / §10.5（详见 v2 设计文档）：

- candle / fx marker / bi_line / SMA / Vol / MACD 数量与单调性
- 顶 / 底分型的 position / shape / color 正确
- HTML 渲染产物结构（含 PAYLOAD JSON、不残留 NaN / Jinja 语法）

测试数据统一来自 ``czsc.mock.generate_symbol_kines``，固定 seed=42。
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

import pytest

from czsc import CZSC, BarGenerator, Freq, format_standard_kline
from czsc._native import CzscTrader
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import _data, _html_renderer, plot_czsc, plot_czsc_trader

# ---------- fixtures ----------------------------------------------------------


@pytest.fixture(scope="module")
def czsc_30m() -> CZSC:
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20230601", seed=42)
    return CZSC(format_standard_kline(df, freq=Freq.F30))


@pytest.fixture(scope="module")
def trader_multi() -> CzscTrader:
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20230701", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    bg = BarGenerator(base_freq="30分钟", freqs=["30分钟", "60分钟", "日线"], max_count=5000)
    for bar in bars:
        bg.update(bar)
    return CzscTrader(bg, positions=[], signals_config=[])


def _payload_dict(c: CZSC) -> dict[str, Any]:
    return _data.build_from_czsc(c).to_dict()


# ---------- L1 数据准备层 -----------------------------------------------------


class TestBuildFromCzsc:
    def test_candle_count_equals_bars_raw(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m)
        pane = payload.panes[0]
        assert len(pane.main.candles) == len(czsc_30m.bars_raw)

    def test_fx_line_connects_all_fractals(self, czsc_30m: CZSC):
        """分型改用虚线连接：fx_line 顶点数 = fx_list 去重后数量，与 FX 顶点价格一一对应。"""
        payload = _data.build_from_czsc(czsc_30m)
        pane = payload.panes[0]
        # 同 time 去重后两边数量应一致（czsc 不会出现真同 time 重复 FX）
        fx_pairs = sorted({(int(fx.dt.timestamp()), float(fx.fx)) for fx in czsc_30m.fx_list}, key=lambda x: x[0])
        assert len(pane.main.fx_line) == len({t for t, _ in fx_pairs})
        # 时间严格升序
        times = [pt["time"] for pt in pane.main.fx_line]
        assert times == sorted(set(times))
        # 价格匹配 FX.fx
        expected = dict(fx_pairs)
        for pt in pane.main.fx_line:
            assert pt["value"] == expected[pt["time"]]

    def test_bi_line_zigzag(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m)
        pts = payload.panes[0].main.bi_line
        bis = list(czsc_30m.bi_list)
        # 每笔起点 + 末笔终点 = len(bis) + 1，但同 time 去重可能减 1
        assert len(pts) in {len(bis) + 1, len(bis)}
        # zigzag：相邻 value 一升一降
        for a, b in zip(pts, pts[1:], strict=False):
            assert a["value"] != b["value"]

    def test_sma_length_and_nan_head(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m, show_sma=(5, 20))
        pane = payload.panes[0]
        n = len(pane.main.candles)
        assert len(pane.main.sma5) == n
        assert len(pane.main.sma20) == n
        # SMA 头几根应当为 None（unix 秒 + value=None）
        assert pane.main.sma5[0]["value"] is None
        assert pane.main.sma5[4]["value"] is not None
        assert pane.main.sma20[0]["value"] is None
        assert pane.main.sma20[19]["value"] is not None

    def test_volume_color(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m)
        theme = payload.theme
        for bar, hist in zip(czsc_30m.bars_raw, payload.panes[0].volume.bars, strict=True):
            up = float(bar.close) >= float(bar.open)
            assert hist["color"] == (theme["up"] if up else theme["down"])

    def test_macd_three_series_aligned(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m)
        macd = payload.panes[0].macd
        n = len(payload.panes[0].main.candles)
        assert len(macd.diff) == n
        assert len(macd.dea) == n
        assert len(macd.macd) == n

    def test_time_strictly_monotonic(self, czsc_30m: CZSC):
        pane = _data.build_from_czsc(czsc_30m).panes[0]
        for seq_name in ("candles", "sma5", "sma20", "fx_line", "bi_line"):
            seq = getattr(pane.main, seq_name)
            times = [x["time"] for x in seq]
            assert times == sorted(set(times)), f"{seq_name} times not strictly increasing or has duplicates"

    def test_tail_bars_truncates_all_series(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m, tail_bars=120)
        pane = payload.panes[0]
        assert len(pane.main.candles) == 120
        assert len(pane.volume.bars) == 120
        assert len(pane.macd.diff) == 120
        # fx_line / bi_line 只保留时间区间内的，不一定等长，但不能比 candles 多
        assert len(pane.main.fx_line) <= 120
        assert len(pane.main.bi_line) <= 120

    def test_minimal_czsc_30_bars(self):
        """少量 K 线不出 BI 也不应崩溃。"""
        df = generate_symbol_kines("000001", "30分钟", "20230101", "20230110", seed=42)
        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        payload = _data.build_from_czsc(c)
        pane = payload.panes[0]
        assert len(pane.main.candles) == len(c.bars_raw)
        # 极短序列允许 bi_list 为空，但其余 series 必须等长
        assert len(pane.volume.bars) == len(c.bars_raw)
        assert len(pane.macd.diff) == len(c.bars_raw)


class TestBuildFromTrader:
    def test_panes_freq_order_large_to_small(self, trader_multi: CzscTrader):
        payload = _data.build_from_trader(trader_multi)
        labels = [p.freq_label for p in payload.panes]
        assert labels == ["日线", "60分钟", "30分钟"]

    def test_each_pane_has_three_series(self, trader_multi: CzscTrader):
        payload = _data.build_from_trader(trader_multi)
        for pane in payload.panes:
            assert pane.main.candles, f"pane {pane.freq_label} 主图为空"
            assert pane.volume.bars, f"pane {pane.freq_label} 成交量为空"
            assert pane.macd.diff, f"pane {pane.freq_label} MACD 为空"


# ---------- L2 渲染层 --------------------------------------------------------


class TestHtmlRenderer:
    def test_dom_structure(self, czsc_30m: CZSC):
        payload = _data.build_from_czsc(czsc_30m)
        html = _html_renderer.render(payload)
        # 静态部分
        assert "<title>" in html and "</title>" in html
        assert "lightweight-charts" in html
        # 动态部分：JS 模板里出现的占位 div 选择器
        assert 'id="main-' in html or "id='main-" in html or "main-" in html
        assert "PAYLOAD.panes.forEach" in html
        # PAYLOAD JSON 注入成功
        m = re.search(r"(?:const|var) PAYLOAD = (.*?);\n", html, re.S)
        assert m, "PAYLOAD JSON 未被注入"
        data = json.loads(m.group(1))
        assert data["symbol"] == "000001"
        assert len(data["panes"]) == 1
        assert data["panes"][0]["freq_label"] == "30分钟"

    def test_no_jinja_left(self, czsc_30m: CZSC):
        html = _html_renderer.render(_data.build_from_czsc(czsc_30m))
        # string.Template 把 $title $bg 等全部消化掉；Jinja 块语法不能出现
        # 注意：{{ / }} 会被 JSON 嵌套对象自然产生，不能直接断言；这里只校验 Jinja 块语法
        assert "{%" not in html, "HTML 含 Jinja 块起始 {%"
        assert "%}" not in html, "HTML 含 Jinja 块结束 %}"
        # 也确保 string.Template 占位符已全部替换
        assert "$title" not in html
        assert "$lwc_script" not in html
        assert "__PAYLOAD_JSON__" not in html

    def test_no_nan_in_payload(self, czsc_30m: CZSC):
        html = _html_renderer.render(_data.build_from_czsc(czsc_30m))
        m = re.search(r"(?:const|var) PAYLOAD = (.*?);\n", html, re.S)
        assert m
        # JS 端 NaN 字面量在 JSON 中非法；json.loads 能成功即说明无 NaN
        data = json.loads(m.group(1))
        # 进一步扫描所有 value 字段，不应出现 float('nan')
        for pane in data["panes"]:
            for series_name in ("sma5", "sma20", "fx_line", "bi_line"):
                for pt in pane["main"][series_name]:
                    v = pt["value"]
                    assert v is None or not (isinstance(v, float) and math.isnan(v))

    def test_no_chinese_fx_labels(self, czsc_30m: CZSC):
        """分型改用虚线后，HTML 中不应再出现 '顶' / '底' 文本 marker。"""
        html = _html_renderer.render(_data.build_from_czsc(czsc_30m))
        m = re.search(r"(?:const|var) PAYLOAD = (.*?);\n", html, re.S)
        assert m
        data = json.loads(m.group(1))
        for pane in data["panes"]:
            # 主图各 series 不应再出现 markers 字段 / text 字段
            assert "fx_markers" not in pane["main"], "fx_markers 字段未清理"
            assert "fx_line" in pane["main"], "fx_line 字段缺失"

    def test_multi_freq_renders_tabs(self, trader_multi: CzscTrader):
        """多周期 HTML 应包含 tabs 容器和 3 个 freq-pane。"""
        payload = _data.build_from_trader(trader_multi)
        html = _html_renderer.render(payload)
        assert 'id="tabs"' in html
        # tab 按钮文本由 freq_label 渲染（运行时插入），但 PAYLOAD 中应有 3 个 panes
        m = re.search(r"(?:const|var) PAYLOAD = (.*?);\n", html, re.S)
        data = json.loads(m.group(1))
        assert [p["freq_label"] for p in data["panes"]] == ["日线", "60分钟", "30分钟"]


class TestPublicApi:
    def test_plot_czsc_returns_html_string_when_path_is_none(self, czsc_30m: CZSC):
        html = plot_czsc(czsc_30m, output="html")
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_plot_czsc_writes_file(self, tmp_path, czsc_30m: CZSC):
        out = tmp_path / "single.html"
        result = plot_czsc(czsc_30m, output="html", path=out)
        assert str(result) == str(out)
        assert out.exists()
        assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")

    def test_plot_czsc_trader_writes_multi_panes(self, tmp_path, trader_multi: CzscTrader):
        out = tmp_path / "multi.html"
        plot_czsc_trader(trader_multi, output="html", path=out, tail_bars=300)
        html = out.read_text(encoding="utf-8")
        m = re.search(r"(?:const|var) PAYLOAD = (.*?);\n", html, re.S)
        assert m
        data = json.loads(m.group(1))
        assert len(data["panes"]) == 3

    def test_plot_czsc_unknown_output_raises(self, czsc_30m: CZSC):
        with pytest.raises(ValueError):
            plot_czsc(czsc_30m, output="pdf")  # type: ignore[arg-type]

    def test_plot_czsc_trader_rejects_bad_object(self):
        class Bad:
            symbol = "X"

        with pytest.raises(TypeError):
            plot_czsc_trader(Bad(), output="html")
