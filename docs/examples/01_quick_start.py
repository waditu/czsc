"""案例 01：CZSC 快速入门 —— 从数据到缠论分析对象

本案例覆盖 czsc 库最核心的入口流程：

1. 准备 K 线数据（使用 czsc.mock 生成模拟数据，无需外部行情源）
2. 标准化为 RawBar 列表（czsc 的统一行情数据结构）
3. 构造 CZSC 分析对象，自动完成分型/笔识别
4. 查看分析结果的关键属性

运行：
    uv run python docs/examples/01_quick_start.py

依赖：仅依赖 czsc 顶层包（已包含 wbt + Rust 扩展）。
"""

from __future__ import annotations

import czsc
from czsc import CZSC, Freq, format_standard_kline
from czsc.mock import generate_symbol_kines


def main() -> None:
    # 1) 打印环境信息（版本号、缓存路径等）
    print("=" * 60)
    print(f"czsc 版本：{czsc.__version__}@{czsc.__date__}")
    print(f"最小笔长度：{czsc.envs.get_min_bi_len()}")
    print(f"最大笔数量：{czsc.envs.get_max_bi_num()}")
    print("=" * 60)

    # 2) 生成模拟 K 线数据
    # generate_symbol_kines 转发到 wbt.mock.mock_symbol_kline，给定 seed 即可复现
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20240601", seed=42)
    print(f"\n[数据] DataFrame shape={df.shape}, 列={df.columns.tolist()}")
    print(df.head(3).to_string(index=False))

    # 3) 转 DataFrame -> List[RawBar]，传入 CZSC 分析器
    bars = format_standard_kline(df, freq=Freq.F30)
    print(f"\n[数据] RawBar 数量={len(bars)}, 第一根={bars[0]}")

    c = CZSC(bars)
    print("\n[CZSC]")
    print(f"  品种 = {c.symbol}")
    print(f"  周期 = {c.freq}")
    print(f"  原始 K 线数 = {len(c.bars_raw)}")
    print(f"  无包含 K 线数 = {len(c.bars_ubi)}")
    print(f"  分型数 = {len(c.fx_list)}")
    print(f"  完成笔数 = {len(c.bi_list)}")
    print(f"  最后一笔是否在延伸中 = {c.last_bi_extend}")

    # 4) 增量更新：CZSC 支持逐根 K 线推进，适合实盘场景
    df2 = generate_symbol_kines("000001", "30分钟", "20240601", "20240701", seed=42)
    new_bars = format_standard_kline(df2, freq=Freq.F30)
    for bar in new_bars[:10]:
        c.update(bar)
    print(f"\n[增量更新后] 笔数 = {len(c.bi_list)}, 最新 K 线时间 = {c.bars_raw[-1].dt}")

    # 5) 关联性提示
    print("\n下一步：")
    print("  - 想看缠论结构（分型/笔/中枢）的详细属性 -> 02_chan_structures.py")
    print("  - 想用 plotly 把分型/笔画出来 -> 03_kline_chart.py")
    print("  - 想做多级别联立分析 -> 04_bar_generator.py")


if __name__ == "__main__":
    main()
