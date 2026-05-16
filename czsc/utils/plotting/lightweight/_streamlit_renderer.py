"""Streamlit 渲染：复用离线 HTML 渲染器 + ``st.components.v1.html`` iframe 嵌入。

这样 Streamlit 版本与离线 HTML 版本 **共用同一份 JS 渲染逻辑**，所有交互（tab 切换 /
分型虚线 / 笔实线 / SMA 叠加 / 跨子图十字光标联动 / 自定义 OHLC + MACD tooltip /
图例点击 toggle / 主题切换）都跑在官方 lightweight-charts JS 里，不再依赖任何
``streamlit-lightweight-charts`` 第三方组件。Streamlit 只负责把当前的数据参数变成
``ChartPayload`` 并触发重渲染。
"""

from __future__ import annotations

from . import _html_renderer
from ._data import ChartPayload

__all__ = ["render"]


def _estimate_height(payload: ChartPayload, *, h_main: int, h_vol: int, h_macd: int) -> int:
    """估算嵌入 iframe 的合适高度。

    多周期时只有 1 个 pane 可见（tab 切换），因此高度由"masthead + tabs +
    单个 pane + footer"决定。
    """
    has_tabs = len(payload.panes) > 1
    masthead = 130
    tabs = 50 if has_tabs else 0
    pane_meta = 56
    chart_stack = h_main + h_vol + h_macd + 4
    pane_padding = 16 + 32
    footer = 70
    return masthead + tabs + pane_meta + chart_stack + pane_padding + footer + 24


def render(
    payload: ChartPayload,
    *,
    key_prefix: str = "lwc",  # noqa: ARG001  保留以维持 API 向后兼容
    height: int | None = None,
    height_main: int = 420,
    height_vol: int = 130,
    height_macd: int = 170,
) -> None:
    """把整页 HTML 通过 ``st.components.v1.html`` 注入 iframe。

    所有交互（tab / tooltip / 主题切换 / 图例 toggle / 跨子图十字光标联动）都在
    iframe 内 JS 中运行；Streamlit 仅提供数据参数 → ``ChartPayload`` → 重渲染。
    """
    import streamlit.components.v1 as components  # noqa: PLC0415

    html = _html_renderer.render(
        payload,
        height_main=height_main,
        height_vol=height_vol,
        height_macd=height_macd,
    )
    iframe_h = height or _estimate_height(payload, h_main=height_main, h_vol=height_vol, h_macd=height_macd)
    components.html(html, height=iframe_h, scrolling=True)
