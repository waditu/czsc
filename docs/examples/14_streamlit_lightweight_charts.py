"""案例 14：Streamlit launcher · 缠论 lightweight_charts 可视化

设计思路（v3）：Streamlit 仅作为"数据参数表单 + 触发重渲染"的薄壳，所有图表交互
（tab 切换 / 自定义 tooltip / 跨子图十字光标联动 / 图例点击 toggle / 主题切换）
**直接复用案例 13 同一份 HTML 渲染器**，通过 ``st.components.v1.html`` 嵌入 iframe。
因此 Streamlit 与离线 HTML 版本在交互层面完全一致——只是参数来源从 Python 脚本
里的硬编码换成了 Streamlit 侧边栏。

这样的好处：
- 不依赖任何 ``streamlit-lightweight-charts`` 第三方组件，少一个 wheel
- 视觉 / 交互 100% 与离线 HTML 一致（同一份 JS）
- 任何 HTML 端的迭代（v4 / v5 / ...）Streamlit 自动同步

启动：
    uv run --no-sync streamlit run docs/examples/14_streamlit_lightweight_charts.py
"""

from __future__ import annotations

import datetime as _dt

import streamlit as st

from czsc import BarGenerator, Freq, format_standard_kline
from czsc._native import CzscTrader
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import _data, _streamlit_renderer, _theme

ALL_FREQS = ["30分钟", "60分钟", "日线"]


@st.cache_data(show_spinner="正在生成 mock K 线...")
def _load_bars(symbol: str, start: str, end: str, seed: int):
    df = generate_symbol_kines(symbol, "30分钟", start, end, seed=seed)
    return format_standard_kline(df, freq=Freq.F30)


def _build_trader(symbol: str, start: str, end: str, freqs: list[str], seed: int) -> CzscTrader:
    bars = _load_bars(symbol, start, end, seed)
    bg = BarGenerator(base_freq="30分钟", freqs=freqs, max_count=10000)
    for bar in bars:
        bg.update(bar)
    return CzscTrader(bg, positions=[], signals_config=[])


def main() -> None:
    st.set_page_config(
        page_title="lightweight_charts · 缠论 Quant Almanac",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 隐藏 Streamlit 默认 header + 让 iframe 占满主区域；
    # 不动 iframe 内部样式（那里完全由 _html_renderer 控制）
    st.markdown(
        """
        <style>
          [data-testid="stHeader"] { display: none !important; }
          [data-testid="stAppViewContainer"] > .main > .block-container {
            padding: 0 !important; max-width: none !important;
          }
          [data-testid="stAppViewContainer"] > .main > .block-container > [data-testid="stVerticalBlock"] {
            gap: 0 !important;
          }
          iframe[title="streamlit.components.v1.html"] {
            border: 0 !important; width: 100% !important; display: block;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("**数据参数**")
        symbol = st.text_input("Symbol", value="000001")
        date_range = st.date_input(
            "区间",
            value=(_dt.date(2023, 1, 1), _dt.date(2024, 3, 1)),
        )
        freqs = st.multiselect("周期", ALL_FREQS, default=ALL_FREQS)
        tail_bars = st.slider("最近 N 根 K 线（按周期独立截断）", 100, 2000, 500, step=50)
        seed = st.number_input("随机种子", value=42, step=1)
        st.caption("数据来自 czsc.mock.generate_symbol_kines，仅作演示。")
        st.divider()
        st.caption(
            "🎨 主题切换 / 图例 toggle / tab / tooltip 等交互均在右侧图表里完成 "
            "（与 docs/examples/_output/13_lwc_multi.html 完全一致）。"
        )

    if not freqs:
        st.warning("请至少选择一个周期")
        st.stop()
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.warning("请选择起止日期")
        st.stop()

    start = date_range[0].strftime("%Y%m%d")
    end = date_range[1].strftime("%Y%m%d")

    ct = _build_trader(symbol, start, end, freqs, int(seed))
    title = f"{symbol} · 多周期缠论结构（{' / '.join(reversed(freqs))}）" if len(freqs) > 1 else f"{symbol} · 缠论结构"
    payload = _data.build_from_trader(
        ct,
        theme=_theme.get_theme("light"),  # 初始主题；用户在 iframe 内可切到 dark
        show_sma=(5, 20),
        tail_bars=tail_bars,
        title=title,
    )

    # 整页 HTML 直接嵌入 iframe；所有交互运行在 lightweight-charts JS 里。
    _streamlit_renderer.render(payload)


if __name__ == "__main__":
    main()
