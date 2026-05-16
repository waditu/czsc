"""把 generate_czsc_signals 的 DataFrame 转成可叠加到主图的 marker overlay。

中间结构与 ``_data.py`` 的协议风格保持一致：dataclass + TypedDict，HTML 与
Streamlit 端共用同一份序列化结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

__all__ = [
    "SignalMarker",
    "SignalSeries",
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


def detect_transitions(*args, **kwargs):
    """T3 实现。"""
    raise NotImplementedError


def build_signal_overlays(*args, **kwargs):
    """T5 实现。"""
    raise NotImplementedError
