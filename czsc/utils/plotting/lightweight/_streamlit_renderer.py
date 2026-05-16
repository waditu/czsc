"""Streamlit 渲染：复用离线 HTML 渲染器 + ``st.components.v1.html`` iframe 嵌入。

这样 Streamlit 版本与离线 HTML 版本 **共用同一份 JS 渲染逻辑**，所有交互（tab 切换 /
分型虚线 / 笔实线 / SMA 叠加 / 跨子图十字光标联动 / 自定义 OHLC + MACD tooltip /
图例点击 toggle / 主题切换）都跑在官方 lightweight-charts JS 里，不再依赖任何
``streamlit-lightweight-charts`` 第三方组件。Streamlit 只负责把当前的数据参数变成
``ChartPayload`` 并触发重渲染。

另外提供 ``_build_groups`` / ``render_freq`` / ``render_signal_kpi`` 三个工具函数，
方便外部（如案例脚本）按 group dict 形式直接喂给 ``streamlit-lightweight-charts``
的 ``renderLightweightCharts``，并在 Streamlit 上方渲染 "当前 K 线 signal" KPI 卡。
"""

from __future__ import annotations

from typing import Any

from . import _html_renderer, _theme
from ._data import ChartPayload, FreqPayload

__all__ = ["render", "render_freq", "render_signal_kpi"]


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


# ---- group-dict 构造（streamlit-lightweight-charts 兼容路径）-------------------


def _build_groups(
    freq: FreqPayload,
    theme: _theme.ThemeColors,
    *,
    visible: dict[str, bool] | None = None,  # noqa: ARG001  预留：未来按 series key 控制可见性
) -> list[dict[str, Any]]:
    """把单周期 ``FreqPayload`` 构造成 ``renderLightweightCharts`` 兼容的 group 列表。

    返回结构::

        [
            {"chart": {...}, "series": [candle, sma5, sma20, fx, bi]},
            {"chart": {...}, "series": [volume]},
            {"chart": {...}, "series": [diff, dea, macd_hist]},
        ]

    每个 series dict 形如 ``{"type": ..., "data": [...], "options": {...}, "markers": [...]}``。
    SignalSeries 中的所有 markers 会合并到第一个 group（主图）的第一个 series（candle）上。
    """
    # —— 主图：candle + SMA + FX + BI ——
    candle_cfg: dict[str, Any] = {
        "type": "Candlestick",
        "data": freq.main.candles,
        "options": {
            "upColor": theme["up"],
            "downColor": theme["down"],
            "borderUpColor": theme["up"],
            "borderDownColor": theme["down"],
            "wickUpColor": theme["up"],
            "wickDownColor": theme["down"],
        },
    }
    main_series: list[dict[str, Any]] = [candle_cfg]
    if freq.main.sma5:
        main_series.append(
            {
                "type": "Line",
                "data": freq.main.sma5,
                "options": {"color": theme["sma5"], "lineWidth": 1, "priceLineVisible": False},
            }
        )
    if freq.main.sma20:
        main_series.append(
            {
                "type": "Line",
                "data": freq.main.sma20,
                "options": {"color": theme["sma20"], "lineWidth": 1, "priceLineVisible": False},
            }
        )
    if freq.main.fx_line:
        main_series.append(
            {
                "type": "Line",
                "data": freq.main.fx_line,
                "options": {
                    "color": theme["fx_dashed"],
                    "lineWidth": 1,
                    "lineStyle": 2,  # Dashed
                    "priceLineVisible": False,
                },
            }
        )
    if freq.main.bi_line:
        main_series.append(
            {
                "type": "Line",
                "data": freq.main.bi_line,
                "options": {"color": theme["bi"], "lineWidth": 2, "priceLineVisible": False},
            }
        )

    # —— 合并所有 SignalSeries 的 markers 到 candle 上（candle 是 main_series[0]）——
    signal_markers: list[dict[str, Any]] = []
    for series in getattr(freq, "signals", []) or []:
        for m in series.markers:
            signal_markers.append(
                {
                    "time": m["time"],
                    "position": series.position,
                    "color": m.get("color") or series.color,
                    "shape": series.shape,
                    "text": m.get("v1", ""),
                }
            )
    if signal_markers:
        main_series[0]["markers"] = sorted(signal_markers, key=lambda x: x["time"])

    # —— Volume ——
    volume_series: list[dict[str, Any]] = [
        {
            "type": "Histogram",
            "data": freq.volume.bars,
            "options": {"priceFormat": {"type": "volume"}},
        }
    ]

    # —— MACD ——
    macd_series: list[dict[str, Any]] = []
    if freq.macd.diff:
        macd_series.append(
            {
                "type": "Line",
                "data": freq.macd.diff,
                "options": {"color": theme["macd_diff"], "lineWidth": 1, "priceLineVisible": False},
            }
        )
    if freq.macd.dea:
        macd_series.append(
            {
                "type": "Line",
                "data": freq.macd.dea,
                "options": {"color": theme["macd_dea"], "lineWidth": 1, "priceLineVisible": False},
            }
        )
    if freq.macd.macd:
        macd_series.append(
            {
                "type": "Histogram",
                "data": freq.macd.macd,
                "options": {},
            }
        )

    chart_common: dict[str, Any] = {
        "layout": {
            "background": {"type": "solid", "color": theme["background"]},
            "textColor": theme["text"],
        },
        "grid": {
            "vertLines": {"color": theme["grid"]},
            "horzLines": {"color": theme["grid"]},
        },
        "rightPriceScale": {"borderColor": theme["grid"]},
        "timeScale": {"borderColor": theme["grid"], "timeVisible": True, "secondsVisible": False},
    }

    return [
        {"chart": chart_common, "series": main_series},
        {"chart": chart_common, "series": volume_series},
        {"chart": chart_common, "series": macd_series},
    ]


