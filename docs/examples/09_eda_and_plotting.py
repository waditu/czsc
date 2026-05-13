"""案例 09：探索性分析（EDA）与离线绘图工具

czsc 在 ``czsc.eda`` 与 ``czsc.utils.plotting`` 中提供了一组面向研究员的
工具函数：

- ``mark_cta_periods``：基于历史数据后验地标记"易/难赚钱"时段
- ``mark_volatility``：标记高/低波动率区间，便于切片回测
- ``cal_trade_price``：从 K 线推导次日开盘等交易撮合价
- ``turnover_rate``：根据权重序列计算换手率
- ``cal_yearly_days``：交易日序列推断年化天数
- ``monotonicity``：单调性指标（Spearman）
- ``weights_simple_ensemble``：朴素权重集成

本案例覆盖典型用法，并演示如何用 ``plot_colored_table`` /
``plot_long_short_comparison`` 输出成离线 HTML。

运行：
    uv run python docs/examples/09_eda_and_plotting.py
    # 产物落在 docs/examples/_output/09_eda_and_plotting.html （已在 .gitignore 中忽略）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from czsc import (
    cal_trade_price,
    cal_yearly_days,
    mark_cta_periods,
    mark_volatility,
    monotonicity,
    turnover_rate,
    weights_simple_ensemble,
)
from czsc.mock import generate_klines_with_weights, generate_symbol_kines

OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_HTML = OUTPUT_DIR / "09_eda_and_plotting.html"


def demo_mark_periods() -> None:
    """演示 mark_cta_periods / mark_volatility：在 K 线上打"后验"分类标签。"""
    df = generate_symbol_kines("000001", "日线", "20210101", "20240101", seed=42)
    print(f"\n[mark_cta_periods] 输入 shape={df.shape}")
    out_cta = mark_cta_periods(df.copy(), verbose=False)
    cta_flag_cols = [c for c in out_cta.columns if c.startswith("is_") and "period" in c]
    print(f"  标记列: {cta_flag_cols}")
    for col in cta_flag_cols:
        ratio = out_cta[col].mean()
        print(f"    {col}: {ratio:.3f}")

    print("\n[mark_volatility] kind='ts' (时序波动率)")
    out_vol = mark_volatility(df.copy(), kind="ts")
    vol_flag_cols = [c for c in out_vol.columns if c.startswith("is_") and "volatility" in c]
    for col in vol_flag_cols:
        print(f"    {col}: 占比 = {out_vol[col].mean():.3f}")


def demo_trade_price() -> None:
    """cal_trade_price：构建一张可在回测中复用的交易撮合价表。"""
    df = generate_symbol_kines("000001", "日线", "20230101", "20240101", seed=42)
    df = cal_trade_price(df)
    cols = [c for c in df.columns if "TP_" in c]
    print(f"\n[cal_trade_price] 新增 {len(cols)} 个交易价列：{cols[:6]}")
    print(df.head(3)[["dt", "symbol", "open", "close"] + cols[:3]].to_string(index=False))


def demo_turnover_and_ensemble() -> None:
    """turnover_rate / weights_simple_ensemble：做权重侧的 EDA。"""
    dfw = generate_klines_with_weights(seed=42)
    base_cols = ["dt", "symbol", "weight", "price"]
    dfw = dfw[base_cols].copy()

    # turnover_rate 期望 dfw 至少有 [dt, symbol, weight] 三列
    res = turnover_rate(dfw)
    print("\n[turnover_rate]")
    for k, v in res.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    # 模拟多策略集成：构造两条权重列后用 weights_simple_ensemble 融合
    np.random.seed(0)
    df_multi = dfw[["dt", "symbol", "price"]].copy()
    df_multi["w1"] = np.random.uniform(-1, 1, len(df_multi))
    df_multi["w2"] = np.random.uniform(-1, 1, len(df_multi))
    df_multi = weights_simple_ensemble(df_multi, weight_cols=["w1", "w2"], method="mean")
    print(f"\n[weights_simple_ensemble] mean 集成后：weight 描述")
    print(df_multi["weight"].describe().round(4).to_string())


def demo_misc() -> None:
    print(f"\n[monotonicity] 严格递增 -> {monotonicity(list(range(20))):.3f}")
    print(f"[monotonicity] 严格递减 -> {monotonicity(list(range(20, 0, -1))):.3f}")
    print(f"[monotonicity] 抖动序列 -> {monotonicity([1, 3, 2, 4, 5, 4, 6]):.3f}")

    dts = pd.date_range("2022-01-01", "2023-12-31", freq="B")
    print(f"\n[cal_yearly_days] 252 工作日序列 -> {cal_yearly_days(dts.tolist())}")


def demo_plotting() -> None:
    """用 czsc.utils.plotting.* 把 stats DataFrame 画成离线表格 HTML。"""
    from czsc.utils.plotting.backtest import plot_colored_table, plot_long_short_comparison

    # 1) plot_colored_table —— 策略 × 指标 的彩色表格
    stats = pd.DataFrame(
        {
            "年化收益率": [0.18, 0.22, 0.31, -0.05],
            "夏普率":    [1.2, 1.5, 2.1, -0.3],
            "最大回撤":  [-0.12, -0.08, -0.15, -0.25],
            "胜率":      [0.55, 0.60, 0.62, 0.48],
        },
        index=["策略A", "策略B", "策略C", "策略D"],
    )
    table_fig = plot_colored_table(stats, title="策略对比表")

    # 2) plot_long_short_comparison —— 同时需要 dailys_pivot 和 stats_df
    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    np.random.seed(42)
    dret = pd.DataFrame(
        {
            "long":  np.random.normal(0.0008, 0.012, 300),
            "short": np.random.normal(-0.0003, 0.011, 300),
            "total": np.random.normal(0.0005, 0.010, 300),
        },
        index=dates,
    )
    ls_stats = pd.DataFrame(
        {
            "年化收益率": [0.18, -0.05, 0.13],
            "夏普率":    [1.4, -0.2, 1.0],
            "最大回撤":  [-0.10, -0.15, -0.08],
        },
        index=["long", "short", "total"],
    )
    ls_fig = plot_long_short_comparison(dret, ls_stats, title="多空对比演示")

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write("<h2>plot_colored_table 演示</h2>")
        f.write(table_fig.to_html(include_plotlyjs="cdn", full_html=False))
        f.write("<hr><h2>plot_long_short_comparison 演示</h2>")
        f.write(ls_fig.to_html(include_plotlyjs=False, full_html=False))
    print(f"\n[输出] {OUT_HTML} 已生成")


def main() -> None:
    demo_mark_periods()
    demo_trade_price()
    demo_turnover_and_ensemble()
    demo_misc()
    demo_plotting()


if __name__ == "__main__":
    main()
