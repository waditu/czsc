"""czsc.traders.sig_parse —— 信号字符串解析工具的纯透传层。

历史上本模块在 Python 侧承担信号配置展平、name 模块前缀剥离、风格归一等
后处理工作。Rust 端 ``czsc._native.derive_signals_config`` /
``derive_signals_freqs`` 升级后（spec PR-2）已经内置了这些逻辑，因此
Python 侧无需再做任何包装，直接 re-export 即可。

保留本模块仅是为了不破坏 ``from czsc.traders.sig_parse import ...`` 的
历史 import 路径；新增代码请直接 ``from czsc._native import ...``。
"""

from __future__ import annotations

from czsc._native import (
    get_signals_config,
    get_signals_freqs,
)

__all__ = ["get_signals_config", "get_signals_freqs"]
