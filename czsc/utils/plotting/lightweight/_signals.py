"""把 generate_czsc_signals 的 DataFrame 转成可叠加到主图的 marker overlay。

中间结构与 ``_data.py`` 的协议风格保持一致：dataclass + TypedDict，HTML 与
Streamlit 端共用同一份序列化结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

import pandas as pd

__all__ = [
    "SignalMarker",
    "SignalSeries",
    "assign_palette",
    "build_signal_overlays",
    "detect_transitions",
]


class SignalMarker(TypedDict):
    time: int  # unix 秒
    value: str  # 完整 value，例如 "向上_任意_任意_0"
    v1: str  # value 第一段，用作 marker 上的文字
    color: str  # 与所属 SignalSeries.color 相同；前端渲染时直接读


@dataclass
class SignalSeries:
    key: str
    short_label: str
    color: str
    shape: str
    position: str
    markers: list[SignalMarker] = field(default_factory=list)


def detect_transitions(
    df: pd.DataFrame,
    key: str,
    *,
    include_others: bool = False,
) -> list[SignalMarker]:
    """逐行扫描 ``df[key]``，仅在 value 与上一条不同处输出 marker。

    - 非字符串 cell（NaN / 数字 / 空串）一律跳过，且**不更新** prev_value
    - 默认 ``include_others=False`` 时，``"其他"`` 视为未触发，既不画 marker 也不更新 prev_value
    - 首条有效值无论是否变化都会输出 marker（prev=None ≠ cur）
    """
    markers: list[SignalMarker] = []
    prev_value: str | None = None

    for _, row in df.iterrows():
        cur = row[key]
        if not isinstance(cur, str) or cur == "":
            continue
        if (not include_others) and ("其他" in cur):
            continue
        if cur != prev_value:
            v1 = cur.split("_", 1)[0]
            dt = row["dt"]
            # 兼容 pd.Timestamp / datetime / ISO 字符串三种 dt 表达
            ts = int(dt.timestamp()) if hasattr(dt, "timestamp") else int(pd.Timestamp(dt).timestamp())
            markers.append(SignalMarker(time=ts, value=cur, v1=v1, color=""))
            prev_value = cur
    return markers


def assign_palette(keys: list[str], palette: list[str]) -> dict[str, str]:
    """按 keys 出现顺序分配 palette 颜色；超过 palette 长度时循环回到 0。"""
    return {k: palette[i % len(palette)] for i, k in enumerate(keys)}


def _strip_freq_prefix(key: str, freq: str) -> str:
    """信号 key 形如 ``{freq}_{k2}_{k3}``；去掉 freq 前缀只留 k2_k3。"""
    prefix = f"{freq}_"
    return key[len(prefix) :] if key.startswith(prefix) else key


def _match_freq(key: str, freqs: list[str]) -> str | None:
    """按最长前缀匹配 freq；找不到返回 None（跳过该 key）。"""
    matches = [f for f in freqs if key.startswith(f"{f}_")]
    if not matches:
        return None
    return max(matches, key=len)


def build_signal_overlays(
    df: pd.DataFrame,
    *,
    freqs: list[str],
    palette: list[str],
    shapes: list[str] | None = None,
    positions: list[str] | None = None,
    include_others: bool = False,
) -> dict[str, list[SignalSeries]]:
    """把信号 DataFrame 转成 {freq → [SignalSeries]} 嵌套结构。

    - 列名前缀决定归属哪个 freq；列名不带任何已知 freq 前缀时跳过
    - 同 freq 内的 keys 按 DataFrame 列顺序分配 palette / shape / position
    - SignalMarker.color 在此函数内回填为所属 SignalSeries.color
    """
    from ._theme import SIGNAL_POSITIONS, SIGNAL_SHAPES

    shapes = shapes or SIGNAL_SHAPES
    positions = positions or SIGNAL_POSITIONS

    signal_cols = [c for c in df.columns if c not in {"dt", "symbol", "freq"}]
    buckets: dict[str, list[str]] = {f: [] for f in freqs}
    for col in signal_cols:
        freq = _match_freq(col, freqs)
        if freq is None:
            continue
        buckets[freq].append(col)

    out: dict[str, list[SignalSeries]] = {}
    for freq, keys in buckets.items():
        if not keys:
            continue
        color_map = assign_palette(keys, palette)
        series_list: list[SignalSeries] = []
        for idx, key in enumerate(keys):
            color = color_map[key]
            shape = shapes[idx % len(shapes)]
            position = positions[idx % len(positions)]
            markers = detect_transitions(df, key, include_others=include_others)
            for m in markers:
                m["color"] = color
            series_list.append(
                SignalSeries(
                    key=key,
                    short_label=_strip_freq_prefix(key, freq),
                    color=color,
                    shape=shape,
                    position=position,
                    markers=markers,
                )
            )
        out[freq] = series_list
    return out
