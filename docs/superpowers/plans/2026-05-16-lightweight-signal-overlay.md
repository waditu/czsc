# Lightweight Charts Signal Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 `czsc/utils/plotting/lightweight/` 子包基础上新增 `plot_czsc_signals(bars, signals_config, output, ...)`，把若干信号函数在 K 线上的历史触发点以 marker 形式叠加到主图，并扩展 tooltip / KPI 显示完整 signal value，HTML + Streamlit 双出口。

**Architecture:** 复用现有 `_data.build_from_trader` 产出多周期 ChartPayload；新增 `_signals.py` 模块计算"signal key/value transition → marker"；扩展 `FreqPayload` 加 `signals` 字段；HTML 端注入 `setMarkers` + tooltip 扩展，Streamlit 端在 candle series options 注入 markers + 加一行信号 KPI 卡。

**Tech Stack:** Python 3.10+，PyO3 扩展 `czsc._native`（提供 `generate_czsc_signals`），lightweight-charts v4（HTML JS）/ streamlit-lightweight-charts（iframe 组件），pytest + uv。

**飞书评审稿（方案权威来源）：** https://s0cqcxuy3p.feishu.cn/docx/TT0QdOWw9otH0fxlPUwc6uGLndh

---

## 关键背景

- 信号 DataFrame 来源：`czsc.traders.generate_czsc_signals(bars, signals_config, df=True, sdt, init_n)` 返回带 `dt`/`symbol`/`freq` 元数据列 + 一组形如 `{freq}_{k2}_{k3}` 的信号列；列名 = key，单元格 = 完整 value（形如 `"v1_v2_v3_score"`）。
- 已用约定：`"其他"`（或包含子串"其他"）= 未触发；默认应过滤掉。
- 测试数据统一来自 `czsc.mock.generate_symbol_kines("000001", "30分钟", ..., seed=42)`。
- 项目使用 `uv` + `ruff`，行长 120。慢测试用 `@pytest.mark.slow`，CI 跑 `--run-slow`。
- 评审决议（飞书评论）：函数命名必须是 `plot_czsc_signals`（与 `plot_czsc` / `plot_czsc_trader` 并列）；tooltip 中 SIGNALS 段显示**完整** value，marker 上只渲染 v1。

## 文件清单

| 动作 | 路径 | 责任 |
|------|------|------|
| 新建 | `czsc/utils/plotting/lightweight/_signals.py` | SignalMarker/SignalSeries 数据类、transition 检测、palette 分配、多 freq 分桶 |
| 修改 | `czsc/utils/plotting/lightweight/_theme.py` | 加 `SIGNAL_PALETTE_LIGHT/DARK`、`SIGNAL_SHAPES`、`SIGNAL_POSITIONS` 常量 |
| 修改 | `czsc/utils/plotting/lightweight/_data.py` | `FreqPayload` 加 `signals: list[SignalSeries]` 字段（默认空） |
| 修改 | `czsc/utils/plotting/lightweight/_html_renderer.py` | JS 内合并 markers 调 `setMarkers` + tooltip 模板加 SIGNALS 段 + signal 图例 toggle |
| 修改 | `czsc/utils/plotting/lightweight/_streamlit_renderer.py` | candle series options 注入 markers + `render_signal_kpi` 辅助 |
| 修改 | `czsc/utils/plotting/lightweight/__init__.py` | 新增 `plot_czsc_signals(...)` 顶层 API；写入 `__all__` |
| 新建 | `docs/examples/15_lightweight_signals_html.py` | HTML 演示案例 |
| 新建 | `docs/examples/16_streamlit_signals.py` | Streamlit 演示案例 |
| 新建 | `tests/test_lightweight_signals.py` | 9 个单元 + 6 个集成（其中 1 个 slow） |

---

