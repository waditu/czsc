"""czsc.sensors —— 事件检测与特征分析命名空间。

按 spec §9，本包目标承载三类传感器能力：

1. **CTA 研究框架**：策略回放、参数优化、并行回测——以 ``CTAResearch`` 类为核心
2. **特征选择器**：基于滚动窗口的因子选择与分析
3. **事件匹配器**：把信号组合成事件并在历史数据上扫描匹配

当前阶段已恢复 ``utils`` 子模块（``holds_concepts_effect`` /
``turn_over_rate`` / ``max_draw_down`` 三个纯 numpy/pandas 工具，无内部 czsc
依赖）。``CTAResearch`` 历史实现依赖已删除的 ``czsc.traders.dummy.DummyBacktest``
（spec §3.3 已经把 dummy 替换为 ``czsc.run_replay`` / wbt），因此暂时保留为
``NotImplementedError`` 占位，等 Phase G 在 Rust 端 ``czsc-trader`` 提供
等价的 dummy/replay 后再恢复实现。
"""

from __future__ import annotations

from czsc.sensors.utils import (
    holds_concepts_effect,
    max_draw_down,
    turn_over_rate,
)


class CTAResearch:
    """spec §9 中的 CTA 研究框架占位类。

    历史实现依赖 ``czsc.traders.dummy.DummyBacktest``；该模块已按 spec §3.3
    在 Phase J 删除（被 ``czsc.run_replay`` / ``wbt.WeightBacktest`` 取代）。
    完整恢复需要先在 Rust 端 ``czsc-trader`` 提供等价能力，详见
    ``docs/MIGRATION_NOTES.md`` §10.2。

    在那之前，实例化此类会立即抛 :class:`NotImplementedError`，明确告知用户
    迁移路径，而不是让代码在运行半截后才报"找不到 DummyBacktest"。
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "czsc.sensors.CTAResearch 暂未恢复——历史实现依赖已删除的 "
            "czsc.traders.dummy.DummyBacktest（spec §3.3 / Phase J）。"
            "请改用 czsc.run_replay / czsc.run_research / czsc.WeightBacktest "
            "组合达成等价工作流；或关注 docs/MIGRATION_NOTES.md §10.2 中"
            "对该项的恢复计划。"
        )


__all__ = [
    "CTAResearch",
    "holds_concepts_effect",
    "max_draw_down",
    "turn_over_rate",
]
