"""czsc.traders.base —— 交易基础对象的纯透传 re-export 层。

交易员对象（``CzscTrader`` / ``CzscSignals``）、信号生成与解析函数
（``generate_czsc_signals`` / ``get_signals_config`` / ``get_signals_freqs``
/ ``get_unique_signals`` / ``derive_signals_config`` / ``derive_signals_freqs``）
均由 Rust 端 ``czsc._native`` 实现并直接暴露，本模块不再承担任何
"为 Python 用户做参数适配 / 返回值转换" 的职责（spec PR-3）。

保留本模块仅是为了不破坏历史 import 路径，例如
``from czsc.traders.base import CzscSignals`` 仍可正常工作。
"""

from __future__ import annotations

from czsc._native import (
    CzscSignals,
    CzscTrader,
    RawBar,
    Signal,
    derive_signals_config,
    derive_signals_freqs,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
)

__all__ = [
    "CzscSignals",
    "CzscTrader",
    "RawBar",
    "Signal",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
]
