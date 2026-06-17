"""czsc.traders —— 交易员（trader）命名空间的统一入口模块。

本模块在 Rust/Python 混合架构下扮演"门面（facade）"角色，把交易相关公共
API 重新汇聚到一个稳定的导入路径上，方便上层业务以 ``from czsc.traders
import XXX`` 的方式直接使用。

模块组成说明：

* ``CzscTrader`` / ``CzscSignals`` / ``generate_czsc_signals`` /
  ``derive_signals_config`` / ``derive_signals_freqs`` /
  ``get_signals_config`` / ``get_signals_freqs`` / ``get_unique_signals`` ：
  均来自 ``czsc._native``（Rust 扩展），承担信号生成与多级别交易决策的核心逻辑。
* ``WeightBacktest`` ：从外部 ``wbt`` 包再次导出，提供基于权重序列的
  回测能力。

历史模块（已下线）：

- 2026-05-17 PR-C 起：
  - ``czsc.traders.base`` / ``czsc.traders.sig_parse`` 纯透传文件已 git rm，
    本 facade 已直接 import ``czsc._native``；
  - ``czsc.traders.optimize`` 整文件 ``git mv`` 到 :mod:`czsc.utils.optimize`，
    职责更贴近 utils；调用方请改用 ``from czsc.utils.optimize import
    OpensOptimize, ExitsOptimize, CzscOpenOptimStrategy, CzscExitOptimStrategy``。
"""

# 直接从 Rust 原生扩展中导入交易体系核心类与帮助函数，
# 确保 Python 侧只承担"调用-转发"职责，业务逻辑落在 Rust 端。
from wbt import WeightBacktest

from czsc._native import (
    CzscSignals,
    CzscTrader,
    derive_signals_config,
    derive_signals_freqs,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
)

# __all__ 显式声明对外公开的符号集合，限定 `from czsc.traders import *` 的行为，
# 同时方便 IDE 与文档工具识别模块的公共 API。
__all__ = [
    "CzscSignals",
    "CzscTrader",
    "WeightBacktest",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
]
