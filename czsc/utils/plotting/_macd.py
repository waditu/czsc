"""czsc 仪表盘场景的 MACD（柱状图 ×2）私有实现。

历史上该函数定义在 ``czsc/utils/ta.py``，仅 czsc 仪表盘绘图链路使用、且柱状图
额外乘以 2 不属于标准做法，因此不迁移到 Rust，改为收敛在 plotting 内部作为
私有辅助函数。

仅供 ``czsc.utils.plotting`` 内部使用（kline / lightweight），不对外暴露。
"""

from __future__ import annotations

import numpy as np

__all__ = ["compute_macd"]


def _ema(close: np.ndarray, period: int) -> np.ndarray:
    """czsc 约定的 EMA 实现：以序列首值为种子直接递推。

    与 TA-Lib 的差异：TA-Lib 在前 ``period`` 根上使用算术均值作为种子，
    本实现以首根价格作种子，因此前若干根数值有差异。这是 czsc 仪表盘的
    历史约定，保持不变。
    """
    res: list[float] = []
    for i in range(len(close)):
        if i < 1:
            res.append(float(close[i]))
        else:
            ema = (2 * close[i] + res[i - 1] * (period - 1)) / (period + 1)
            res.append(ema)
    return np.array(res, dtype=np.double).round(4)


def compute_macd(
    real: np.ndarray,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 ``(diff, dea, macd)``，其中 ``macd = (diff - dea) * 2``（×2 是约定）。"""
    ema_fast = _ema(real, period=fastperiod)
    ema_slow = _ema(real, period=slowperiod)
    diff = ema_fast - ema_slow
    dea = _ema(diff, period=signalperiod)
    macd = (diff - dea) * 2
    return diff.round(4), dea.round(4), macd.round(4)
