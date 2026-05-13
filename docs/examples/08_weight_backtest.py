"""案例 08：WeightBacktest 权重回测

``czsc.WeightBacktest`` 来自硬依赖 ``wbt`` 包，是 czsc 推荐的"持仓权重时序"
回测引擎，支持时序策略（``ts``）与截面策略（``cs``）。

本案例展示：

1. 用 ``czsc.mock.generate_klines_with_weights`` 直接生成回测打样数据
2. 调用 ``WeightBacktest`` 完成回测，查看核心绩效字段
3. 用 ``czsc.utils.plot_*`` 系列函数把结果画成 HTML 报告

权重数据格式约定：``[dt, symbol, weight, price]``，weight ∈ [-1, 1]
（>0 多头权重，<0 空头权重，0 空仓）。

运行：
    uv run python docs/examples/08_weight_backtest.py
    # 产物落在 docs/examples/_output/08_weight_backtest.html （已在 .gitignore 中忽略）
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import czsc
from czsc import WeightBacktest, daily_performance, top_drawdowns
from czsc.mock import generate_klines_with_weights

OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_HTML = OUTPUT_DIR / "08_weight_backtest.html"


def main() -> None:
    # 1) 生成模拟"权重 + 价格" DataFrame（多品种、日内分钟级）
    dfw = generate_klines_with_weights(seed=42)
    dfw = dfw[["dt", "symbol", "weight", "price"]].copy()
    print(f"[数据] shape={dfw.shape}, 品种={dfw['symbol'].nunique()}, "
          f"时间={dfw['dt'].min()} ~ {dfw['dt'].max()}")
    print(dfw.head(3).to_string(index=False))

    # 2) 跑回测
    #    - fee_rate=2 BP（双边手续费）
    #    - weight_type='ts' 表示时序策略；'cs' 是截面
    #    - yearly_days 用 cal_yearly_days 自动推断更稳妥
    yearly_days = czsc.cal_yearly_days(dts=dfw["dt"].unique())
    wb = WeightBacktest(
        data=dfw,
        fee_rate=0.0002,
        digits=2,
        weight_type="ts",
        yearly_days=yearly_days,
    )
    print(f"\n[回测] yearly_days={yearly_days}")
    print("  核心绩效指标：")
    for k, v in wb.stats.items():
        print(f"    {k}: {v}")

    # 3) 看每日收益序列
    #    wb.daily_return 是宽表：第一列是 date，其余是各品种 + total 收益
    daily = wb.daily_return.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date")
    daily.index.name = "dt"
    print(f"\n[日收益] shape={daily.shape}, 列={daily.columns.tolist()}")

    # 4) 用 daily_performance / top_drawdowns 做更精细的指标
    #    注意：daily_performance / top_drawdowns 由 wbt 提供，参数需要 numpy 数组（不是 list）
    if "total" in daily.columns:
        import numpy as np

        print("\n[daily_performance(total)]")
        ret_arr = daily["total"].to_numpy(dtype=np.float64)
        for k, v in daily_performance(ret_arr, yearly_days=yearly_days).items():
            print(f"  {k}: {v}")
        # top_drawdowns 接收 date-indexed pandas Series（不是 numpy 数组）
        print("\n[Top 5 回撤]")
        dd_df = top_drawdowns(daily["total"], top=5)
        print(dd_df.to_string(index=False))

    # 5) 用 czsc.utils 中的绘图函数生成离线 HTML
    from czsc.utils.plotting.backtest import plot_backtest_stats, plot_cumulative_returns

    fig_cum = plot_cumulative_returns(daily, title="WeightBacktest 累计收益")
    fig_stats = plot_backtest_stats(daily, ret_col=daily.columns[0], title="WeightBacktest 综合统计")

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(fig_cum.to_html(include_plotlyjs="cdn", full_html=False))
        f.write("<hr>")
        f.write(fig_stats.to_html(include_plotlyjs=False, full_html=False))
    print(f"\n[输出] HTML 报告已生成: {OUT_HTML}")

    print("\n下一步：")
    print("  - 在 Streamlit 面板里互动地查看本回测 -> 12_streamlit_research.py")


if __name__ == "__main__":
    main()
