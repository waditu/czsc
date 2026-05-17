"""案例 17：性能基准 —— CZSC vs CzscTrader 在 20 年 5 分钟 K 线上的吞吐量

本案例用 czsc.mock 生成 20 年 5 分钟 K 线，分别在两种典型路径下做性能基准：

1. ``CZSC`` —— 单周期纯结构分析（分型 / 笔 / 中枢识别）
   - 一次性 ``CZSC(bars)`` 构造
   - 逐根 ``c.update(bar)`` 增量推进（模拟实盘）
2. ``CzscTrader`` —— 5 分钟为基础周期 + 30 分钟 / 日线联立 + 1 个 Position
   - 逐根 ``trader.update(bar)`` 推进（事件驱动 + 多级别合成 + 信号 + 决策）

仅打印文本性能指标（耗时 + 吞吐量），不产出任何 HTML / 绘图。

运行：
    uv run python docs/examples/17_perf_benchmark.py
"""

from __future__ import annotations

import time

import czsc
from czsc import (
    CZSC,
    BarGenerator,
    CzscTrader,
    Event,
    Freq,
    Position,
    format_standard_kline,
    get_signals_config,
)
from czsc.mock import generate_symbol_kines

SYMBOL = "000001"
BASE_FREQ = "5分钟"
SDT = "20050101"
EDT = "20250101"
TARGET_FREQS = ["5分钟", "30分钟", "日线"]


def _fmt_rate(n: int, sec: float) -> str:
    if sec <= 0:
        return "n/a"
    return f"{n / sec:>10,.0f} bars/s"


def _print_row(label: str, sec: float, n: int) -> None:
    print(f"  {label:<18} {sec:>8.3f} s   {_fmt_rate(n, sec)}")


def bench_czsc(bars: list) -> None:
    print(f"\n[CZSC] 单周期 {BASE_FREQ} 结构分析  共 {len(bars):,} 根")

    # 1) 一次性构造：把全量 bars 喂给 CZSC，内部一次走完分型/笔识别
    t0 = time.perf_counter()
    c_full = CZSC(bars)
    t_full = time.perf_counter() - t0
    _print_row("一次性构造", t_full, len(bars))
    print(
        f"    结构: 分型={len(c_full.fx_list):>5}  完成笔={len(c_full.bi_list):>5}  "
        f"无包含K线={len(c_full.bars_ubi):>5}"
    )

    # 2) 增量 update：先用首根 bar 构造，再 .update() 推进，模拟实盘
    c_inc = CZSC(bars[:1])
    t0 = time.perf_counter()
    for bar in bars[1:]:
        c_inc.update(bar)
    t_inc = time.perf_counter() - t0
    _print_row("增量 update", t_inc, len(bars) - 1)
    print(f"    结构: 完成笔={len(c_inc.bi_list):>5}（应与一次性构造一致）")


def _build_long_short_position(symbol: str, base_freq: str) -> Position:
    """5 分钟笔表里关系 —— 向上开多、向下开空（反手为平）。"""
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
        exits=[],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )


def bench_trader(bars: list) -> None:
    print(
        f"\n[CzscTrader] base={BASE_FREQ}  freqs={TARGET_FREQS}  + 1 个 Position  "
        f"共 {len(bars):,} 根"
    )

    position = _build_long_short_position(bars[0].symbol, BASE_FREQ)
    signals_config = get_signals_config(position.unique_signals)
    bg = BarGenerator(base_freq=BASE_FREQ, freqs=TARGET_FREQS, max_count=5000)
    trader = CzscTrader(bg, positions=[position], signals_config=signals_config)

    t0 = time.perf_counter()
    for bar in bars:
        trader.update(bar)
    t_inc = time.perf_counter() - t0
    _print_row("增量 update", t_inc, len(bars))

    pos = trader.positions[0]
    ops = pos.operates or []
    pairs = pos.pairs or []
    print(
        f"    Position: 触发操作={len(ops):>5}  完整交易对={len(pairs):>5}  "
        f"最终仓位={pos.pos}"
    )


def main() -> None:
    print("=" * 72)
    print(f"czsc 版本：{czsc.__version__}@{czsc.__date__}")
    print(f"基准设定：symbol={SYMBOL}  base={BASE_FREQ}  {SDT} ~ {EDT}")
    print("=" * 72)

    # 1) mock 20 年 5 分钟 K 线
    t0 = time.perf_counter()
    df = generate_symbol_kines(SYMBOL, BASE_FREQ, SDT, EDT, seed=42)
    t_mock = time.perf_counter() - t0
    print(f"\n[数据] mock 5 分钟 K 线: shape={df.shape}  耗时 {t_mock:.3f}s")

    t0 = time.perf_counter()
    bars = format_standard_kline(df, freq=Freq.F5)
    t_fmt = time.perf_counter() - t0
    print(f"[数据] format_standard_kline -> RawBar 列表: {len(bars):,} 根  耗时 {t_fmt:.3f}s")
    print(f"[数据] 时间范围: {bars[0].dt}  ~  {bars[-1].dt}")

    bench_czsc(bars)
    bench_trader(bars)


if __name__ == "__main__":
    main()
