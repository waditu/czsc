"""czsc.utils.analysis —— 通用分析工具模块。

本子包汇集了 CZSC 中与“事后分析 / 评估”相关的常用工具函数，主要分为两大类：

- 相关性分析（``corr``）：
    * :func:`cross_sectional_ic`  —— 横截面 IC（Information Coefficient）计算，
      用于衡量因子值与未来收益之间的相关性；
    * :func:`nmi_matrix`           —— 归一化互信息（Normalized Mutual Information）
      矩阵，刻画多个变量两两之间的非线性相关程度；
    * :func:`single_linear`        —— 单变量线性回归的便捷封装。

- 业绩与统计（``stats``）：
    * :func:`daily_performance`         —— 日频策略业绩指标（年化收益、夏普、
      最大回撤、卡玛比率等）；
    * :func:`rolling_daily_performance` —— 在滚动窗口上计算上述业绩指标，
      便于绘制业绩稳定性曲线；
    * :func:`holds_performance`         —— 基于持仓权重序列计算业绩；
    * :func:`top_drawdowns`             —— 提取最大的若干段回撤区间；
    * :func:`psi`                       —— PSI（Population Stability Index）
      群体稳定性指标，用于因子稳定性监控。

所有函数均通过 ``__all__`` 显式公开，保证 ``from czsc.utils.analysis import *``
的行为可预期。
"""

# 相关性分析相关函数
from .corr import cross_sectional_ic, nmi_matrix, single_linear

# 业绩与统计相关函数
from .stats import (
    daily_performance,
    holds_performance,
    psi,
    rolling_daily_performance,
    top_drawdowns,
)

# 显式声明对外公开的符号，避免 ``from xxx import *`` 时引入过多内部依赖
__all__ = [
    "cross_sectional_ic",
    "daily_performance",
    "holds_performance",
    "nmi_matrix",
    "psi",
    "rolling_daily_performance",
    "single_linear",
    "top_drawdowns",
]
