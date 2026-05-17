"""探索性分析（EDA）模块的兼容入口。

2026-05-17 PR-D 起：

- ``monotonicity`` 已迁到 Rust 实现（:mod:`czsc._native.monotonicity`），
  本模块只做 re-export，行为与原 Python 版本一致（与
  ``scipy.stats.spearmanr`` 等价），但去掉了对 scipy 的直接依赖；
- ``mark_cta_periods`` / ``mark_volatility`` 已于 PR-B 拆到
  :mod:`czsc.utils.mark_cta_periods` / :mod:`czsc.utils.mark_volatility`，
  本模块仅保留 re-export 以维持 ``from czsc.eda import ...`` 的历史路径。

新代码请直接走 ``czsc.*`` 顶层或 ``czsc.utils.*`` / ``czsc._native.*``。
"""

from __future__ import annotations

from czsc._native import monotonicity
from czsc.utils.mark_cta_periods import mark_cta_periods
from czsc.utils.mark_volatility import mark_volatility

__all__ = ["mark_cta_periods", "mark_volatility", "monotonicity"]
