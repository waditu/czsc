"""czsc.traders —— 交易员（trader）命名空间的统一入口模块。

本模块在 Rust/Python 混合架构下扮演"门面（facade）"角色，将分散在多个底层
实现中的交易相关公共 API 重新汇聚到一个稳定的导入路径上，方便上层业务以
``from czsc.traders import XXX`` 的方式直接使用，而无需关心底层是 Rust
扩展还是纯 Python 实现。

模块组成说明：

* ``CzscTrader`` / ``CzscSignals`` / ``generate_czsc_signals`` /
  ``derive_signals_config`` / ``derive_signals_freqs`` ：均来自
  ``czsc._native``（Rust 扩展），承担信号生成与多级别交易决策的核心逻辑。
* ``WeightBacktest`` ：从外部 ``wbt`` 包再次导出，提供基于权重序列的
  回测能力。
* ``check_signals_acc`` ：旧版 czsc 中以 HTML 截图方式辅助核对信号的工具，
  Rust 版本未提供等价实现，因此**不再**在此处导出；如需可视化校验信号，
  请改用 ``czsc.svc`` 中提供的 Streamlit 组件。
* ``OpensOptimize`` / ``ExitsOptimize`` / ``CzscOpenOptimStrategy`` /
  ``CzscExitOptimStrategy`` ：定义在 :mod:`czsc.traders.optimize` 中，是对
  ``czsc._native.run_optimize_batch`` 的轻量 Python 封装，用于开仓/平仓
  参数的批量优化。
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
)

# 兼容老的导入路径：保留 Python 侧的薄封装函数 get_unique_signals。
from czsc.traders.base import get_unique_signals
from czsc.traders.sig_parse import SignalsParser, get_signals_config, get_signals_freqs

# __all__ 显式声明对外公开的符号集合，限定 `from czsc.traders import *` 的行为，
# 同时方便 IDE 与文档工具识别模块的公共 API。
__all__ = [
    "CzscSignals",
    "CzscTrader",
    "SignalsParser",
    "WeightBacktest",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
]
