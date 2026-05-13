"""案例 04：K 线合成与多级别联立（BarGenerator）

``BarGenerator`` 将低级别 K 线（如 30 分钟）实时合成为高级别 K 线
（如日线、周线），是缠论"多级别联立分析"的基础设施。

本案例演示：

1. 用 30 分钟基础数据合成 30 分钟 / 60 分钟 / 日线 三档周期
2. 在每个周期上分别构造 ``CZSC`` 分析对象
3. 直观对比同一时间点上不同周期的笔结构

关联：``CzscSignals`` / ``CzscTrader`` 内部都使用 ``BarGenerator`` 维护多周期 K 线。

运行：
    uv run python docs/examples/04_bar_generator.py
"""

from __future__ import annotations

from czsc import CZSC, BarGenerator, Freq, format_standard_kline, freqs_sorted
from czsc.mock import generate_symbol_kines


def main() -> None:
    base_freq = "30分钟"
    target_freqs = ["30分钟", "60分钟", "日线"]

    # 1) 准备 30 分钟基础 K 线（约 4 年）
    df = generate_symbol_kines("000001", base_freq, "20200101", "20240101", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)

    # 2) 创建 BarGenerator，逐根 K 线 update 完成多级别合成
    bg = BarGenerator(base_freq=base_freq, freqs=target_freqs, max_count=5000)
    for bar in bars:
        bg.update(bar)

    print(f"[品种] {bg.symbol}")
    print(f"[基础周期] {bg.base_freq}")
    print(f"[最新时间] {bg.get_latest_date()}")
    for freq in freqs_sorted(target_freqs):
        kbars = bg.bars[freq]
        print(f"  {freq}: {len(kbars)} 根，最新 = {kbars[-1].dt}")

    # 3) 在每个周期上构造 CZSC，对比笔结构
    print("\n[多级别 CZSC 分析]")
    for freq in freqs_sorted(target_freqs):
        c = CZSC(bg.bars[freq])
        print(
            f"  {freq:<6}  K线={len(c.bars_raw):>6}  分型={len(c.fx_list):>4}  "
            f"笔={len(c.bi_list):>3}  最后笔方向={c.bi_list[-1].direction if c.bi_list else 'N/A'}"
        )

    # 4) 模拟实盘：用一段新数据继续 update，验证增量合成
    print("\n[增量合成]")
    df2 = generate_symbol_kines("000001", base_freq, "20240101", "20240115", seed=42)
    new_bars = format_standard_kline(df2, freq=Freq.F30)
    for bar in new_bars:
        bg.update(bar)
    for freq in freqs_sorted(target_freqs):
        kbars = bg.bars[freq]
        print(f"  {freq}: {len(kbars)} 根，最新 = {kbars[-1].dt}")


if __name__ == "__main__":
    main()