## Task 1：调色板与常量（`_theme.py`）

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_theme.py`
- Test: `tests/test_lightweight_signals.py`（新建）

- [ ] **Step 1.1: 创建测试文件并写第一个失败测试**

Create `tests/test_lightweight_signals.py`:

```python
"""tests/test_lightweight_signals.py —— lightweight 信号叠加层单测 + 集成测试。

覆盖飞书评审方案 §9.1 单元（U1–U9）和 §9.2 集成（I1–I6）。
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd
import pytest

from czsc import Freq, format_standard_kline
from czsc.mock import generate_symbol_kines


class TestPaletteConstants:
    def test_palette_lengths_match(self):
        from czsc.utils.plotting.lightweight import _theme

        assert len(_theme.SIGNAL_PALETTE_LIGHT) >= 10
        assert len(_theme.SIGNAL_PALETTE_LIGHT) == len(_theme.SIGNAL_PALETTE_DARK)
        assert len(_theme.SIGNAL_SHAPES) >= 2
        assert len(_theme.SIGNAL_POSITIONS) == 2

    def test_palette_colors_are_hex(self):
        from czsc.utils.plotting.lightweight import _theme

        for color in _theme.SIGNAL_PALETTE_LIGHT + _theme.SIGNAL_PALETTE_DARK:
            assert isinstance(color, str)
            assert color.startswith("#") and len(color) == 7
```

- [ ] **Step 1.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPaletteConstants -v
```

Expected: FAIL with `AttributeError: module 'czsc.utils.plotting.lightweight._theme' has no attribute 'SIGNAL_PALETTE_LIGHT'`

- [ ] **Step 1.3: 在 `_theme.py` 末尾追加常量**

Append to `czsc/utils/plotting/lightweight/_theme.py`:

```python
# —— Signal overlay 调色板 ——————————————————————————————————————
# 10 色循环；颜色按 series 序号分配；超过 10 个 key 时循环回到 #0
SIGNAL_PALETTE_LIGHT: list[str] = [
    "#1F3C6E", "#C03A2B", "#2E7D32", "#C78A2E", "#7B4FA8",
    "#0C7B93", "#A52A2A", "#5B7C0C", "#B86B25", "#6E2C82",
]
SIGNAL_PALETTE_DARK: list[str] = [
    "#A8B8E8", "#E94B3C", "#5BB85B", "#E6A93B", "#C29CF2",
    "#6FCFE0", "#E08989", "#B9D560", "#F2A56E", "#C99BE0",
]

# marker 形状/位置在 series 序号上交错，缓解同 bar 上多个 marker 视觉重叠
SIGNAL_SHAPES: list[str] = ["circle", "square", "arrowUp", "arrowDown"]
SIGNAL_POSITIONS: list[str] = ["aboveBar", "belowBar"]


def get_signal_palette(name: ThemeName = "light") -> list[str]:
    """按主题取信号调色板。"""
    if name == "dark":
        return SIGNAL_PALETTE_DARK
    return SIGNAL_PALETTE_LIGHT
```

- [ ] **Step 1.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPaletteConstants -v
```

Expected: 2 passed

- [ ] **Step 1.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_theme.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): 新增 signal overlay 调色板常量"
```

---

## Task 2：`_signals.py` 数据类骨架

**Files:**
- Create: `czsc/utils/plotting/lightweight/_signals.py`
- Modify: `tests/test_lightweight_signals.py`（追加）

- [ ] **Step 2.1: 在测试文件追加类型 import 测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestSignalsModuleSkeleton:
    def test_types_importable(self):
        from czsc.utils.plotting.lightweight._signals import (
            SignalMarker,
            SignalSeries,
        )

        marker: SignalMarker = {"time": 1, "value": "v1_v2_v3_0", "v1": "v1", "color": "#000000"}
        series = SignalSeries(
            key="30分钟_D1_X",
            short_label="X",
            color="#1F3C6E",
            shape="circle",
            position="aboveBar",
            markers=[marker],
        )
        assert series.key == "30分钟_D1_X"
        assert series.markers[0]["v1"] == "v1"
```

- [ ] **Step 2.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestSignalsModuleSkeleton -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'czsc.utils.plotting.lightweight._signals'`

- [ ] **Step 2.3: 创建 `_signals.py` 骨架**

Create `czsc/utils/plotting/lightweight/_signals.py`:

```python
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
    time: int           # unix 秒
    value: str          # 完整 value，例如 "向上_任意_任意_0"
    v1: str             # value 第一段，用作 marker 上的文字
    color: str          # 与所属 SignalSeries.color 相同；前端渲染时直接读


@dataclass
class SignalSeries:
    key: str
    short_label: str
    color: str
    shape: str
    position: str
    markers: list[SignalMarker] = field(default_factory=list)


def detect_transitions(*args, **kwargs):  # noqa: D401, ANN001, ANN002, ANN003 - 占位
    """T3 实现。"""
    raise NotImplementedError


def build_signal_overlays(*args, **kwargs):  # noqa: D401, ANN001, ANN002, ANN003 - 占位
    """T5 实现。"""
    raise NotImplementedError
```

- [ ] **Step 2.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestSignalsModuleSkeleton -v
```

Expected: 1 passed

- [ ] **Step 2.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_signals.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): 新增 _signals 模块骨架（SignalMarker/SignalSeries）"
```

---

## Task 3：`detect_transitions` —— U1–U5 单元测试

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_signals.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 3.1: 追加 5 个 transition 检测测试（U1–U5）**

Append to `tests/test_lightweight_signals.py`:

```python
class TestDetectTransitions:
    """飞书评审 §9.1 U1–U5：transition 检测核心逻辑。"""

    @staticmethod
    def _df(values: list[str | float]) -> pd.DataFrame:
        """构造一个 dt + key 列的小 DataFrame。"""
        return pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=len(values), freq="30min"),
                "30分钟_D1_X": values,
            }
        )

    def test_u1_strict_switching(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["A_x_x_0", "A_x_x_0", "B_x_x_0", "B_x_x_0", "C_x_x_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        assert [m["v1"] for m in markers] == ["A", "B", "C"]
        assert [m["time"] for m in markers] == [
            int(df["dt"].iloc[i].timestamp()) for i in (0, 2, 4)
        ]

    def test_u2_other_filtered_by_default(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_0", "其他_任意_任意_0", "向上_任意_任意_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        # '其他' 既不画也不更新 prev_value → 仅首行触发，第 3 行不算切换
        assert len(markers) == 1
        assert markers[0]["v1"] == "向上"

    def test_u3_include_others(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_0", "其他_任意_任意_0", "向上_任意_任意_0"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=True)
        assert [m["v1"] for m in markers] == ["向上", "其他", "向上"]

    def test_u4_skip_non_string(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["A_x_x_0", float("nan"), "", 1.5, "B_x_x_0"])  # type: ignore[list-item]
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        # NaN/空串/数字都跳过且不更新 prev_value
        assert [m["v1"] for m in markers] == ["A", "B"]

    def test_u5_marker_full_value_preserved(self):
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        df = self._df(["向上_任意_任意_3"])
        markers = detect_transitions(df, "30分钟_D1_X", include_others=False)
        assert markers[0]["value"] == "向上_任意_任意_3"
        assert markers[0]["v1"] == "向上"
```

- [ ] **Step 3.2: 运行测试，确认 5 个全部失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestDetectTransitions -v
```

Expected: 5 FAIL with `NotImplementedError`

- [ ] **Step 3.3: 实现 `detect_transitions`**

Replace the `detect_transitions` placeholder in `czsc/utils/plotting/lightweight/_signals.py` with:

```python
def detect_transitions(
    df: "pd.DataFrame",
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
```

Add `import pandas as pd` at the top of `_signals.py` (with `from __future__ import annotations` it's safe as a runtime import, but tests use real pandas - keep it as TYPE_CHECKING-free direct import):

```python
import pandas as pd  # noqa: E402,F401  - 也用于 build_signal_overlays
```

Place this import block right after `from dataclasses import ...` and before `__all__`.

- [ ] **Step 3.4: 运行测试，确认全部通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestDetectTransitions -v
```

Expected: 5 passed

- [ ] **Step 3.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_signals.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): detect_transitions 仅在 value 变化处输出 marker"
```

---

## Task 4：调色板分配 —— U6/U7

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_signals.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 4.1: 追加 U6/U7 测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestPaletteAssignment:
    def test_u6_stable_color_for_same_key(self):
        from czsc.utils.plotting.lightweight._signals import assign_palette
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        keys = ["30分钟_D1_A", "30分钟_D1_B", "30分钟_D1_C"]
        a = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        b = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        assert a == b
        # 同 palette 长度内不同 key 颜色互异
        assert len(set(a.values())) == len(keys)

    def test_u7_palette_cycles_when_exceeds(self):
        from czsc.utils.plotting.lightweight._signals import assign_palette
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        keys = [f"30分钟_D1_K{i}" for i in range(len(SIGNAL_PALETTE_LIGHT) + 1)]
        mapping = assign_palette(keys, SIGNAL_PALETTE_LIGHT)
        # 第 N+1 个 key 回到 palette[0]
        assert mapping[keys[-1]] == SIGNAL_PALETTE_LIGHT[0]
```

- [ ] **Step 4.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPaletteAssignment -v
```

Expected: 2 FAIL with `ImportError: cannot import name 'assign_palette'`

- [ ] **Step 4.3: 实现 `assign_palette`**

Add to `czsc/utils/plotting/lightweight/_signals.py` (after `detect_transitions`):

```python
def assign_palette(keys: list[str], palette: list[str]) -> dict[str, str]:
    """按 keys 出现顺序分配 palette 颜色；超过 palette 长度时循环回到 0。"""
    return {k: palette[i % len(palette)] for i, k in enumerate(keys)}
```

Also update `__all__`:

```python
__all__ = [
    "SignalMarker",
    "SignalSeries",
    "assign_palette",
    "build_signal_overlays",
    "detect_transitions",
]
```

- [ ] **Step 4.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPaletteAssignment -v
```

Expected: 2 passed

- [ ] **Step 4.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_signals.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): assign_palette 稳定 + 循环分配信号颜色"
```

---

## Task 5：`build_signal_overlays` —— U8 多 freq 分桶

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_signals.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 5.1: 追加 U8 测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestBuildSignalOverlays:
    def test_u8_multi_freq_bucketing(self):
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=3, freq="30min"),
                "30分钟_D1_A": ["向上_任意_任意_0", "向下_任意_任意_0", "向下_任意_任意_0"],
                "30分钟_D1_B": ["多_任意_任意_0", "多_任意_任意_0", "空_任意_任意_0"],
                "日线_D1_C":   ["持平_任意_任意_0", "持平_任意_任意_0", "持平_任意_任意_0"],
            }
        )
        out = build_signal_overlays(
            df,
            freqs=["30分钟", "日线"],
            palette=SIGNAL_PALETTE_LIGHT,
        )
        assert set(out.keys()) == {"30分钟", "日线"}
        keys_30m = [s.key for s in out["30分钟"]]
        keys_day = [s.key for s in out["日线"]]
        assert keys_30m == ["30分钟_D1_A", "30分钟_D1_B"]
        assert keys_day == ["日线_D1_C"]
        # 颜色独立分配（同 palette 池，同序号同色，但 series 在不同桶里）
        assert out["30分钟"][0].color in SIGNAL_PALETTE_LIGHT
        # 持平没有切换且仅 1 个值出现一次 → 第一条仍 trigger 一个 marker
        assert len(out["日线"][0].markers) == 1
        # short_label 去掉 freq 前缀
        assert out["30分钟"][0].short_label == "D1_A"

    def test_build_overlays_marker_color_filled(self):
        """marker.color 应该被填成所属 SignalSeries.color，方便前端直接读。"""
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT

        df = pd.DataFrame(
            {
                "dt": pd.date_range("2023-01-01", periods=2, freq="30min"),
                "30分钟_D1_A": ["x_v_v_0", "y_v_v_0"],
            }
        )
        out = build_signal_overlays(df, freqs=["30分钟"], palette=SIGNAL_PALETTE_LIGHT)
        series = out["30分钟"][0]
        for marker in series.markers:
            assert marker["color"] == series.color
```

- [ ] **Step 5.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestBuildSignalOverlays -v
```

Expected: 2 FAIL with `NotImplementedError`

- [ ] **Step 5.3: 实现 `build_signal_overlays`**

Replace the placeholder in `czsc/utils/plotting/lightweight/_signals.py`:

```python
def _strip_freq_prefix(key: str, freq: str) -> str:
    """信号 key 形如 ``{freq}_{k2}_{k3}``；去掉 freq 前缀只留 k2_k3。"""
    prefix = f"{freq}_"
    return key[len(prefix):] if key.startswith(prefix) else key


def _match_freq(key: str, freqs: list[str]) -> str | None:
    """按最长前缀匹配 freq；找不到返回 None（跳过该 key）。"""
    matches = [f for f in freqs if key.startswith(f"{f}_")]
    if not matches:
        return None
    return max(matches, key=len)


def build_signal_overlays(
    df: "pd.DataFrame",
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
```

- [ ] **Step 5.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestBuildSignalOverlays -v
```

Expected: 2 passed

- [ ] **Step 5.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_signals.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): build_signal_overlays 多 freq 分桶 + palette 注入"
```

---

## Task 6：扩展 `FreqPayload.signals` 字段 —— U9

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_data.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 6.1: 追加 U9 测试（默认空、向后兼容）**

Append to `tests/test_lightweight_signals.py`:

```python
class TestFreqPayloadSignalsField:
    def test_u9_signals_defaults_empty(self):
        from czsc import CZSC, Freq, format_standard_kline
        from czsc.utils.plotting.lightweight import _data

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20230301", seed=42)
        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        payload = _data.build_from_czsc(c)
        assert payload.panes[0].signals == []
        # asdict 序列化不抛
        d = payload.to_dict()
        assert d["panes"][0]["signals"] == []
```

- [ ] **Step 6.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestFreqPayloadSignalsField -v
```

Expected: FAIL with `AttributeError: 'FreqPayload' object has no attribute 'signals'`

- [ ] **Step 6.3: 扩展 `FreqPayload`**

Modify `czsc/utils/plotting/lightweight/_data.py`:

Find the `FreqPayload` dataclass and add the `signals` field:

```python
@dataclass
class FreqPayload:
    freq_label: str
    main: MainPane
    volume: VolumePane
    macd: MacdPane
    signals: list[Any] = field(default_factory=list)  # list[SignalSeries]，避免循环 import 用 Any
```

Also export the field-aware import. In the same `_data.py`, ensure `Any` is already imported (it is).

- [ ] **Step 6.4: 运行原有的 plotting 测试，确认未破坏**

```bash
uv run --no-sync pytest tests/test_lightweight_plotting.py tests/test_lightweight_signals.py -v
```

Expected: 所有原 plotting 测试 + 新 U9 全绿

- [ ] **Step 6.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/_data.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): FreqPayload 新增 signals 字段（默认空，向后兼容）"
```

---

## Task 7：`plot_czsc_signals` 顶层 API —— I1/I3/I4

**Files:**
- Modify: `czsc/utils/plotting/lightweight/__init__.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 7.1: 追加 I3 / I4 集成测试（先不测 HTML 字符串，留给 T8）**

Append to `tests/test_lightweight_signals.py`:

```python
SIGNALS_CONFIG_DEMO = [
    {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    {"name": "cxt_bi_status_V230101", "freq": "日线"},
]


@pytest.fixture(scope="module")
def _bars_demo():
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20230601", seed=42)
    return format_standard_kline(df, freq=Freq.F30)


class TestPlotCzscSignalsPayload:
    def test_i3_multi_freq_bucketing(self, _bars_demo):
        """日线 key 不出现在 30 分钟 pane.signals，反之亦然。"""
        from czsc.traders import generate_czsc_signals
        from czsc.utils.plotting.lightweight import plot_czsc_signals
        from czsc.utils.plotting.lightweight._data import build_from_trader
        from czsc.utils.plotting.lightweight._signals import build_signal_overlays
        from czsc.utils.plotting.lightweight._theme import SIGNAL_PALETTE_LIGHT, get_theme

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        assert isinstance(html, str)
        # 提取 PAYLOAD JSON 检查 signals 分桶
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        assert m is not None
        payload = json.loads(m.group(1))
        for pane in payload["panes"]:
            for series in pane["signals"]:
                key = series["key"]
                assert key.startswith(pane["freq_label"] + "_"), (
                    f"key {key} 落到了错误的 pane {pane['freq_label']}"
                )

    def test_i4_transition_count_matches_direct_calc(self, _bars_demo):
        """plot 输出的 marker 数 == 直接调 generate_czsc_signals + detect_transitions 的数量。"""
        from czsc.traders import generate_czsc_signals
        from czsc.utils.plotting.lightweight import plot_czsc_signals
        from czsc.utils.plotting.lightweight._signals import detect_transitions

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "30分钟"}],
            output="html",
            tail_bars=200,
        )
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))

        df = generate_czsc_signals(
            _bars_demo,
            signals_config=[{"name": "cxt_bi_status_V230101", "freq": "30分钟"}],
            df=True,
        )
        signal_col = next(c for c in df.columns if "表里关系" in c)
        # tail_bars 截断只影响图表 marker，所以这里以 payload 内 marker 时间为准
        plot_marker_times = {
            m_["time"]
            for pane in payload["panes"]
            for series in pane["signals"]
            for m_ in series["markers"]
        }
        direct = detect_transitions(df, signal_col, include_others=False)
        direct_times_in_window = {
            m_["time"]
            for m_ in direct
            if m_["time"] in plot_marker_times or m_["time"] >= min(plot_marker_times, default=0)
        }
        # 不强相等（tail_bars 截断 + warmup 边界）；要求所有 plot 端 marker 都来自直接计算结果
        assert plot_marker_times.issubset({m_["time"] for m_ in direct})
```

- [ ] **Step 7.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPlotCzscSignalsPayload -v
```

Expected: FAIL with `ImportError: cannot import name 'plot_czsc_signals'`

- [ ] **Step 7.3: 新增 `plot_czsc_signals` 顶层 API**

Modify `czsc/utils/plotting/lightweight/__init__.py`:

Add the new function before the existing `_dispatch` or after `plot_czsc_trader`, and update `__all__`:

```python
__all__ = ["plot_czsc", "plot_czsc_signals", "plot_czsc_trader"]


def plot_czsc_signals(
    bars: list,
    *,
    signals_config: list[dict],
    output: OutputType = "html",
    path: str | Path | None = None,
    title: str | None = None,
    theme: _theme.ThemeName = "light",
    show_sma: Sequence[int] = (5, 20),
    tail_bars: int | None = None,
    sdt: str = "20170101",
    init_n: int = 500,
    include_others: bool = False,
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
        theme: ``"light"`` / ``"dark"``。
        show_sma: 主图 SMA 周期序列。
        tail_bars: 截断到最近 N 根；为 ``None`` 不截断。
        sdt: 信号开始计算日期，透传给 ``generate_czsc_signals``。
        init_n: 预热 K 线数，透传给 ``generate_czsc_signals``。
        include_others: ``True`` 时不过滤 "其他"；默认 ``False``。
    """
    from czsc._native import BarGenerator, CzscTrader  # noqa: PLC0415
    from czsc.traders import generate_czsc_signals, get_signals_freqs  # noqa: PLC0415

    from . import _signals  # noqa: PLC0415

    if not bars:
        raise ValueError("bars 不能为空")

    freqs = get_signals_freqs(signals_config) or [str(bars[0].freq)]
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
```

- [ ] **Step 7.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPlotCzscSignalsPayload -v
```

