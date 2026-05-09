"""czsc.traders.sig_parse —— 信号字符串解析与频率提取工具模块。

本模块提供两个面向外部调用的工具函数：

- :func:`get_signals_config` — 把信号字符串序列解析为扁平化的信号配置列表。
- :func:`get_signals_freqs`  — 从信号序列中提取所有涉及到的 K 线周期。

底层 ``derive_signals_config`` / ``derive_signals_freqs`` 均由
Rust 端 ``czsc._native`` 提供（Phase F 完成迁移）；本模块只做
Python 侧的展平、去重等后处理编排工作。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from czsc._native import (
    derive_signals_config,
    derive_signals_freqs,
)


def get_signals_config(signals_seq: list[str]) -> list[dict]:
    """把信号字符串序列解析为扁平化的信号配置列表。

    实现上把信号序列交给 ``derive_signals_config``（Rust 端）做权威解析，
    再在 Python 侧补齐 ``params`` 字段展平、其余字段透传并去重，
    得到的结构可以直接用作 czsc 信号配置项。

    Args:
        signals_seq: 信号字符串序列。

    Returns:
        扁平化后的信号配置字典列表；输入为空或底层解析不可用时返回空列表。
    """
    if not signals_seq:
        return []

    try:
        conf = derive_signals_config(signals_seq)
    except Exception as exc:
        logger.error(f"derive_signals_config failed: {exc}")
        return []

    out: list[dict[str, Any]] = []
    for row in conf:
        raw = dict(row)
        item: dict[str, Any] = {"name": str(raw.get("name", ""))}
        if raw.get("freq"):
            item["freq"] = raw.get("freq")
        params = raw.get("params") or {}
        if isinstance(params, dict):
            item.update(params)
        for key, value in raw.items():
            if key not in {"name", "freq", "params"}:
                item[key] = value
        if item not in out:
            out.append(item)
    return out


def get_signals_freqs(signals_seq: list) -> list[str]:
    """从信号序列中提取所有涉及到的 K 线周期。

    输入既可以是已经解析好的信号配置字典列表，也可以是原始的信号字符串
    列表；前者直接交给 ``derive_signals_freqs``，后者会先经过
    ``derive_signals_config`` 解析后再提取频率。

    Args:
        signals_seq: 信号字符串列表或信号配置字典列表。

    Returns:
        去重的 K 线周期字符串列表；输入为空时返回空列表。
    """
    if not signals_seq:
        return []

    if isinstance(signals_seq[0], dict):
        return list(derive_signals_freqs(signals_seq))
    conf = derive_signals_config(signals_seq)
    return list(derive_signals_freqs(conf))
