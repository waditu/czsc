"""案例 05：信号系统 —— 配置 / 生成 / 解析

czsc 的信号体系是事件驱动策略的最底层原料：

- 信号函数（``czsc._native.signals.{bar,cxt,tas,vol,pressure,obv,cvolp}``）由 Rust 实现
- 每个信号产出形如 ``"{freq}_{...}_{name}V{ver}"`` 的 key + ``"{v1}_{v2}_{v3}_{score}"`` 的 value
- 通过 ``signals_config`` 配置项调度信号函数 + 在哪个周期上算

本案例演示：

1. 用 ``CzscSignals`` 在多周期上批量计算信号（流式接口，适合实盘）
2. 用 ``generate_czsc_signals`` 批量产出信号 DataFrame（研究/特征工程）
3. 用 ``get_signals_config`` / ``get_signals_freqs`` 反推配置 + 涉及周期

可用信号清单：``czsc._native.signals.bar.list_signal_names()``
对应模板：``czsc._native.signals.bar.get_signal_template(name)``

运行：
    uv run python docs/examples/05_signals.py
"""

from __future__ import annotations

from czsc import (
    BarGenerator,
    CzscSignals,
    Freq,
    format_standard_kline,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
)
from czsc.mock import generate_symbol_kines

# 信号配置：name 是 Rust 端注册名（不带 ``czsc.signals.`` 前缀，版本号大写 V）
# 模板可通过 czsc._native.signals.cxt.get_signal_template(name) 查询
SIGNALS_CONFIG = [
    # 笔的表里关系（30 分钟 / 日线 各算一份）
    {"name": "cxt_bi_status_V230101", "freq": "30分钟"},
    {"name": "cxt_bi_status_V230101", "freq": "日线"},
    # 日线 5 日均线分类
    {"name": "tas_ma_base_V221101", "freq": "日线", "di": 1, "timeperiod": 5, "ma_type": "SMA"},
    # 30 分钟涨跌停
    {"name": "bar_zdt_V230331", "freq": "30分钟", "di": 1},
]


def demo_czsc_signals(bars: list) -> None:
    """方式 A：流式信号计算（适合实盘/回放，逐根 K 线更新）。

    关键点：CzscSignals 是事件驱动的——构造时传入空的 BarGenerator，
    然后逐根调用 ``update_signals(bar)``，内部会先更新 bg 再计算信号。
    """
    bg = BarGenerator(base_freq="30分钟", freqs=["30分钟", "日线"], max_count=5000)
    cs = CzscSignals(bg, signals_config=SIGNALS_CONFIG)
    for bar in bars:
        cs.update_signals(bar)

    # cs.s 同时包含 dt/symbol 等元信息和形如 "k1_k2_k3" 的真信号
    sig_items = {k: v for k, v in cs.s.items() if len(k.split("_")) == 3}
    print("\n[A. CzscSignals.s 当前信号字典]")
    print(f"  共 {len(sig_items)} 个信号；最新时间 = {cs.end_dt}")
    for k, v in sig_items.items():
        print(f"    {k:<35} = {v}")


def demo_generate_signals(bars: list) -> None:
    """方式 B：批量计算，得到 DataFrame，方便做研究/特征工程。"""
    df = generate_czsc_signals(bars, signals_config=SIGNALS_CONFIG, df=True, sdt="2023-01-01")
    sig_cols = [c for c in df.columns if len(c.split("_")) == 3]
    print(f"\n[B. generate_czsc_signals] DataFrame shape={df.shape}")
    print(f"  信号列共 {len(sig_cols)} 个，举例：")
    for col in sig_cols[:4]:
        uniq = [x for x in df[col].dropna().unique().tolist() if "其他" not in x][:5]
        print(f"    {col}: 取值样本 = {uniq}")
    if sig_cols:
        print("\n  最近 3 行的信号取值：")
        print(df[["dt"] + sig_cols[:2]].tail(3).to_string(index=False))


def demo_signal_parse() -> None:
    """方式 C：从一组"信号字符串"反推配置 + 涉及频率。"""
    target_signals = [
        "30分钟_D1_表里关系V230101_向上_任意_任意_0",
        "日线_D1_表里关系V230101_向上_任意_任意_0",
        "日线_D1SMA#5_分类V221101_多头_任意_任意_0",
        "30分钟_D1_涨跌停V230331_涨停_任意_任意_0",
    ]
    cfgs = get_signals_config(target_signals)
    freqs = get_signals_freqs(target_signals)
    print("\n[C. 反向解析]")
    print(f"  涉及周期 = {freqs}")
    print("  解析出的配置：")
    for cfg in cfgs:
        print(f"    {cfg}")


def main() -> None:
    df = generate_symbol_kines("000001", "30分钟", "20220101", "20240101", seed=42)
    bars = format_standard_kline(df, freq=Freq.F30)
    print(f"[数据] {bars[0].symbol} {bars[0].freq}  共 {len(bars)} 根 K 线")

    demo_czsc_signals(bars)
    demo_generate_signals(bars)
    demo_signal_parse()

    print("\n下一步：把信号组合成事件，再驱动持仓变化 -> 06_event_position.py")


if __name__ == "__main__":
    main()
