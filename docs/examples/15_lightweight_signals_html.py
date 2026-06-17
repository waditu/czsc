"""案例 15：lightweight_charts 信号叠加（离线 HTML 版）

把多个信号函数的历史触发点叠加到 K 线主图：

- 每个 signal key 一个独立颜色 marker
- 同一 key 下，value 与上一个值一致时不再画 marker（只标 transition）
- hover K 线弹出的 tooltip 含 SIGNALS 段，显示完整 value（v1_v2_v3_score）

运行：
    uv run --no-sync python docs/examples/15_lightweight_signals_html.py
    # 产物：docs/examples/_output/15_lwc_signals.html
"""

from __future__ import annotations

from pathlib import Path

from czsc import Freq, format_standard_kline
from czsc.mock import generate_symbol_kines
from czsc.utils.plotting.lightweight import plot_czsc_signals

OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_CONFIG = [
    {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    {"name": "cxt_bi_status_V230101", "freq": "日线"},
    {"name": "tas_ma_base_V221101", "freq": "日线", "di": 1, "timeperiod": 5, "ma_type": "SMA"},
    {"name": "bar_zdt_V230331", "freq": "30分钟", "di": 1},
]


def main() -> Path:
    print("[案例 15] 生成 lightweight_charts 信号叠加 HTML...")
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20240301", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    out = OUTPUT_DIR / "15_lwc_signals.html"
    plot_czsc_signals(
        bars,
        signals_config=SIGNALS_CONFIG,
        output="html",
        path=out,
        title="000001 · 多信号历史触发可视化（lightweight_charts）",
        tail_bars=600,
    )
    print(f"  · 落盘：{out}  ({out.stat().st_size / 1024:.1f} KB)")
    print("\n双击 HTML 用浏览器打开（需联网加载 lightweight-charts CDN）。")
    return out


if __name__ == "__main__":
    main()
