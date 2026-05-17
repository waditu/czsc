"""探索性分析（EDA）入口。

历史上本模块汇集 ``monotonicity`` / ``mark_cta_periods`` / ``mark_volatility``
三个工具函数。

- 2026-05-17 PR-B 起：``mark_cta_periods`` 与 ``mark_volatility`` 已拆分到
  :mod:`czsc.utils.mark_cta_periods` / :mod:`czsc.utils.mark_volatility` 独立
  文件，本模块仅为不破坏 ``from czsc.eda import mark_cta_periods`` 的历史
  导入路径做 re-export，新增代码请直接走 ``czsc.utils.*``。
- ``monotonicity`` 留待下一阶段 PR-D Rust 化（届时本文件会进一步精简或删除）。
"""

from __future__ import annotations

from czsc.utils.mark_cta_periods import mark_cta_periods
from czsc.utils.mark_volatility import mark_volatility


def monotonicity(sequence):
    """计算序列的单调性

    原理：计算序列与自然数序列的相关系数，系数越接近1，表示单调递增；系数越接近-1，表示单调递减；接近0表示无序

    :param sequence: list, tuple 序列
    :return: float, 单调性系数
    """
    from scipy.stats import spearmanr

    return spearmanr(sequence, range(len(sequence)))[0]


__all__ = ["mark_cta_periods", "mark_volatility", "monotonicity"]