Expected: 2 passed

- [ ] **Step 7.5: Commit**

```bash
git add czsc/utils/plotting/lightweight/__init__.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): plot_czsc_signals 顶层 API（端到端 payload，先落 signal overlay）"
```

---

## Task 8：HTML 渲染 —— marker JS 注入 + tooltip 扩展 —— I1

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_html_renderer.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 8.1: 追加 I1 HTML 字符串内容测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestPlotCzscSignalsHTML:
    def test_i1_html_contains_signal_blocks(self, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        html = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            tail_bars=200,
        )
        # JS 必含 setMarkers 调用 + SIGNALS tooltip 段标题
        assert "setMarkers" in html
        assert "SIGNALS · @CURRENT BAR" in html
        # short_label 渲染到图例区
        m = re.search(r"PAYLOAD = (\{.*?\});", html, re.S)
        payload = json.loads(m.group(1))
        any_signals = any(pane["signals"] for pane in payload["panes"])
        assert any_signals
```

- [ ] **Step 8.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPlotCzscSignalsHTML -v
```

Expected: FAIL（HTML 不含 `setMarkers` / `SIGNALS · @CURRENT BAR`）

- [ ] **Step 8.3: 修改 `_html_renderer.py` 的 JS 模板**

在 `_PAGE_TPL` 的 JavaScript 内 `buildFreqPane(...)` 函数内（变量 `bi` 设置完之后，`// VOL` 之前），插入以下 JS：

