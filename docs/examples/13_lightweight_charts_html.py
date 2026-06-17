"""案例 13：lightweight_charts 缠论可视化（离线 HTML 版）

把 ``CZSC`` / ``CzscTrader`` 用 TradingView 的 Lightweight Charts JS 绘制成
自包含 HTML 文件，可分享、可嵌入研报。整页只有一个 ``<script src="...">`` 指向
CDN，文件本身不到 1 MB。

每个周期展开为三张子图：

- **主图**：K 线 + SMA5 + SMA20 + 分型 marker + 笔 zigzag
- **副图 1**：成交量柱状图（红涨绿跌）
- **副图 2**：MACD（DIFF / DEA + 柱）

运行：
    uv run python docs/examples/13_lightweight_charts_html.py
    # 产物在 docs/examples/_output/13_lwc_single.html 与 13_lwc_multi.html
"""

from __future__ import annotations

from pathlib import Path

from czsc import CZSC, BarGenerator, Freq, format_standard_kline
from czsc._native import CzscTrader
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import plot_czsc, plot_czsc_trader

OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def demo_single() -> Path:
    """方式 A：单周期，直接传 CZSC。"""
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20240301", seed=42)
    c = CZSC(format_standard_kline(df, freq=Freq.F30))
    out = OUTPUT_DIR / "13_lwc_single.html"
    plot_czsc(c, output="html", path=out, title=f"{c.symbol} · {c.freq.value} 缠论结构（单周期）")
    return out


def demo_multi() -> Path:
    """方式 B：多周期，用 CzscTrader 合成。"""
    df = generate_symbol_kines("000001", "30分钟", "20220101", "20240301", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    bg = BarGenerator(base_freq="30分钟", freqs=["30分钟", "60分钟", "日线"], max_count=5000)
    for bar in bars:
        bg.update(bar)
    ct = CzscTrader(bg, positions=[], signals_config=[])
    out = OUTPUT_DIR / "13_lwc_multi.html"
    plot_czsc_trader(
        ct,
        output="html",
        path=out,
        title=f"{ct.symbol} · 多周期缠论结构（日线 / 60分钟 / 30分钟）",
        tail_bars=400,
    )
    return out


def main() -> None:
    print("[案例 13] 生成 lightweight_charts 缠论 HTML...")
    p1 = demo_single()
    print(f"  · 单周期：{p1}  ({p1.stat().st_size / 1024:.1f} KB)")
    p2 = demo_multi()
    print(f"  · 多周期：{p2}  ({p2.stat().st_size / 1024:.1f} KB)")
    print("\n双击上面任意 HTML 文件用浏览器打开即可（需要联网加载 lightweight-charts CDN）。")


if __name__ == "__main__":
    main()
