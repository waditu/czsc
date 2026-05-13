"""案例 02：缠论核心结构深入分析（分型 / 笔 / 中枢）

本案例展示 czsc 缠论分析的关键数据结构：

- ``FX``（分型）：顶分型、底分型，含强度等属性
- ``BI``（笔）：方向、长度、力度（power/snr/slope/angle）
- ``ZS``（中枢）：基于笔列表构造，含上下沿/中轴

并演示如何从 ``CZSC`` 分析对象中提取上述结构、做后处理。

运行：
    uv run python docs/examples/02_chan_structures.py
"""

from __future__ import annotations

from czsc import CZSC, ZS, Freq, Mark, Direction, format_standard_kline
from czsc.mock import generate_symbol_kines


def show_fx(c: CZSC, n: int = 5) -> None:
    """打印前 n 个分型的关键属性。"""
    print(f"\n=== 前 {n} 个分型 ===")
    for i, fx in enumerate(c.fx_list[:n], 1):
        kind = "顶分型" if fx.mark == Mark.G else "底分型"
        print(
            f"  分型#{i}  {kind}  时间={fx.dt}  价格={fx.fx:.3f}  "
            f"强度={fx.power_str}  成交量力度={fx.power_volume:.1f}"
        )


def show_bi(c: CZSC, n: int = 5) -> None:
    """打印前 n 笔的形态、力度等指标。"""
    print(f"\n=== 前 {n} 笔（共 {len(c.bi_list)} 笔） ===")
    for i, bi in enumerate(c.bi_list[:n], 1):
        arrow = "↑" if bi.direction == Direction.Up else "↓"
        print(
            f"  笔#{i} {arrow}  {bi.sdt:%Y-%m-%d %H:%M} -> {bi.edt:%Y-%m-%d %H:%M}\n"
            f"          价差力度={bi.power:.3f}  涨跌幅={bi.change:.3%}  "
            f"长度={bi.length}根  斜率={bi.slope:.3f}\n"
            f"          SNR={bi.SNR:.3f}  rsq={bi.rsq:.3f}  夹角={bi.angle:.2f}°"
        )


def show_zs(c: CZSC) -> None:
    """从最近若干笔中构造中枢并打印其属性。"""
    if len(c.bi_list) < 3:
        print("\n[中枢] 笔数不足 3，无法构造中枢")
        return
    # ZS 接受 bis（笔列表），用最近若干笔做演示
    recent = c.bi_list[-7:]
    zs = ZS(recent)
    print("\n=== 最近 7 笔尝试构造的中枢 ===")
    print(f"  是否有效 = {zs.is_valid()}")
    if zs.is_valid():
        print(f"  中枢区间：[{zs.zd:.3f}, {zs.zg:.3f}]  中轴 zz={zs.zz:.3f}")
        print(f"  极值范围：[{zs.dd:.3f}, {zs.gg:.3f}]")
        print(f"  起始时间 = {zs.sdt}")
        print(f"  结束时间 = {zs.edt}")
        print(f"  方向变化：{zs.sdir} -> {zs.edir}")


def show_ubi(c: CZSC) -> None:
    """无包含关系（unmerged bars in incomplete bi）状态。"""
    print("\n=== 未完成笔（ubi）===")
    ubi = c.ubi
    if ubi:
        print(
            f"  方向={ubi.get('direction')}  "
            f"高={ubi.get('high'):.3f}  低={ubi.get('low'):.3f}"
        )


def main() -> None:
    # 用相对长一点的样本，确保有足够分型/笔/中枢可分析
    df = generate_symbol_kines("000001", "30分钟", "20210101", "20240101", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    c = CZSC(bars)

    print(f"[CZSC] {c.symbol} {c.freq} 共 {len(c.bars_raw)} 根 K 线")
    print(f"[CZSC] 分型 {len(c.fx_list)}，完成笔 {len(c.bi_list)}")

    show_fx(c, n=5)
    show_bi(c, n=5)
    show_zs(c)
    show_ubi(c)

    # 把 K 线数据导出为 DataFrame，便于和外部分析工具协作
    df_bars = c.bars_raw_df
    print(f"\n[bars_raw_df] shape={df_bars.shape}, 列={df_bars.columns.tolist()}")


if __name__ == "__main__":
    main()