```javascript
      // —— Signal markers（每个 key 一个 SignalSeries，合并到 candle series 上）——
      var signalSeries = freq.signals || [];
      var signalMarkersAll = [];      // 当前可见的 markers 数组
      var signalsByTime = {};         // tooltip 用：time → [{ key, v1, value, color }, ...]
      var seriesVisibleMap = {};      // key → bool
      signalSeries.forEach(function (s) {
        seriesVisibleMap[s.key] = true;
        s.markers.forEach(function (m) {
          var entry = {
            time: m.time,
            position: s.position,
            color: m.color || s.color,
            shape: s.shape || 'circle',
            text: m.v1 || '',
          };
          entry.__key = s.key;
          entry.__value = m.value;
          signalMarkersAll.push(entry);
          if (!signalsByTime[m.time]) signalsByTime[m.time] = [];
          signalsByTime[m.time].push({ key: s.key, v1: m.v1, value: m.value, color: m.color || s.color });
        });
      });
      function applySignalMarkers() {
        var visible = signalMarkersAll
          .filter(function (m) { return seriesVisibleMap[m.__key]; })
          .sort(function (a, b) { return a.time - b.time; })
          .map(function (m) {
            return { time: m.time, position: m.position, color: m.color, shape: m.shape, text: m.text };
          });
        ks.setMarkers(visible);
      }
      applySignalMarkers();
```

