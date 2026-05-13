"""案例 06：事件驱动 —— Signal → Event → Position

czsc 的策略表达体系层次：

- ``Signal``：单根 K 线 / 单时间点上的市场状态（如 "30分钟_BI状态_向上"）
- ``Event``：信号的逻辑组合，含三种集合
    - ``signals_all``：必须全部满足（AND）
    - ``signals_any``：满足任意一个（OR）
    - ``signals_not``：必须全部不满足（NOT）
- ``Position``：一个完整的多/空策略，由若干"开仓事件 + 平仓事件"驱动，含
  ``interval`` / ``timeout`` / ``stop_loss`` / ``t0`` 等风控参数

本案例展示：

1. 用 dict 声明事件；调用 ``Event.load`` 反序列化
2. 组装 ``Position``，再用一连串 mock 信号字典验证 ``is_match``
3. 通过 ``Position.unique_signals`` 反查所需信号清单（用于 derive 配置）

运行：
    uv run python docs/examples/06_event_position.py
"""

from __future__ import annotations

from czsc import Event, Operate, Position, get_signals_config, get_signals_freqs


def build_long_only_position(symbol: str = "000001") -> Position:
    """构造一个简单的"30 分钟笔向上 -> 开多；向下 -> 平多"策略。"""
    open_event = Event.load(
        {
            "name": "开多_笔向上",
            "operate": "开多",
            # signals_all：全部满足才触发；signals_not：触发时这些必须不满足
            "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"],
            "signals_any": [],
            "signals_not": ["30分钟_D1_涨跌停V230331_涨停_任意_任意_0"],
        }
    )
    exit_event = Event.load(
        {
            "name": "平多_笔向下",
            "operate": "平多",
            "signals_all": ["30分钟_D1_表里关系V230101_向下_任意_任意_0"],
            "signals_any": [],
            "signals_not": [],
        }
    )
    return Position(
        symbol=symbol,
        name="30分钟笔趋势_多头",
        opens=[open_event],
        exits=[exit_event],
        interval=3600 * 4,   # 两次开仓最小间隔 4 小时（秒）
        timeout=16 * 30,     # 最长持仓 K 线根数
        stop_loss=300,       # BP 单位的止损（300 = 3%）
        t0=False,            # 是否 T+0
    )


def demo_event_match() -> None:
    """直接用 ``Event.is_match`` 测试信号字典是否触发事件。"""
    open_event = Event.load(
        {
            "name": "test_open",
            "operate": "开多",
            "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"],
        }
    )

    # 用一个"信号字典"模拟 czsc 内部的 s
    sigs_match = {"30分钟_D1_表里关系V230101": "向上_任意_任意_0"}
    sigs_miss = {"30分钟_D1_表里关系V230101": "向下_任意_任意_0"}
    print("[Event.is_match]")
    print(f"  触发信号  -> {open_event.is_match(sigs_match)}")
    print(f"  不匹配信号 -> {open_event.is_match(sigs_miss)}")


def main() -> None:
    pos = build_long_only_position()
    print("[Position 构造完成]")
    print(f"  名称 = {pos.name}")
    print(f"  品种 = {pos.symbol}")
    print(f"  开仓事件数 = {len(pos.opens)} | 平仓事件数 = {len(pos.exits)}")
    print(f"  风控参数：interval={pos.interval}s, timeout={pos.timeout}, stop_loss={pos.stop_loss}BP, t0={pos.t0}")
    print(f"  当前仓位 = {pos.pos}（0=空仓, 1=多, -1=空）")

    print("\n[Position 涉及的信号]")
    for sig in pos.unique_signals:
        print(f"  {sig}")

    # 反推配置/频率：策略 -> 信号清单 -> 配置 + 涉及周期
    cfgs = get_signals_config(pos.unique_signals)
    freqs = get_signals_freqs(pos.unique_signals)
    print(f"\n[反推] signals_config 共 {len(cfgs)} 项；涉及周期 = {freqs}")
    for cfg in cfgs:
        print(f"  {cfg}")

    print("\n=== 直接演示 Event.is_match ===")
    demo_event_match()

    print("\n下一步：")
    print("  - 把 Position 包装成完整策略类 + 跑回测 -> 07_strategy_backtest.py")


if __name__ == "__main__":
    main()
