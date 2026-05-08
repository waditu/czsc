"""
author: claude-code
create_dt: 2026/05/07
describe: 测试 czsc.utils.trade.stoploss_by_direction —— 按方向止损改写权重序列。

本文件按照 spec §10 P1 中"用 czsc 自实现替代 rs_czsc.stoploss_by_direction"的目标
设计 RED 测试基线。函数语义参考 czsc/svc/backtest.py:show_stoploss_by_direction
对该工具的列契约（raw_weight / weight / order_id / hold_returns / min_hold_returns
/ returns / is_stop）。
"""

from __future__ import annotations

import pandas as pd
import pytest


def _make_dfw(weights: list[float], prices: list[float], symbol: str = "X") -> pd.DataFrame:
    assert len(weights) == len(prices)
    return pd.DataFrame(
        {
            "dt": pd.date_range("2024-01-01", periods=len(prices), freq="D"),
            "symbol": symbol,
            "weight": weights,
            "price": prices,
        }
    )


def test_long_position_no_stop():
    """多头持仓未触发止损：weight 不被改写，is_stop 全 False。"""
    from czsc.utils.trade import stoploss_by_direction

    dfw = _make_dfw(
        weights=[1.0, 1.0, 1.0, 1.0],
        prices=[100.0, 101.0, 102.0, 103.0],
    )
    out = stoploss_by_direction(dfw, stoploss=0.10)

    assert (out["weight"] == 1.0).all()
    assert (out["raw_weight"] == 1.0).all()
    assert out["is_stop"].any() is False or out["is_stop"].sum() == 0
    # 持仓累计收益对长仓 = price[t]/entry - 1
    assert out["hold_returns"].iloc[-1] == pytest.approx(0.03, rel=1e-9)


def test_long_position_triggers_stop():
    """多头持仓在浮亏达到 stoploss 时触发：从触发 bar 起 weight 归零、is_stop=True。"""
    from czsc.utils.trade import stoploss_by_direction

    # 100 -> 92 = -8% 触达 stoploss=0.08
    dfw = _make_dfw(
        weights=[1.0, 1.0, 1.0, 1.0, 1.0],
        prices=[100.0, 95.0, 92.0, 91.0, 90.0],
    )
    out = stoploss_by_direction(dfw, stoploss=0.08)

    # raw_weight 保持原值
    assert (out["raw_weight"] == 1.0).all()
    # 触发点为第三个 bar（index 2，price=92, ret=-0.08）
    assert out["is_stop"].iloc[0] is False or not out["is_stop"].iloc[0]
    assert bool(out["is_stop"].iloc[2]) is True
    # 触发后所有 bar 都标 is_stop 且权重归零
    assert (out.loc[out.index >= 2, "is_stop"]).all()
    assert (out.loc[out.index >= 2, "weight"] == 0.0).all()


def test_short_position_triggers_stop():
    """空头持仓在浮亏达到 stoploss 时触发：方向相反，价格上涨触发止损。"""
    from czsc.utils.trade import stoploss_by_direction

    # 空头 entry=100, price 涨到 110 = -10% 浮亏（空头亏损）
    dfw = _make_dfw(
        weights=[-1.0, -1.0, -1.0, -1.0],
        prices=[100.0, 105.0, 110.0, 115.0],
    )
    out = stoploss_by_direction(dfw, stoploss=0.10)

    # 第三个 bar（index 2, price=110, hold_ret=-0.10）触发
    assert bool(out["is_stop"].iloc[2]) is True
    assert (out.loc[out.index >= 2, "weight"] == 0.0).all()


def test_order_id_increments_on_direction_change():
    """方向切换（含切到 0）时 order_id 自增。"""
    from czsc.utils.trade import stoploss_by_direction

    dfw = _make_dfw(
        weights=[1.0, 1.0, 0.0, -1.0, -1.0],
        prices=[100.0, 101.0, 102.0, 103.0, 104.0],
    )
    out = stoploss_by_direction(dfw, stoploss=0.20)

    # order_id 应该是 3 个不同的值（多 → 空仓 → 空）
    order_ids = out["order_id"].tolist()
    assert order_ids[0] == order_ids[1]
    assert order_ids[2] != order_ids[1]
    assert order_ids[3] == order_ids[4]
    assert order_ids[3] != order_ids[2]


def test_required_output_columns():
    """函数必须返回 svc/backtest.py:show_stoploss_by_direction 所需的全部列。"""
    from czsc.utils.trade import stoploss_by_direction

    dfw = _make_dfw(weights=[1.0, 1.0], prices=[100.0, 101.0])
    out = stoploss_by_direction(dfw, stoploss=0.05)

    required = {
        "dt",
        "symbol",
        "raw_weight",
        "weight",
        "price",
        "hold_returns",
        "min_hold_returns",
        "returns",
        "order_id",
        "is_stop",
    }
    assert required.issubset(set(out.columns))


def test_input_dfw_not_mutated():
    """函数不能就地修改入参（show_stoploss_by_direction 的 .copy() 已经先做了一层防御）。"""
    from czsc.utils.trade import stoploss_by_direction

    dfw = _make_dfw(weights=[1.0, 1.0, 1.0], prices=[100.0, 92.0, 90.0])
    cols_before = set(dfw.columns)
    _ = stoploss_by_direction(dfw, stoploss=0.05)
    assert set(dfw.columns) == cols_before  # 未给原 df 加列
