"""
``czsc.utils.ta`` —— 迁移后保留的少量纯 Python 技术指标实现

历史上，本目录下存在一层基于 TA-Lib 的封装；在向 Rust 迁移之后，TA-Lib 封装层
已经被移除，绝大多数指标已经由 Rust 实现的 ``czsc._native.ta`` 命名空间提供
（如 ``ema`` / ``sma`` / ``rolling_rank`` 等）。

但 czsc 仪表盘等场景中使用的 MACD 含有"柱状图额外乘以 2"的特殊约定，目前尚未
迁移至 Rust 实现，因此暂时在本文件中保留对应的纯 Python 版本。这些函数 **不会**
通过 ``czsc.ta`` 重新导出（``czsc.ta`` 现在指向 Rust 子模块），调用方需要显式从
本模块导入。

后续计划：将 :func:`MACD` 移植到 Rust 后，本文件可整体删除。
"""

from __future__ import annotations

import numpy as np

# 仅显式暴露 EMA 与 MACD 两个函数
__all__ = ["EMA", "MACD"]


def EMA(close: np.ndarray, timeperiod: int = 5) -> np.ndarray:
    """指数移动平均（czsc 约定版本）

    采用如下递推公式逐项计算：

        ``ema_t = (2 * close_t + ema_{t-1} * (timeperiod - 1)) / (timeperiod + 1)``

    与 TA-Lib 的差异：TA-Lib 在前 ``timeperiod`` 根上使用简单算术平均作为种子；
    本实现以序列首个观测值作为种子直接迭代，因此结果在前若干根上与 TA-Lib 略有差别。

    :param close: np.ndarray，待平滑的价格序列（一般为收盘价）
    :param timeperiod: int，EMA 周期，默认 5
    :return: np.ndarray，与 ``close`` 等长的 EMA 序列，保留 4 位小数
    """
    res: list[float] = []
    for i in range(len(close)):
        if i < 1:
            # 第一根用原始价格作为种子
            res.append(float(close[i]))
        else:
            ema = (2 * close[i] + res[i - 1] * (timeperiod - 1)) / (timeperiod + 1)
            res.append(ema)
    return np.array(res, dtype=np.double).round(4)


def MACD(
    real: np.ndarray,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """带 2 倍柱状图缩放的 MACD（czsc 仪表盘约定版本）

    返回 ``(diff, dea, macd)`` 三个序列：

    - ``diff = ema(real, fast) - ema(real, slow)``
    - ``dea  = ema(diff, signal)``
    - ``macd = (diff - dea) * 2`` —— 注意相比 TA-Lib 的 MACD 柱状图，这里额外乘以 2，
      以便在仪表盘中读数更直观。

    :param real: np.ndarray，价格序列（一般为收盘价）
    :param fastperiod: int，快线 EMA 周期，默认 12
    :param slowperiod: int，慢线 EMA 周期，默认 26
    :param signalperiod: int，DEA 信号线 EMA 周期，默认 9
    :return: tuple[np.ndarray, np.ndarray, np.ndarray]，``(diff, dea, macd)``，均保留 4 位小数
    """
    ema_fast = EMA(real, timeperiod=fastperiod)
    ema_slow = EMA(real, timeperiod=slowperiod)
    diff = ema_fast - ema_slow
    dea = EMA(diff, timeperiod=signalperiod)
    macd = (diff - dea) * 2
    return diff.round(4), dea.round(4), macd.round(4)