def render_freq(
    freq: FreqPayload,
    theme: _theme.ThemeColors,
    *,
    key: str = "lwc-freq",
    visible: dict[str, bool] | None = None,
) -> None:
    """在 Streamlit 上把单周期 ``FreqPayload`` 用 ``streamlit-lightweight-charts``
    渲染成多 pane 组件。仅在该第三方组件已安装时可用。
    """
    try:
        from streamlit_lightweight_charts import renderLightweightCharts  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover - 可选依赖未安装的兜底
        raise ImportError(
            "render_freq 需要 'streamlit-lightweight-charts' 第三方组件，请先 pip 安装；"
            "若仅需 iframe 嵌入版本，使用 render(payload) 即可。"
        ) from e

    groups = _build_groups(freq, theme, visible=visible)
    renderLightweightCharts(groups, key=key)


def render_signal_kpi(freq: FreqPayload, *, key_prefix: str = "lwc-sig-kpi") -> None:  # noqa: ARG001  保留以维持 API 对称
    """在 Streamlit 上方渲染"最近一根 K 线上仍生效的信号"卡片。

    iframe 内无法注入 tooltip，因此用 Streamlit 原生组件代偿。展示策略：
    取 ``freq.main.candles[-1]['time']`` 时刻每个 SignalSeries 最近一条有效 marker。
    """
    import streamlit as st  # noqa: PLC0415

    if not freq.signals:
        return
    if not freq.main.candles:
        return

    cur_time = freq.main.candles[-1]["time"]
    rows: list[tuple[str, str, str]] = []  # (key, full value, color)
    for series in freq.signals:
        # 找 <= cur_time 的最后一条 marker
        candidate = [m for m in series.markers if m["time"] <= cur_time]
        if not candidate:
            continue
        last = max(candidate, key=lambda m: m["time"])
        rows.append((series.key, last["value"], series.color))

    if not rows:
        st.info("当前 K 线上无 signal 触发。")
        return

    chips = "".join(
        f'<div class="qa-kpi" style="border-left: 3px solid {color};">'
        f'<div class="qa-kpi__label">{key}</div>'
        f'<div class="qa-kpi__value">{value}</div>'
        f"</div>"
        for key, value, color in rows
    )
    st.html(f'<div class="qa-kpi-row">{chips}</div>')


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