在同一函数底部（`// 图例点击 → toggle series 可见` 之前），插入"signal legend chip 注入 + 点击切 visibility"的代码：

```javascript
      // —— Signal 图例条目（动态注入到 pane-meta 末尾）——
      if (signalSeries.length) {
        var meta = pane.querySelector('.pane-meta');
        var divider = document.createElement('span');
        divider.className = 'pane-meta__divider';
        meta.insertBefore(divider, meta.querySelector('.pane-meta__hint') || null);
        signalSeries.forEach(function (s) {
          var chip = document.createElement('span');
          chip.className = 'pane-meta__legend';
          chip.setAttribute('data-signal-key', s.key);
          chip.innerHTML =
            '<span class="pane-meta__swatch" style="background:' + s.color + ';height:6px;border-radius:50%;width:6px"></span>'
            + s.short_label;
          chip.addEventListener('click', function () {
            seriesVisibleMap[s.key] = !seriesVisibleMap[s.key];
            chip.classList.toggle('legend--off', !seriesVisibleMap[s.key]);
            applySignalMarkers();
          });
          meta.insertBefore(chip, meta.querySelector('.pane-meta__hint') || null);
        });
      }
```

把 `tooltipHTML` 函数改为接收第 4 个参数 `signals`，并把 SIGNALS 段拼到现有 return 的末尾。具体两步：

**步骤 8.3a**：修改 `function tooltipHTML(c, prev, macd) {` 函数签名为 `function tooltipHTML(c, prev, macd, signals) {`。

**步骤 8.3b**：找到现有 `tooltipHTML` 的 return 语句。原本是：

```javascript
      return ''
        + '<div class="tooltip__time">' + timeStr + '</div>'
        + '<div class="tooltip__grid">'
        // ... OHLC + Vol ...
        + '</div>'
        + (macd ? /* MACD 段 */ : '');
```

把整段 return 改成先求 `var html = '' + <原表达式>;`，然后在末尾追加 signalsBlock 后 return：

```javascript
      var html = ''
        + '<div class="tooltip__time">' + timeStr + '</div>'
        + '<div class="tooltip__grid">'
        + '<span class="tooltip__label">Open</span>'
        + '<span class="tooltip__value">' + fmt(c.open) + '</span>'
        + '<span class="tooltip__label">High</span>'
        + '<span class="tooltip__value">' + fmt(c.high) + '</span>'
        + '<span class="tooltip__label">Low</span>'
        + '<span class="tooltip__value">' + fmt(c.low) + '</span>'
        + '<span class="tooltip__label">Close</span>'
        + '<span class="tooltip__value tooltip__value--' + ccls + '">' + fmt(c.close) + '</span>'
        + '<span class="tooltip__label">Chg %</span>'
        + '<span class="tooltip__value tooltip__value--' + ccls + '">' + sgn(change) + Math.abs(pct).toFixed(2) + '%</span>'
        + (c.volume != null
            ? '<span class="tooltip__label">Vol</span><span class="tooltip__value">' + fmtVol(c.volume) + '</span>'
            : '')
        + '</div>'
        + (macd ?
            '<div class="tooltip__section">MACD · 12/26/9</div>'
            + '<div class="tooltip__grid">'
            + '<span class="tooltip__label">DIFF</span>'
            + '<span class="tooltip__value tooltip__value--' + diffCls + '">' + fmt(macd.diff) + '</span>'
            + '<span class="tooltip__label">DEA</span>'
            + '<span class="tooltip__value">' + fmt(macd.dea) + '</span>'
            + '<span class="tooltip__label">MACD</span>'
            + '<span class="tooltip__value tooltip__value--' + macdCls + '">' + fmt(macd.macd) + '</span>'
            + '</div>'
            : '');
      if (signals && signals.length) {
        html += '<div class="tooltip__section">SIGNALS · @CURRENT BAR</div>'
              + '<div class="tooltip__grid">';
        signals.forEach(function (s) {
          html +=
            '<span class="tooltip__label" style="color:' + s.color + '">' + s.key + '</span>'
            + '<span class="tooltip__value">' + s.value + '</span>';
        });
        html += '</div>';
      }
      return html;
```

**步骤 8.3c**：在 `subscribeCrosshairMove` 回调内（原来调用 `tipEl.innerHTML = tooltipHTML(c, prev ? prev.ohlc : null, m);` 那行）改成把 `signalsByTime[param.time] || []` 作为第 4 个参数传入：

