"""``CzscStrategyBase.unique_signals`` Rust 透传契约测试。

2026-05-17 PR-F：unique_signals 的去重 / 保序逻辑已下沉到 Rust
（``czsc._native.strategy_unique_signals`` /
``czsc_trader::strategy::unique_signals_across``）。

本文件锁定两条契约：

1. Python 侧的 ``CzscStrategyBase.unique_signals`` 必须把工作完整委托给
   ``czsc._native.strategy_unique_signals``，不能再回退到纯 Python 实现；
2. Rust 实现的语义与历史 Python 行为等价：跨 Position 扁平化 + 首次出现保序。

任一项被回退（例如有人误改回 Python for-loop）都会让本测试红，从而暴露
开发宪法第一条的违规。
"""

from __future__ import annotations

from czsc import CzscStrategyBase
from czsc._native import Event, Operate, Position, Signal, strategy_unique_signals


def _signal(suffix: str) -> str:
    """构造一个 7 段式合法 Signal 字符串，唯一变化点是 k2 段。"""
    return f"日线_{suffix}_kind_v1_v2_v3_0"


def _make_position(name: str, signals: list[str]) -> Position:
    """构造一个最小可序列化 Position：单 open 事件，单 exit 事件。"""
    open_event = Event(
        operate=Operate.LO,
        signals_all=[Signal(s) for s in signals],
        signals_any=[],
        signals_not=[],
    )
    exit_event = Event(
        operate=Operate.LE,
        signals_all=[],
        signals_any=[],
        signals_not=[],
    )
    return Position(symbol="TEST", opens=[open_event], exits=[exit_event], name=name)


class _DummyStrategy(CzscStrategyBase):
    """覆盖 positions 让 CzscStrategyBase 可实例化。"""

    @property
    def positions(self):
        return self.kwargs["_positions"]


def test_strategy_unique_signals_dedups_in_order() -> None:
    """跨 position 扁平化 + 首次出现保序（与历史 Python 行为一致）。"""
    p1 = _make_position("p1", [_signal("siga"), _signal("sigb")])
    p2 = _make_position("p2", [_signal("sigb"), _signal("sigc")])

    rust = strategy_unique_signals([p1, p2])

    # sigb 在 p1 已经出现，p2 重复出现时丢弃；最终顺序保留首次出现位置
    assert rust == [_signal("siga"), _signal("sigb"), _signal("sigc")]


def test_czsc_strategy_base_unique_signals_delegates_to_rust() -> None:
    """开发宪法第一条：Python 侧必须是 Rust 实现的纯透传，不能自行计算。"""
    p1 = _make_position("p1", [_signal("alpha"), _signal("beta")])
    p2 = _make_position("p2", [_signal("beta"), _signal("gamma")])
    tactic = _DummyStrategy(symbol="TEST", _positions=[p1, p2])

    direct = strategy_unique_signals([p1, p2])
    assert tactic.unique_signals == direct, "CzscStrategyBase.unique_signals 必须走 Rust 透传"


def test_strategy_unique_signals_empty_positions() -> None:
    """空持仓列表应返回空列表（边界覆盖）。"""
    assert strategy_unique_signals([]) == []
