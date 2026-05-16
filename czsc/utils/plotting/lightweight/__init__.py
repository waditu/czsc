"""lightweight_charts 缠论可视化：对外仅暴露 ``plot_czsc`` 与 ``plot_czsc_trader``。

设计要点：

- ``plot_czsc(c, output=...)``        — 接 ``CZSC`` 对象（单周期）
- ``plot_czsc_trader(ct, output=...)`` — 接 ``CzscTrader`` / ``CzscSignals``（多周期）
- ``output="html"``      → 写文件到 ``path``（或返回 HTML 字符串）
- ``output="streamlit"`` → 通过 ``st.components.v1.html`` 嵌 iframe，复用 HTML
  渲染器的全部交互（tab / tooltip / 主题切换 / 图例 toggle / 跨子图十字光标联动）

每个周期展开为 3 个 sub-pane：主图（K + SMA5 + SMA20 + 分型 + 笔）+ 副图1 成交量 +
副图2 MACD。颜色与项目 Plotly 版 ``KlineChart`` 对齐，避免红绿互换迷惑。

零第三方运行时依赖：HTML 模板用 Python 标准库 ``string.Template``；Streamlit 嵌入
用 ``streamlit.components.v1.html``，不依赖 ``streamlit-lightweight-charts`` 等组件。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from czsc._native import CZSC

from . import _data, _html_renderer, _signals, _streamlit_renderer, _theme

OutputType = Literal["html", "streamlit"]

__all__ = ["plot_czsc", "plot_czsc_signals", "plot_czsc_trader"]


def _dispatch(payload: _data.ChartPayload, *, output: OutputType, path: str | Path | None) -> str | None:
    if output == "html":
        html = _html_renderer.render(payload)
        if path is None:
            return html
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(html, encoding="utf-8")
        return str(path)
    if output == "streamlit":
        _streamlit_renderer.render(payload)
        return None
    raise ValueError(f"unknown output={output!r}; expected 'html' or 'streamlit'")


def plot_czsc(
    c: CZSC,
    *,
    output: OutputType = "html",
    path: str | Path | None = None,
    title: str | None = None,
    theme: _theme.ThemeName = "light",
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
) -> str | None:
    """单周期：把 ``CZSC`` 对象画成 lightweight-charts 三 sub-pane 图。

    :param c: ``CZSC`` 实例
    :param output: ``"html"``（默认）或 ``"streamlit"``
    :param path: HTML 模式下落盘路径；为 ``None`` 时返回 HTML 字符串
    :param title: 网页 / 标题文字；默认 ``"<symbol> 缠论结构（<freq>）"``
    :param theme: ``"light"`` 或 ``"dark"``
    :param show_sma: 主图叠加的 SMA 周期序列；默认 ``(5, 20)``
    :param tail_bars: 只渲染最近 N 根 K 线；为 ``None`` 时全量

    :return: HTML 模式下若 ``path`` 为空返回 HTML 字符串、否则返回写入路径；Streamlit 模式恒返回 ``None``

    示例::

        from czsc import CZSC, Freq, format_standard_kline
        from czsc.mock import generate_symbol_kines
        from czsc.utils.plotting.lightweight import plot_czsc

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20240101", seed=42)
        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        plot_czsc(c, output="html", path="out/chan.html")
    """
    payload = _data.build_from_czsc(
        c,
        theme=_theme.get_theme(theme),
        show_sma=show_sma,
        tail_bars=tail_bars,
        title=title,
    )
    return _dispatch(payload, output=output, path=path)


def plot_czsc_trader(
    ct: Any,
    *,
    output: OutputType = "html",
    path: str | Path | None = None,
    title: str | None = None,
    theme: _theme.ThemeName = "light",
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
) -> str | None:
    """多周期：把任何有 ``symbol`` + ``kas`` 的对象（``CzscTrader`` / ``CzscSignals``）画成多 pane 图。

    周期顺序：从大到小（日线 → 60 分钟 → 30 分钟 …），符合主图 / 大盘在上的视觉习惯。

    参数语义与 :func:`plot_czsc` 一致。

    示例::

        from czsc import CzscTrader, BarGenerator, Freq, format_standard_kline
        from czsc.mock import generate_symbol_kines
        from czsc.utils.plotting.lightweight import plot_czsc_trader

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20240101", seed=42)
        bars = format_standard_kline(df, freq=Freq.F30)
        bg = BarGenerator(base_freq="30分钟", freqs=["30分钟","60分钟","日线"], max_count=5000)
        for b in bars:
            bg.update(b)
        ct = CzscTrader(bg, positions=[], signals_config=[])
        plot_czsc_trader(ct, output="html", path="out/chan_multi.html")
    """
    payload = _data.build_from_trader(
        ct,
        theme=_theme.get_theme(theme),
        show_sma=show_sma,
        tail_bars=tail_bars,
        title=title,
    )
    return _dispatch(payload, output=output, path=path)


def plot_czsc_signals(
    bars: list,
    *,
    signals_config: list[dict],
    output: OutputType = "html",
    path: str | Path | None = None,
    title: str | None = None,
    theme: _theme.ThemeName = "dark",
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
    sdt: str = "20170101",
    init_n: int = 500,
    include_others: bool = True,
) -> str | None:
    """把若干信号函数在 ``bars`` 上的历史触发点叠加到 lightweight-charts 主图。

    流程：
    1. 用 ``signals_config`` 推断需要的 freqs，构造 ``CzscTrader``
    2. ``generate_czsc_signals(df=True)`` 拿到 key/value DataFrame
    3. ``build_signal_overlays`` 计算 transition marker + palette 分配
    4. 复用 ``build_from_trader`` 得到 K/缠论 payload，注入 signals 字段
    5. 按 ``output`` 分发到 HTML / Streamlit 渲染器

    Args:
        bars: 基础周期 K 线列表（``RawBar``）。
        signals_config: 信号配置，结构同 ``generate_czsc_signals``。
        output: ``"html"`` 或 ``"streamlit"``。
        path: HTML 模式下落盘路径，为 ``None`` 时返回 HTML 字符串。
        title: 网页标题；缺省自动生成。
        theme: ``"light"`` / ``"dark"``。默认 ``"dark"``。
        show_sma: 主图 SMA 周期序列。
        tail_bars: 截断到最近 N 根；为 ``None`` 不截断。
        sdt: 信号开始计算日期，透传给 ``generate_czsc_signals``。
        init_n: 预热 K 线数，透传给 ``generate_czsc_signals``。
        include_others: ``True`` 时不过滤 "其他"；默认 ``True``。

    Note:
        HTML 模式下当前在浏览器内切换 LIGHT/DARK 主题时，K 线 / SMA / FX / BI / MACD
        会跟随重染色，但 signal marker 颜色保持构建时的 palette（即生成 HTML 时
        ``theme=`` 决定 light 或 dark palette）。若需要切换主题后 marker 也重染色，
        在调用本函数时按目标主题分别生成两份 HTML 即可。后续版本计划在 payload 中
        同时携带 light / dark 两套 palette，由 JS 在 ``applyTheme`` 时切换。
    """
    from czsc._native import BarGenerator, CzscTrader  # noqa: PLC0415
    from czsc.traders import generate_czsc_signals, get_signals_freqs  # noqa: PLC0415

    if not bars:
        raise ValueError("bars 不能为空")

    # 给缺失 ``params`` 的配置补上空字典，避免 Rust 端 derive_signals_freqs 反序列化失败
    normalized_config = [({**cfg, "params": {}} if "params" not in cfg else cfg) for cfg in signals_config]
    freqs = get_signals_freqs(normalized_config) or [str(bars[0].freq)]
    base_freq = str(bars[0].freq)
    if base_freq not in freqs:
        freqs = [base_freq, *freqs]

    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=max(10000, len(bars)))
    for bar in bars:
        bg.update(bar)
    ct = CzscTrader(bg, positions=[], signals_config=[])

    theme_cols = _theme.get_theme(theme)
    payload = _data.build_from_trader(
        ct,
        theme=theme_cols,
        show_sma=show_sma,
        tail_bars=tail_bars,
        title=title,
    )

    # 注：generate_czsc_signals 容忍 params 缺失（Rust 端走 default），无需 normalize；
    # 仅 derive_signals_freqs（上面 freqs 推断处）才必须显式 params={}。
    df = generate_czsc_signals(
        bars,
        signals_config=signals_config,
        sdt=sdt,
        init_n=init_n,
        df=True,
    )
    palette = _theme.get_signal_palette(theme)
    overlays = _signals.build_signal_overlays(
        df,
        freqs=freqs,
        palette=palette,
        include_others=include_others,
    )

    for pane in payload.panes:
        series = overlays.get(pane.freq_label, [])
        # 按 tail_bars 同步裁剪 marker
        if tail_bars is not None and pane.main.candles:
            cutoff_ts = pane.main.candles[0]["time"]
            series = [
                _signals.SignalSeries(
                    key=s.key,
                    short_label=s.short_label,
                    color=s.color,
                    shape=s.shape,
                    position=s.position,
                    markers=[m for m in s.markers if m["time"] >= cutoff_ts],
                )
                for s in series
            ]
        pane.signals = series  # type: ignore[assignment]

    return _dispatch(payload, output=output, path=path)