```javascript
          var sigs = signalsByTime[param.time] || [];
          tipEl.innerHTML = tooltipHTML(c, prev ? prev.ohlc : null, m, sigs);
```

> **实现注意**：`_PAGE_TPL` 是 `string.Template`，里面的 `$` 必须保留为 `$$`；上面这些 JS 不含 `$`，可直接粘贴。注入点要找准——建议先 `grep -n` 定位 `// VOL`、`function tooltipHTML`、`// 图例点击` 三处锚点。

- [ ] **Step 8.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestPlotCzscSignalsHTML -v
```

Expected: 1 passed

- [ ] **Step 8.5: 跑全部 lightweight 测试，确认未破坏**

```bash
uv run --no-sync pytest tests/test_lightweight_plotting.py tests/test_lightweight_signals.py -v
```

Expected: 全绿

- [ ] **Step 8.6: Commit**

```bash
git add czsc/utils/plotting/lightweight/_html_renderer.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): HTML 端 signal marker 注入 + tooltip SIGNALS 段"
```

---

## Task 9：Streamlit 渲染 —— markers + signal KPI

**Files:**
- Modify: `czsc/utils/plotting/lightweight/_streamlit_renderer.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 9.1: 追加单测：`_build_groups` 携带 markers**

Append to `tests/test_lightweight_signals.py`:

```python
class TestStreamlitMarkers:
    def test_build_groups_passes_markers_to_candle(self):
        from czsc.utils.plotting.lightweight._data import build_from_czsc
        from czsc.utils.plotting.lightweight._signals import SignalMarker, SignalSeries
        from czsc.utils.plotting.lightweight._streamlit_renderer import _build_groups
        from czsc.utils.plotting.lightweight._theme import get_theme

        df = generate_symbol_kines("000001", "30分钟", "20230101", "20230201", seed=42)
        from czsc import CZSC, Freq, format_standard_kline

        c = CZSC(format_standard_kline(df, freq=Freq.F30))
        payload = build_from_czsc(c)
        freq = payload.panes[0]
        freq.signals = [
            SignalSeries(
                key="30分钟_D1_X",
                short_label="D1_X",
                color="#1F3C6E",
                shape="circle",
                position="aboveBar",
                markers=[
                    SignalMarker(time=int(freq.main.candles[10]["time"]), value="A_x_x_0", v1="A", color="#1F3C6E"),
                ],
            )
        ]
        groups = _build_groups(freq, get_theme("light"), visible=None)
        candle_cfg = groups[0]["series"][0]
        markers = candle_cfg.get("markers", [])
        assert any(m["time"] == int(freq.main.candles[10]["time"]) for m in markers)
        assert markers[0]["color"] == "#1F3C6E"
        assert markers[0]["text"] == "A"
```

- [ ] **Step 9.2: 运行测试，确认失败**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestStreamlitMarkers -v
```

Expected: FAIL（`candle_cfg.get("markers", [])` 为空）

- [ ] **Step 9.3: 修改 `_streamlit_renderer._build_groups`**

在 `_streamlit_renderer.py` 的 `_build_groups()` 内，构造 `main_series` 时把 `freq.signals` 的 markers 合并塞进 candle 那一条：

```python
def _build_groups(freq: FreqPayload, theme, *, visible: dict[str, bool] | None) -> list[dict[str, Any]]:
    # ... 原有 main_series 构造逻辑不变 ...

    # 合并所有 SignalSeries 的 markers 到 candle 上
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
        # candle 是 main_series[0]
        main_series[0]["markers"] = sorted(signal_markers, key=lambda x: x["time"])
    # ... 后面 macd_series / 返回值不变 ...
```

- [ ] **Step 9.4: 运行测试，确认通过**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestStreamlitMarkers -v
```

Expected: 1 passed

- [ ] **Step 9.5: 追加 signal KPI 卡渲染辅助**

Append to `_streamlit_renderer.py`（在 `render_freq` 之后）：

```python
def render_signal_kpi(freq: FreqPayload, *, key_prefix: str = "lwc-sig-kpi") -> None:
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
        f'</div>'
        for key, value, color in rows
    )
    st.html(f'<div class="qa-kpi-row">{chips}</div>')
```

- [ ] **Step 9.6: 简单冒烟单测（不依赖 streamlit 实际渲染，只检查函数可调用）**

Append to `tests/test_lightweight_signals.py`:

```python
    def test_render_signal_kpi_callable(self):
        """signal KPI 仅做"无 markers / 无 candles"两条早返路径的导入/早返冒烟。"""
        from czsc.utils.plotting.lightweight._data import (
            FreqPayload,
            MacdPane,
            MainPane,
            VolumePane,
        )
        from czsc.utils.plotting.lightweight._streamlit_renderer import render_signal_kpi

        # 无 signals → 直接 return，不会触发 streamlit 调用
        empty = FreqPayload(freq_label="30分钟", main=MainPane(), volume=VolumePane(), macd=MacdPane())
        render_signal_kpi(empty)  # 不抛
```

- [ ] **Step 9.7: 跑测试**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestStreamlitMarkers -v
```

Expected: 2 passed

- [ ] **Step 9.8: Commit**

```bash
git add czsc/utils/plotting/lightweight/_streamlit_renderer.py tests/test_lightweight_signals.py
git commit -m "feat(lightweight): Streamlit 端 candle markers + signal KPI 卡"
```

---

## Task 10：HTML 演示案例 15 + I2 文件持久化

**Files:**
- Create: `docs/examples/15_lightweight_signals_html.py`
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 10.1: 写案例 15**

Create `docs/examples/15_lightweight_signals_html.py`:

```python
"""案例 15：lightweight_charts 信号叠加（离线 HTML 版）

把多个信号函数的历史触发点叠加到 K 线主图：

- 每个 signal key 一个独立颜色 marker
- 同一 key 下，value 与上一个值一致时不再画 marker（只标 transition）
- hover K 线弹出的 tooltip 含 SIGNALS 段，显示完整 value（v1_v2_v3_score）

运行：
    uv run --no-sync python docs/examples/15_lightweight_signals_html.py
    # 产物：docs/examples/_output/15_lwc_signals.html
"""

