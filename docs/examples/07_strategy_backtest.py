"""案例 07：自定义策略类 + 回测 + 回放

继承 ``CzscStrategyBase`` 是 czsc 推荐的策略组织方式：

- 子类只需实现 ``positions`` 属性（返回 ``list[Position]``）
- 框架自动派生 ``signals_config`` / ``freqs`` / ``base_freq``
- ``backtest()`` 内存执行；``replay()`` 落盘 parquet 产物

本案例完整演示：从策略类定义到内存回测到落盘回放，并解读返回的
``ResearchResult`` / ``ReplayResult``（含 signals/pairs/holds 三份 Arrow 字节）。

运行：
    uv run python docs/examples/07_strategy_backtest.py

输出：
    - 控制台打印各产物的形状与典型字段
    - 在 docs/examples/_output/07_strategy_backtest/ 下落盘 parquet 与 Position JSON
      （目录已在 .gitignore 中忽略）
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.ipc as ipc

from czsc import CzscStrategyBase, Event, Position, format_standard_kline
from czsc.mock import generate_symbol_kines

# 所有案例统一把产物落到 docs/examples/_output/
OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPLAY_DIR = OUTPUT_DIR / "07_strategy_backtest"


# ----------------------------- 策略类定义 ----------------------------- #


def _build_long_short_position(symbol: str, base_freq: str) -> Position:
    """笔表里关系：向上开多、向下开空，涨跌停时禁止开仓。

    与 ``tests/parity/test_examples.py`` 中的 30 分钟示例保持一致，
    确保策略在生产路径上有充分回归测试覆盖。
    """
    opens = [
        Event.load(
            {
                "operate": "开多",
                "signals_all": [f"{base_freq}_D1_表里关系V230101_向上_任意_任意_0"],
                "signals_not": [f"{base_freq}_D1_涨跌停V230331_涨停_任意_任意_0"],
            }
        ),
        Event.load(
            {
                "operate": "开空",
                "signals_all": [f"{base_freq}_D1_表里关系V230101_向下_任意_任意_0"],
                "signals_not": [f"{base_freq}_D1_涨跌停V230331_跌停_任意_任意_0"],
            }
        ),
    ]
    return Position(
        name=f"{base_freq}笔非多即空",
        symbol=symbol,
        opens=opens,
        exits=[],            # 反手开仓即平
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )


class LongShortStrategy(CzscStrategyBase):
    """三个时间周期同时启用"笔非多即空"，多策略集成。"""

    @property
    def positions(self) -> list[Position]:
        return [
            _build_long_short_position(self.symbol, "30分钟"),
            _build_long_short_position(self.symbol, "60分钟"),
            _build_long_short_position(self.symbol, "日线"),
        ]


# ------------------------------ 工具函数 ------------------------------ #


def _arrow_to_df(arrow_bytes: bytes) -> pd.DataFrame:
    """把 Arrow IPC 字节流读回 pandas DataFrame。"""
    with ipc.open_file(arrow_bytes) as reader:
        return reader.read_all().to_pandas()


# --------------------------------- main --------------------------------- #


def main() -> None:
    # 1) 准备 30 分钟基础 K 线
    df = generate_symbol_kines("000001", "30分钟", "20200101", "20240101", seed=42)
    bars = format_standard_kline(df, freq="30分钟")
    print(f"[数据] {bars[0].symbol}  {len(bars)} 根 30 分钟 K 线")

    # 2) 实例化策略，框架自动派生信号配置/频率
    tactic = LongShortStrategy(symbol="000001")
    print(f"[策略] {tactic.__class__.__name__}")
    print(f"  base_freq = {tactic.base_freq}")
    print(f"  freqs = {tactic.freqs}")
    print(f"  signals_config 共 {len(tactic.signals_config)} 项（前 3 项）：")
    for cfg in tactic.signals_config[:3]:
        print(f"    {cfg}")

    # 3) 内存回测：返回 ResearchResult
    res = tactic.backtest(bars, sdt="2020-06-01")
    print("\n[回测产物 ResearchResult]")
    pairs = _arrow_to_df(res.pairs_arrow)
    holds = _arrow_to_df(res.holds_arrow)
    signals = _arrow_to_df(res.signals_arrow)
    print(f"  signals: shape={signals.shape}, 列示例={signals.columns.tolist()[:6]}")
    print(f"  pairs:   shape={pairs.shape}, 列示例={pairs.columns.tolist()[:6]}")
    print(f"  holds:   shape={holds.shape}, 列示例={holds.columns.tolist()[:6]}")

    if not pairs.empty:
        # pairs 是"完整开平仓对"，含开仓时间、平仓时间、收益等
        print("\n[最近 3 个交易对]")
        cols = [c for c in ["开仓时间", "平仓时间", "开仓价格", "平仓价格", "盈亏比例"] if c in pairs.columns]
        print(pairs.tail(3)[cols].to_string(index=False))

    # 4) 回放：落盘 parquet 产物（注意 refresh=True 会清空旧产物）
    replay_res = tactic.replay(bars, res_path=REPLAY_DIR, sdt="2020-06-01", refresh=True)
    print(f"\n[回放] 已落盘到 {REPLAY_DIR}/，目录内文件：")
    for p in sorted(REPLAY_DIR.glob("**/*.parquet")):
        print(f"  {p.relative_to(REPLAY_DIR)}  size={p.stat().st_size}")

    # 5) 持仓策略可单独序列化（用于策略市场 / 优化器）
    pos_dir = REPLAY_DIR / "positions"
    tactic.save_positions(pos_dir)
    print(f"\n[Position dump] 已写入 {pos_dir}/，可用 CzscJsonStrategy 重新加载")
    for p in sorted(pos_dir.glob("*.json")):
        print(f"  {p.name}")

    print("\n下一步：")
    print("  - 把回测得到的权重序列做更精细的回测分析 -> 08_weight_backtest.py")
    print("  - 用 lightweight-charts HTML 看每个 Position 的开平仓点 -> 13_lightweight_charts_html.py")


if __name__ == "__main__":
    main()
