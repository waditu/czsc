"""把 CZSC / CzscTrader 转成 lightweight-charts 能直接消费的 ``ChartPayload``。

中间结构是整个可视化层的"协议"——HTML 端与 Streamlit 端都只读这一份数据，
CZSC 对象不会泄漏到 JS 端。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict, cast

import numpy as np

from czsc._native import CZSC
from czsc._native.ta import sma as _sma_rust

from . import _theme

__all__ = [
    "Candle",
    "ChartPayload",
    "FreqPayload",
    "Histogram",
    "LinePoint",
    "MacdPane",
    "MainPane",
    "VolumePane",
    "build_from_czsc",
    "build_from_trader",
]


# -- TypedDicts（JSON 友好）------------------------------------------------------


class Candle(TypedDict):
    time: int
    open: float
    high: float
    low: float
    close: float


class LinePoint(TypedDict):
    time: int
    value: float | None


class Histogram(TypedDict):
    time: int
    value: float | None
    color: str


# -- Dataclasses（业务侧使用）---------------------------------------------------


@dataclass
class MainPane:
    candles: list[Candle] = field(default_factory=list)
    sma5: list[LinePoint] = field(default_factory=list)
    sma20: list[LinePoint] = field(default_factory=list)
    fx_line: list[LinePoint] = field(default_factory=list)  # 虚线，连接所有分型
    bi_line: list[LinePoint] = field(default_factory=list)  # 实线，仅笔的端点


@dataclass
class VolumePane:
    bars: list[Histogram] = field(default_factory=list)


@dataclass
class MacdPane:
    diff: list[LinePoint] = field(default_factory=list)
    dea: list[LinePoint] = field(default_factory=list)
    macd: list[Histogram] = field(default_factory=list)


@dataclass
class FreqPayload:
    freq_label: str
    main: MainPane
    volume: VolumePane
    macd: MacdPane
    signals: list[Any] = field(default_factory=list)  # list[SignalSeries]，避免循环 import 用 Any


@dataclass
class ChartPayload:
    symbol: str
    title: str
    panes: list[FreqPayload]
    theme: _theme.ThemeColors

    def to_dict(self) -> dict[str, Any]:
        """转成嵌套 dict 方便 ``json.dumps``；NaN/inf 已在构造时处理为 None。"""
        return asdict(self)


# -- 构造逻辑 ------------------------------------------------------------------


def _ts(dt: Any) -> int:
    """pd.Timestamp / datetime → unix 秒整数。"""
    if hasattr(dt, "timestamp"):
        return int(dt.timestamp())
    raise TypeError(f"unsupported dt type: {type(dt)!r}")


def _none_if_nan(value: float) -> float | None:
    return None if math.isnan(value) else float(value)


def _macd(close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """局部封装 plotting 内部 MACD（×2 约定），避免在 import 阶段拉入。"""
    from czsc.utils.plotting._macd import compute_macd  # noqa: PLC0415

    diff, dea, macd = compute_macd(close)
    return diff, dea, macd


def _sma(close: np.ndarray, n: int) -> np.ndarray:
    """优先调用 Rust 端 ``_native.ta.sma``；返回与 close 等长的数组。"""
    res = np.asarray(_sma_rust(close, n=n), dtype=float)
    if res.shape[0] != close.shape[0]:
        # 防御：理论上 Rust 端返回等长序列，这里只做安全兜底
        padded = np.full_like(close, np.nan, dtype=float)
        padded[-res.shape[0] :] = res
        return padded
    return res


def _build_main_pane(c: CZSC, theme: _theme.ThemeColors, *, show_sma: Sequence[int]) -> MainPane:
    bars = list(c.bars_raw)
    candles: list[Candle] = []
    closes: list[float] = []
    times: list[int] = []
    for b in bars:
        t = _ts(b.dt)
        times.append(t)
        closes.append(float(b.close))
        candles.append(
            cast(
                Candle,
                {
                    "time": t,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                },
            )
        )

    close_arr = np.asarray(closes, dtype=float) if closes else np.empty(0, dtype=float)

    def _sma_series(n: int) -> list[LinePoint]:
        if close_arr.size == 0 or n not in tuple(show_sma):
            return []
        values = _sma(close_arr, n)
        return [
            cast(LinePoint, {"time": times[i], "value": _none_if_nan(float(values[i]))}) for i in range(close_arr.size)
        ]

    sma5 = _sma_series(5)
    sma20 = _sma_series(20)

    # 分型：所有 FX 顶点按时间升序连成一条线（渲染时设为虚线，区别于 笔 的实线）
    fx_pairs: list[tuple[int, float]] = [(_ts(fx.dt), float(fx.fx)) for fx in c.fx_list]
    fx_pairs.sort(key=lambda p: p[0])
    # 同 time 去重，保留首个
    seen_t: set[int] = set()
    fx_line: list[LinePoint] = []
    for t, v in fx_pairs:
        if t in seen_t:
            continue
        seen_t.add(t)
        fx_line.append(cast(LinePoint, {"time": t, "value": v}))

    # 笔：fx_a 顶点序列 + 末笔的 fx_b
    bi_line: list[LinePoint] = []
    bis = list(c.bi_list)
    if bis:
        for bi in bis:
            bi_line.append(cast(LinePoint, {"time": _ts(bi.fx_a.dt), "value": float(bi.fx_a.fx)}))
        bi_line.append(cast(LinePoint, {"time": _ts(bis[-1].fx_b.dt), "value": float(bis[-1].fx_b.fx)}))
        # 同 time 去重（防止 fx_a 与上一笔 fx_b 完全同 time），保留后者
        dedup: dict[int, LinePoint] = {}
        for p in bi_line:
            dedup[p["time"]] = p
        bi_line = sorted(dedup.values(), key=lambda p: p["time"])

    return MainPane(candles=candles, sma5=sma5, sma20=sma20, fx_line=fx_line, bi_line=bi_line)


def _build_volume_pane(c: CZSC, theme: _theme.ThemeColors) -> VolumePane:
    bars: list[Histogram] = []
    for b in c.bars_raw:
        up = float(b.close) >= float(b.open)
        bars.append(
            cast(
                Histogram,
                {
                    "time": _ts(b.dt),
                    "value": float(b.vol),
                    "color": theme["up"] if up else theme["down"],
                },
            )
        )
    return VolumePane(bars=bars)


def _build_macd_pane(c: CZSC, theme: _theme.ThemeColors) -> MacdPane:
    bars = list(c.bars_raw)
    if not bars:
        return MacdPane()
    times = [_ts(b.dt) for b in bars]
    closes = np.asarray([float(b.close) for b in bars], dtype=float)
    diff, dea, macd_hist = _macd(closes)
    diff_pts = [cast(LinePoint, {"time": times[i], "value": _none_if_nan(float(diff[i]))}) for i in range(len(bars))]
    dea_pts = [cast(LinePoint, {"time": times[i], "value": _none_if_nan(float(dea[i]))}) for i in range(len(bars))]
    macd_pts: list[Histogram] = []
    for i in range(len(bars)):
        v = float(macd_hist[i])
        macd_pts.append(
            cast(
                Histogram,
                {
                    "time": times[i],
                    "value": _none_if_nan(v),
                    "color": theme["up"] if v >= 0 else theme["down"],
                },
            )
        )
    return MacdPane(diff=diff_pts, dea=dea_pts, macd=macd_pts)


def _tail_freq_payload(fp: FreqPayload, n: int) -> FreqPayload:
    """按 candles 的最后 n 根截断同周期的所有 series。"""
    if n <= 0 or n >= len(fp.main.candles):
        return fp
    cutoff = fp.main.candles[-n]["time"]

    def _filter(seq: list[Any], key: str = "time") -> list[Any]:
        return [x for x in seq if x[key] >= cutoff]

    fp.main.candles = _filter(fp.main.candles)
    fp.main.sma5 = _filter(fp.main.sma5)
    fp.main.sma20 = _filter(fp.main.sma20)
    fp.main.fx_line = _filter(fp.main.fx_line)
    fp.main.bi_line = _filter(fp.main.bi_line)
    fp.volume.bars = _filter(fp.volume.bars)
    fp.macd.diff = _filter(fp.macd.diff)
    fp.macd.dea = _filter(fp.macd.dea)
    fp.macd.macd = _filter(fp.macd.macd)
    return fp


def _build_freq_payload(
    freq_label: str,
    c: CZSC,
    theme: _theme.ThemeColors,
    *,
    show_sma: Sequence[int],
    tail_bars: int | None,
) -> FreqPayload:
    fp = FreqPayload(
        freq_label=freq_label,
        main=_build_main_pane(c, theme, show_sma=show_sma),
        volume=_build_volume_pane(c, theme),
        macd=_build_macd_pane(c, theme),
    )
    if tail_bars is not None:
        _tail_freq_payload(fp, tail_bars)
    return fp


def build_from_czsc(
    c: CZSC,
    *,
    theme: _theme.ThemeColors | None = None,
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
    title: str | None = None,
) -> ChartPayload:
    """单周期：把一个 ``CZSC`` 实例转成 ``ChartPayload``。"""
    theme = theme or _theme.get_theme("light")
    freq_label = str(c.freq.value) if hasattr(c.freq, "value") else str(c.freq)
    pane = _build_freq_payload(freq_label, c, theme, show_sma=show_sma, tail_bars=tail_bars)
    return ChartPayload(
        symbol=str(c.symbol),
        title=title or f"{c.symbol} 缠论结构（{freq_label}）",
        panes=[pane],
        theme=theme,
    )


def build_from_trader(
    ct: Any,  # CzscSignals 也可，无须强约束（只依赖 .symbol / .kas）
    *,
    theme: _theme.ThemeColors | None = None,
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
    title: str | None = None,
) -> ChartPayload:
    """多周期：传入任何有 ``symbol`` + ``kas: dict[str, CZSC]`` 的对象。

    覆盖 ``CzscTrader`` / ``CzscSignals`` 两类，避免对二者形成强类型耦合。
    """
    if not hasattr(ct, "kas") or not hasattr(ct, "symbol"):
        raise TypeError("ct must expose `.symbol` and `.kas: dict[str, CZSC]`")

    theme = theme or _theme.get_theme("light")
    from czsc.utils import freqs_sorted as _freqs_sorted  # noqa: PLC0415

    kas: dict[str, CZSC] = dict(ct.kas)
    # 大周期在上、小周期在下 —— freqs_sorted 返回从小到大，这里反转
    sorted_freqs = list(reversed(_freqs_sorted(list(kas.keys()))))

    panes = [
        _build_freq_payload(freq_label, kas[freq_label], theme, show_sma=show_sma, tail_bars=tail_bars)
        for freq_label in sorted_freqs
        if freq_label in kas
    ]
    return ChartPayload(
        symbol=str(ct.symbol),
        title=title or f"{ct.symbol} 缠论结构（多周期：{' / '.join(p.freq_label for p in panes)}）",
        panes=panes,
        theme=theme,
    )