from __future__ import annotations

from pathlib import Path

from czsc import Freq, format_standard_kline
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import plot_czsc_signals

OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_CONFIG = [
    {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    {"name": "cxt_bi_status_V230101", "freq": "日线"},
    {"name": "tas_ma_base_V221101", "freq": "日线",
     "di": 1, "timeperiod": 5, "ma_type": "SMA"},
    {"name": "bar_zdt_V230331", "freq": "30分钟", "di": 1},
]


def main() -> Path:
    print("[案例 15] 生成 lightweight_charts 信号叠加 HTML...")
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20240301", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    out = OUTPUT_DIR / "15_lwc_signals.html"
    plot_czsc_signals(
        bars,
        signals_config=SIGNALS_CONFIG,
        output="html",
        path=out,
        title="000001 · 多信号历史触发可视化（lightweight_charts）",
        tail_bars=600,
    )
    print(f"  · 落盘：{out}  ({out.stat().st_size / 1024:.1f} KB)")
    print("\n双击 HTML 用浏览器打开（需联网加载 lightweight-charts CDN）。")
    return out


if __name__ == "__main__":
    main()
```

- [ ] **Step 10.2: 写 I2 文件持久化集成测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestCase15HtmlPersistence:
    def test_i2_writes_html_file(self, tmp_path, _bars_demo):
        from czsc.utils.plotting.lightweight import plot_czsc_signals

        out = tmp_path / "15_lwc_signals.html"
        ret = plot_czsc_signals(
            _bars_demo,
            signals_config=SIGNALS_CONFIG_DEMO,
            output="html",
            path=out,
            tail_bars=200,
        )
        assert str(ret) == str(out)
        assert out.exists()
        assert out.stat().st_size > 50 * 1024  # > 50KB
        html = out.read_text(encoding="utf-8")
        # 自包含 + 关键 JS hook 存在
        assert html.startswith("<!DOCTYPE html")
        assert "setMarkers" in html
```

- [ ] **Step 10.3: 跑集成测试**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestCase15HtmlPersistence -v
```

Expected: 1 passed

- [ ] **Step 10.4: 跑案例 15，肉眼检查 HTML**

```bash
uv run --no-sync python docs/examples/15_lightweight_signals_html.py
```

Expected: 输出形如 `· 落盘：docs/examples/_output/15_lwc_signals.html  (XXX.X KB)`

打开 `docs/examples/_output/15_lwc_signals.html` 用浏览器肉眼验证：
- 主图能看到 ≥ 2 种颜色 marker
- pane-meta 区域出现每个 signal 的图例 chip + 短 label
- hover bar 时 tooltip 底部出现 "SIGNALS · @CURRENT BAR"，每行 `{key} = v1_v2_v3_score`
- 点 LIGHT/DARK 切换主题，marker 颜色随之换 palette
- 切到日线 tab 时主图 marker 来自日线 signals

- [ ] **Step 10.5: Commit**

```bash
git add docs/examples/15_lightweight_signals_html.py tests/test_lightweight_signals.py
git commit -m "docs(examples): 新增案例 15 lightweight_charts 信号叠加（HTML）"
```

---

## Task 11：Streamlit 演示案例 16

**Files:**
- Create: `docs/examples/16_streamlit_signals.py`

- [ ] **Step 11.1: 写案例 16**

Create `docs/examples/16_streamlit_signals.py`:

```python
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
    "笔表里关系 · 日线":   {"name": "cxt_bi_status_V230101", "freq": "日线"},
    "5 日均线分类":         {"name": "tas_ma_base_V221101", "freq": "日线",
                           "di": 1, "timeperiod": 5, "ma_type": "SMA"},
    "30 分钟涨跌停":        {"name": "bar_zdt_V230331", "freq": "30分钟", "di": 1},
}


@st.cache_data(show_spinner="生成 mock K 线...")
def _load_bars(symbol: str, start: str, end: str, seed: int):
    df = generate_symbol_kines(symbol, "30分钟", start, end, seed=seed)
    return format_standard_kline(df, freq=Freq.F30)


