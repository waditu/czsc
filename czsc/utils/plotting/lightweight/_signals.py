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
            ts = int(row["dt"].timestamp())
            markers.append(
                SignalMarker(time=ts, value=cur, v1=v1, color="")
            )
            prev_value = cur
    return markers


def build_signal_overlays(*args, **kwargs):
    """T5 实现。"""
    raise NotImplementedError
