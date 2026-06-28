"""Signal catalog for LLM-guided position optimization.

优化必须真正改变 opens/exits 的 event 信号。本模块从 czsc 注册表 + signal-functions
skill 文档中提取「真实存在、可在目标周期解析」的信号字符串，作为 LLM 每轮迭代的信号池，
避免生成行为等价的开/平仓 event（无效优化）。
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

# 方向关键词：用于把信号归类为「开多/平多」可用的方向。
LONG_OPEN_KEYS = ("看多", "向上", "买入", "多头排列", "多头", "多头#向上", "加速上涨", "强", "金叉", "底分")
LONG_EXIT_KEYS = ("看空", "向下", "卖出", "空头排列", "空头", "空头#向下", "减速下跌", "弱", "死叉", "顶分")


@lru_cache(maxsize=1)
def _registry_signals() -> list[dict[str, str]]:
    """从 czsc._native 注册表列出全部 K线级信号函数（name / template / category）。"""
    from czsc import _native

    try:
        raw = _native.list_all_signals(include_kline=True, include_trader=False)
    except Exception:  # noqa: BLE001 - 注册表不可用时降级为空。
        return []
    return [
        {
            "name": str(s.get("name", "")),
            "template": str(s.get("param_template", "")),
            "category": str(s.get("category", "")),
        }
        for s in raw
        if s.get("name")
    ]


def _skill_signals_dir() -> Path:
    """定位 signal-functions skill 的详细信号文档目录。"""
    here = Path(__file__).resolve()
    # auto_quant/scripts/auto-czsc-quant/.claude/skills/signal-functions/references/signals
    for candidate in (
        here.parents[2] / ".claude" / "skills" / "signal-functions" / "references" / "signals",
        here.parents[3] / ".claude" / "skills" / "signal-functions" / "references" / "signals",
        Path.cwd() / ".claude" / "skills" / "signal-functions" / "references" / "signals",
    ):
        if candidate.is_dir():
            return candidate
    return here.parents[2] / ".claude" / "skills" / "signal-functions" / "references" / "signals"


def _extract_doc_examples(docs_dir: Path) -> list[str]:
    """从 skill 详细文档抽取 Signal('...') 示例字符串。"""
    if not docs_dir.is_dir():
        return []
    pat = re.compile(r"Signal\(['\"]([^'\"]+)['\"]\)")
    out: list[str] = []
    for doc in docs_dir.glob("*.md"):
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        out.extend(pat.findall(text))
    return out


def _retarget_freq(signal: str, freq: str) -> str:
    """把信号字符串的首段周期替换为目标周期。"""
    parts = signal.split("_", 1)
    if len(parts) < 2:
        return signal
    return f"{freq}_{parts[1]}"


@lru_cache(maxsize=8)
def resolved_signal_pool(freq: str, *, limit_per_direction: int = 40) -> dict[str, list[str]]:
    """返回目标周期下「真实可解析」的信号字符串池，按方向分组。

    数据来源：signal-functions skill 详细文档里的 Signal(...) 示例，逐条把周期改写为
    ``freq`` 并用 derive_signals_config 校验确实存在。返回::

        {"long_open": [...], "long_exit": [...], "other": [...]}

    long_open / long_exit 用于开多 / 平多 event；other 是无法自动归类但有效的信号。
    """
    from czsc import derive_signals_config

    examples = _extract_doc_examples(_skill_signals_dir())
    seen: set[str] = set()
    long_open: list[str] = []
    long_exit: list[str] = []
    other: list[str] = []

    for raw in examples:
        sig = _retarget_freq(raw, freq)
        if sig in seen:
            continue
        try:
            if not derive_signals_config([sig]):
                continue
        except Exception:  # noqa: BLE001
            continue
        seen.add(sig)
        # 用 v1 段（倒数第 4 段，score 之前）做方向归类。
        tokens = sig.rsplit("_", 4)  # [k..., v1, v2, v3, score]
        v1 = tokens[-4] if len(tokens) == 5 else ""
        if any(k in sig for k in LONG_OPEN_KEYS) or v1 in LONG_OPEN_KEYS:
            bucket = long_open
        elif any(k in sig for k in LONG_EXIT_KEYS) or v1 in LONG_EXIT_KEYS:
            bucket = long_exit
        else:
            bucket = other
        if len(bucket) < limit_per_direction:
            bucket.append(sig)

    return {"long_open": long_open, "long_exit": long_exit, "other": other}


def render_signal_catalog(freq: str, *, max_signals: int = 60) -> str:
    """渲染供 LLM 直接消费的信号目录文本（按方向分组 + 注册表函数索引）。"""
    pool = resolved_signal_pool(freq)
    long_open = pool["long_open"][: max_signals // 2]
    long_exit = pool["long_exit"][: max_signals // 2]
    registry = _registry_signals()

    lines = [
        f"# 目标周期：{freq}（信号字符串必须以此周期开头）",
        "",
        "## A. 可直接使用的「开多方向」信号（填入 opens[].signals_all）",
        "下面每条都是经 derive_signals_config 校验真实存在的信号，可整条复制使用：",
    ]
    lines.extend(f"- {s}" for s in long_open) or lines.append("- （未抽取到，请用 B 节函数自行构造）")
    lines.extend(
        [
            "",
            "## B. 可直接使用的「平多/止盈方向」信号（填入 exits[].signals_all）",
        ]
    )
    lines.extend(f"- {s}" for s in long_exit) or lines.append("- （未抽取到，请用 C 节函数自行构造）")
    lines.extend(
        [
            "",
            "## C. 全部注册信号函数（name | 参数模板），用于自造信号字符串",
            "信号字符串 7 段格式：`{freq}_{k2}_{k3}_{v1}_{v2}_{v3}_{score}`；score 整数 0-100。",
        ]
    )
    for s in registry[:80]:
        lines.append(f"- `{s['name']}` 模板 `{s['template']}`")
    if len(registry) > 80:
        lines.append(f"- …（共 {len(registry)} 个函数，已截断展示）")
    return "\n".join(lines)


def known_signals(freq: str) -> set[str]:
    """目标周期下全部已解析的有效信号字符串集合（供校验候选信号是否真实存在）。"""
    pool = resolved_signal_pool(freq)
    return set(pool["long_open"]) | set(pool["long_exit"]) | set(pool["other"])


def event_signature(events: list[dict[str, Any]]) -> frozenset[str]:
    """提取一组 event 的规范化信号签名（operate + 全部去重信号），用于检测重复克隆。"""
    sigs: set[str] = set()
    for ev in events or []:
        op = str(ev.get("operate", ""))
        for field in ("signals_all", "signals_any", "signals_not"):
            for sig in ev.get(field) or []:
                sigs.add(f"{op}:{_normalize_signal(sig)}")
    return frozenset(sigs)


def _normalize_signal(sig: Any) -> str:
    """规范化信号字符串：统一为 dict->str、去 score 末段差异。

    候选里信号可能是 str 或 {key,value} dict（Position.dump 的形态），都归一成字符串比较。
    """
    if isinstance(sig, dict):
        key = sig.get("key", "")
        value = sig.get("value", "")
        return f"{key}_{value}" if value else str(key)
    return str(sig)