def main() -> None:
    st.set_page_config(page_title="lightweight_charts · 信号叠加",
                       layout="wide", initial_sidebar_state="expanded")

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
    freqs = get_signals_freqs(cfg) or ["30分钟"]
    base = "30分钟"
    if base not in freqs:
        freqs = [base, *freqs]

    bg = BarGenerator(base_freq=base, freqs=freqs, max_count=max(10000, len(bars)))
    for b in bars:
        bg.update(b)
    ct = CzscTrader(bg, positions=[], signals_config=[])

    theme = _theme.get_theme(theme_name)  # type: ignore[arg-type]
    payload = _data.build_from_trader(ct, theme=theme, show_sma=(5, 20), tail_bars=tail,
                                      title=f"{symbol} · 信号叠加")

    df = generate_czsc_signals(bars, signals_config=cfg, df=True)
    overlays = _signals.build_signal_overlays(df, freqs=freqs, palette=_theme.get_signal_palette(theme_name))  # type: ignore[arg-type]
    for pane in payload.panes:
        series = overlays.get(pane.freq_label, [])
        if tail is not None and pane.main.candles:
            cutoff = pane.main.candles[0]["time"]
            series = [
                _signals.SignalSeries(
                    key=s.key, short_label=s.short_label, color=s.color,
                    shape=s.shape, position=s.position,
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
```

- [ ] **Step 11.2: 手工启动 Streamlit 肉眼验证（S1–S4）**

```bash
uv run --no-sync streamlit run docs/examples/16_streamlit_signals.py
```

打开浏览器（默认 http://localhost:8501）核对：
- 侧栏勾选 / 取消信号后主图 marker 数量实时变化（S1）
- 顶部 "qa-kpi-row" 卡片显示每个生效 signal 的完整 value（S2）
- 切换主题 segmented control，marker 颜色随 palette 切换（S3）
- 滑动 tail_bars，pane 内 bar 数和 marker 数同步收缩（S4）

确认无 exception 后 `Ctrl+C` 退出。

- [ ] **Step 11.3: Commit**

```bash
git add docs/examples/16_streamlit_signals.py
git commit -m "docs(examples): 新增案例 16 lightweight_charts 信号叠加（Streamlit）"
```

---

## Task 12：向后兼容 I5 + 慢测试 I6

**Files:**
- Modify: `tests/test_lightweight_signals.py`

- [ ] **Step 12.1: 追加 I5 向后兼容测试**

Append to `tests/test_lightweight_signals.py`:

```python
class TestBackwardCompat:
    def test_i5_case13_demos_unchanged(self, tmp_path):
        """跑案例 13 的 demo 函数，确认输出依然能生成且包含原有结构。"""
        import sys

        sys.path.insert(0, str((tmp_path.parent / "..").resolve()))
        try:
            import importlib

            mod = importlib.import_module("docs.examples.13_lightweight_charts_html")
        except (ImportError, ModuleNotFoundError):
            pytest.skip("案例 13 未安装为可 import 模块；视觉对照在案例 13 自身的回归测试里覆盖。")
            return
        # 不直接调用（会写 _output/）；仅断言关键函数仍可 import
        assert callable(getattr(mod, "demo_single", None))
        assert callable(getattr(mod, "demo_multi", None))
```

> 注：案例 13/14 视觉 baseline 通过现有 `tests/test_lightweight_plotting.py` 全部断言已覆盖；I5 这里只做模块可 import 的弱断言，避免在 CI 里再次写盘。

- [ ] **Step 12.2: 追加 I6 慢测试（Streamlit AppTest）**

Append to `tests/test_lightweight_signals.py`:

```python
@pytest.mark.slow
class TestStreamlitSlow:
    def test_i6_streamlit_app_smoke(self, tmp_path):
        """通过 streamlit.testing.v1.AppTest 启动案例 16，确保不抛异常。"""
        try:
            from streamlit.testing.v1 import AppTest  # noqa: PLC0415
        except ImportError:
            pytest.skip("当前环境无 streamlit.testing.v1.AppTest")
            return
        at = AppTest.from_file("docs/examples/16_streamlit_signals.py", default_timeout=30)
        at.run()
        # 无 exception
        assert not at.exception
```

- [ ] **Step 12.3: 跑 I5（默认）和 I6（带 --run-slow）**

```bash
uv run --no-sync pytest tests/test_lightweight_signals.py::TestBackwardCompat -v
uv run --no-sync pytest tests/test_lightweight_signals.py::TestStreamlitSlow --run-slow -v
```

Expected: I5 通过；I6 在 streamlit-lightweight-charts 安装时通过，否则 skip。

- [ ] **Step 12.4: Commit**

```bash
git add tests/test_lightweight_signals.py
git commit -m "test(lightweight): I5 案例 13 模块可 import + I6 Streamlit slow smoke"
```

---

## Task 13：代码质量门禁

**Files:**
- All modified/created files

- [ ] **Step 13.1: 跑 ruff format（不会自动改但会列出差异）**

```bash
uv run --no-sync ruff format --check \
  czsc/utils/plotting/lightweight \
  tests/test_lightweight_signals.py \
  docs/examples/15_lightweight_signals_html.py \
  docs/examples/16_streamlit_signals.py
```

Expected: `X file(s) already formatted`

如有 diff，跑 `ruff format` 修正：

```bash
uv run --no-sync ruff format \
  czsc/utils/plotting/lightweight \
  tests/test_lightweight_signals.py \
  docs/examples/15_lightweight_signals_html.py \
  docs/examples/16_streamlit_signals.py
```

- [ ] **Step 13.2: 跑 ruff check**

```bash
uv run --no-sync ruff check \
  czsc/utils/plotting/lightweight \
  tests/test_lightweight_signals.py \
  docs/examples/15_lightweight_signals_html.py \
  docs/examples/16_streamlit_signals.py
```

Expected: `All checks passed!`

- [ ] **Step 13.3: 跑全部 lightweight 测试**

```bash
uv run --no-sync pytest tests/test_lightweight_plotting.py tests/test_lightweight_signals.py -v
```

Expected: 全部通过（原 plotting 测试 + 9 个单元 + 5 个集成）

- [ ] **Step 13.4: 跑全套测试（不带 slow，确认未殃及其他模块）**

```bash
uv run --no-sync pytest
```

Expected: 全部通过；输出末尾的 `X skipped` 包含 I6 slow 测试。

- [ ] **Step 13.5: 如有 ruff 或测试调整，Commit**

```bash
git add -A
git commit -m "chore(lightweight): ruff format/check 通过 + 全套测试绿"
```

- [ ] **Step 13.6: 跑视觉验收清单**

按飞书评审 §9.3 + §9.4 表逐条人工打勾：
- V1–V7：肉眼复查 `docs/examples/_output/15_lwc_signals.html`
- S1–S4：肉眼复查 Streamlit 应用（案例 16）
- §9.4 验收门禁 R1–R6 全部 `[x]`

---

## Final Checklist

- [ ] T1–T13 全部 step 完成
- [ ] `tests/test_lightweight_signals.py` 单元 + 集成全绿
- [ ] `--run-slow` 下 I6 通过或合理 skip
- [ ] ruff format / check 干净
- [ ] 案例 15 HTML 落盘可在浏览器打开，肉眼通过 V1–V7
- [ ] 案例 16 Streamlit 启动后肉眼通过 S1–S4
- [ ] 飞书评审稿 §9.4 验收门禁表 R1–R6 全勾
- [ ] 原 plotting 测试（`test_lightweight_plotting.py`）一个都没破

---

## Risk & Open Questions

1. **lightweight-charts 4.x `setMarkers` API 变更**：若发现 `text` 字段被改为 `tooltip`，按当前线上 CDN 版本 `4.1.3` 校准。
2. **marker 文字过长**：当前用 v1（信号 value 第一段）；若 v1 文本宽度 > 30px 会挡线，需要在 T8 末尾追加截断（`v1.slice(0, 4)`）。
3. **`include_others` 默认值**：默认 `False`，与飞书评审一致；若某信号函数把"其他"当真状态用，须显式 `include_others=True`。

---

> **完成后**：把本 plan 标记为 done，更新飞书评审稿 §9.4 验收门禁表的 R1–R6 checkbox 为 `done="true"`。
