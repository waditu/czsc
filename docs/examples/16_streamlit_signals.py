"""案例 16：lightweight_charts 信号叠加（Streamlit 版）

侧栏多选 signals，主区显示对应 marker；顶部 KPI 卡片显示当前 K 线上仍生效的所有信号
完整 value（v1_v2_v3_score），代偿 iframe 内 tooltip 不能自定义的限制。

启动：
    uv run --no-sync streamlit run docs/examples/16_streamlit_signals.py
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from czsc import Freq, format_standard_kline
from czsc._native import BarGenerator, CzscTrader
from czsc.mock import generate_symbol_kines
from czsc.traders import generate_czsc_signals, get_signals_freqs
from czsc.utils.plotting.lightweight import _data, _signals, _streamlit_renderer, _theme

ALL_SIGNALS: dict[str, dict] = {
    "笔表里关系 · 30 分钟": {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    "笔表里关系 · 日线": {"name": "cxt_bi_status_V230101", "freq": "日线"},
    "5 日均线分类": {"name": "tas_ma_base_V221101", "freq": "日线", "di": 1, "timeperiod": 5, "ma_type": "SMA"},
    "30 分钟涨跌停": {"name": "bar_zdt_V230331", "freq": "30分钟", "di": 1},
}


@st.cache_data(show_spinner="生成 mock K 线...")
def _load_bars(symbol: str, start: str, end: str, seed: int):
    df = generate_symbol_kines(symbol, "30分钟", start, end, seed=seed)
    return format_standard_kline(df, freq=Freq.F30)


def main() -> None:
    st.set_page_config(
        page_title="lightweight_charts · 信号叠加",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        symbol = st.text_input("Symbol", value="000001")
        date_range = st.date_input("区间", value=(_dt.date(2023, 1, 1), _dt.date(2024, 3, 1)))
        picked = st.multiselect("信号", list(ALL_SIGNALS), default=list(ALL_SIGNALS)[:3])
        tail = st.slider("尾部 K 线", 200, 2000, 600, step=50)
        seed = st.number_input("随机种子", value=42, step=1)
        theme_name = st.segmented_control("主题", options=["light", "dark"], default="light") or "light"

    if not picked:
        st.warning("请至少选择一个信号。")
        st.stop()
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.warning("请选择起止日期。")
        st.stop()

    start = date_range[0].strftime("%Y%m%d")
    end = date_range[1].strftime("%Y%m%d")
    bars = _load_bars(symbol, start, end, int(seed))
    cfg = [ALL_SIGNALS[k] for k in picked]
    # 处理 get_signals_freqs 对 params 字段的强制要求
    normalized_cfg = [({**c, "params": {}} if "params" not in c else c) for c in cfg]
    freqs = get_signals_freqs(normalized_cfg) or ["30分钟"]
    base = "30分钟"
    if base not in freqs:
        freqs = [base, *freqs]

    bg = BarGenerator(base_freq=base, freqs=freqs, max_count=max(10000, len(bars)))
    for b in bars:
        bg.update(b)
    ct = CzscTrader(bg, positions=[], signals_config=[])

    theme = _theme.get_theme(theme_name)  # type: ignore[arg-type]
    payload = _data.build_from_trader(
        ct,
        theme=theme,
        show_sma=(5, 20),
        tail_bars=tail,
        title=f"{symbol} · 信号叠加",
    )

    df = generate_czsc_signals(bars, signals_config=cfg, df=True)
    overlays = _signals.build_signal_overlays(
        df,
        freqs=freqs,
        palette=_theme.get_signal_palette(theme_name),  # type: ignore[arg-type]
    )
    for pane in payload.panes:
        series = overlays.get(pane.freq_label, [])
        if tail is not None and pane.main.candles:
            cutoff = pane.main.candles[0]["time"]
            series = [
                _signals.SignalSeries(
                    key=s.key,
                    short_label=s.short_label,
                    color=s.color,
                    shape=s.shape,
                    position=s.position,
                    markers=[m for m in s.markers if m["time"] >= cutoff],
                )
                for s in series
            ]
        pane.signals = series  # type: ignore[assignment]

    if len(payload.panes) == 1:
        freq = payload.panes[0]
        _streamlit_renderer.render_signal_kpi(freq)
        _streamlit_renderer.render_freq(freq, theme, key=f"sig-{freq.freq_label}-0")
    else:
        tabs = st.tabs([p.freq_label for p in payload.panes])
        for fi, (tab, freq) in enumerate(zip(tabs, payload.panes, strict=True)):
            with tab:
                _streamlit_renderer.render_signal_kpi(freq, key_prefix=f"kpi-{fi}")
                _streamlit_renderer.render_freq(freq, theme, key=f"sig-{freq.freq_label}-{fi}")


if __name__ == "__main__":
    main()
