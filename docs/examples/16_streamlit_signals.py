"""案例 16：lightweight_charts 信号叠加（Streamlit 版）

通过 ``plot_czsc_signals(..., output="streamlit")`` 在 Streamlit 应用中嵌入与离线
HTML 完全一致的可视化 —— 包含 marker 红绿点、tooltip SIGNALS / SUB-FREQ SIGNALS
段、副 pane signal timeline、hover 双向高亮、tab 切换十字光标联动等全部交互。

侧栏可多选 signals、改 tail_bars、切换主题；主区是嵌入的 lightweight-charts iframe。

启动：
    uv run --no-sync streamlit run docs/examples/16_streamlit_signals.py
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from czsc import Freq, format_standard_kline
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import plot_czsc_signals

ALL_SIGNALS: dict[str, dict] = {
    "笔表里关系 · 30 分钟": {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    "笔表里关系 · 日线": {"name": "cxt_bi_status_V230101", "freq": "日线"},
    "5 日均线分类": {
        "name": "tas_ma_base_V221101",
        "freq": "日线",
        "di": 1,
        "timeperiod": 5,
        "ma_type": "SMA",
    },
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
        date_range = st.date_input(
            "区间",
            value=(_dt.date(2023, 1, 1), _dt.date(2024, 3, 1)),
        )
        picked = st.multiselect(
            "信号",
            list(ALL_SIGNALS),
            default=list(ALL_SIGNALS)[:3],
        )
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

    plot_czsc_signals(
        bars,
        signals_config=cfg,
        output="streamlit",
        title=f"{symbol} · 信号叠加",
        theme=theme_name,  # type: ignore[arg-type]
        tail_bars=tail,
    )


if __name__ == "__main__":
    main()
