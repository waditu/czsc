"""czsc.utils.analysis —— 通用分析工具模块。

本子包目前只保留相关性分析模块（``corr``）：

* :func:`cross_sectional_ic`  —— 横截面 IC（Information Coefficient）计算，
  用于衡量因子值与未来收益之间的相关性。

2026-05-17 PR-A 起：

- 删除 ``nmi_matrix`` / ``single_linear``（合并入 ``corr.py`` 私有实现路径，
  公共 API 不再暴露），同时 czsc 不再依赖 ``scikit-learn``；
- 删除 ``stats`` 子模块（5 个函数全部下线）。``daily_performance`` /
  ``top_drawdowns`` 仍可通过 :mod:`czsc` 顶层访问（来自 ``wbt``），但本子包
  不再 re-export。
"""

from .corr import cross_sectional_ic

# 显式声明对外公开的符号，避免 ``from xxx import *`` 时引入过多内部依赖
__all__ = [
    "cross_sectional_ic",
]
