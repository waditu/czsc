"""czsc.traders.base —— 由 ``czsc._native`` 支撑的交易基础对象再导出层。

在当前的 Rust/Python 混合架构下，交易员对象（``CzscTrader``、
``CzscSignals``）以及与信号生成相关的辅助函数（``generate_czsc_signals``、
``get_unique_signals``、``derive_signals_config``、``derive_signals_freqs``）
均迁移到 Rust 扩展中实现，以获得更优的性能与并发能力。

本模块的存在主要有两个目的：

1. **兼容性**：保持历史导入路径稳定，例如老代码中的
   ``from czsc.traders.base import CzscSignals`` 仍可正常工作。
2. **薄封装**：仅在必要时提供少量纯 Python 的"调用拼装"逻辑（如
   :func:`get_unique_signals`），将 Rust 侧返回的 DataFrame 转换为
   业务期望的字符串列表。

按照"Python 仅负责包装、不承载业务逻辑"的总体设计原则，旧版基于
HTML 快照的 ``check_signals_acc`` 编排函数已被移除，可视化诊断需求
请改用 ``czsc.svc`` 中的 Streamlit 组件。
"""

from __future__ import annotations

# 直接从 Rust 原生扩展导入交易/信号体系的核心类型与函数，
# 上层调用方因此感知不到底层是 Rust 实现。
from czsc._native import (
    CzscSignals,
    CzscTrader,
    RawBar,
    Signal,
    derive_signals_config,
    derive_signals_freqs,
    generate_czsc_signals,
)

from czsc.traders.sig_parse import get_signals_freqs


def get_unique_signals(
    bars: list[RawBar],
    signals_config: list[dict[str, object]],
    **kwargs,
) -> list[str]:
    """对 Rust ``generate_czsc_signals`` 结果做去重整理的薄封装。

    本函数会先调用 Rust 实现批量计算所有信号，得到一张包含若干信号列的
    DataFrame；随后逐列提取所有非"其他"取值，按照惯用的
    ``"<列名>_<取值>"`` 字符串格式拼装并去重返回，便于上层做信号字典构建、
    回放校验或断言用。

    Args:
        bars: 标准化后的原始 K 线序列；序列长度过短时不进行计算。
        signals_config: 信号配置列表，会原样透传给 Rust 端的
            ``generate_czsc_signals``。
        **kwargs: 透传给 ``generate_czsc_signals`` 的其他可选参数。

    Returns:
        去重后的信号字符串列表；若输入 K 线数量不足 600 根，则直接返回
        空列表（避免在样本不足时产生噪声信号）。

    Notes:
        - 仅识别列名按 ``"a_b_c"`` 三段式命名的列，与 czsc 信号命名约定保持一致。
        - "其他"是缠论信号体系中通用的"无意义/未匹配"占位取值，会被显式跳过。
    """
    # 当输入 K 线数据不足以形成稳定的信号样本时直接返回空列表，
    # 避免下游被冷启动阶段的噪声信号污染。
    if len(bars) < 600:
        return []

    # 通过 Rust 实现批量计算所有信号取值，输出为 pandas DataFrame。
    df = generate_czsc_signals(bars, signals_config=signals_config, df=True, **kwargs)
    out: list[str] = []
    # 仅遍历列名形如 "a_b_c" 的信号列；其他列（如时间戳、价格等）被忽略。
    for col in [c for c in df.columns if len(c.split("_")) == 3]:
        # 将每列的非"其他"取值拼装成完整的信号串，构建去重序列。
        out.extend(f"{col}_{v}" for v in df[col].unique() if "其他" not in v)
    return out


# __all__ 列出本模块对外暴露的全部公共符号，限定 `import *` 行为，
# 也方便文档生成工具与类型检查器识别公共 API 范围。
__all__ = [
    "CzscSignals",
    "CzscTrader",
    "Signal",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_freqs",
    "get_unique_signals",
]
