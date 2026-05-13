"""案例 03：K 线 + 分型 + 笔 的可视化（离线 HTML 图）

使用 ``czsc.utils.plotting.kline`` 中的 ``KlineChart`` / ``plot_czsc_chart``
直接把 ``CZSC`` 分析对象渲染为带分型、笔、均线、成交量、MACD 的交互式
Plotly 图，并保存为 HTML。

适用场景：
- 离线生成研究报告中的图表
- 不依赖 Streamlit 的快速可视化
- 自定义叠加自己的指标/标记

运行：
    uv run python docs/examples/03_kline_chart.py
    # 产物落在 docs/examples/_output/03_kline_chart.html （已在 .gitignore 中忽略）
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from czsc import CZSC, Freq, KlineChart, format_standard_kline, plot_czsc_chart
from czsc.mock import generate_symbol_kines

# 所有案例统一把产物落到 docs/examples/_output/（已在仓库 .gitignore 中忽略）
OUTPUT_DIR = Path(__file__).resolve().parent / "_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_HTML = OUTPUT_DIR / "03_kline_chart.html"


def chart_with_plot_czsc_chart(c: CZSC) -> str:
    """方式 A：``plot_czsc_chart`` —— 一行直出 KlineChart，再转 HTML 字符串。"""
    # plot_czsc_chart 返回 KlineChart 实例（包装 plotly Figure），不是字符串
    chart = plot_czsc_chart(c, height=900)
    return chart.fig.to_html(include_plotlyjs="cdn", full_html=True)


def chart_with_kline_chart_class(c: CZSC) -> str:
    """方式 B：用 ``KlineChart`` 自定义子图布局，叠加分型/笔/均线/成交量/MACD。"""
    from czsc.utils.ta import MACD  # czsc 仪表盘场景的特殊 MACD 约定

    # CZSC.bars_raw_df 已经是规范化的 DataFrame，避免直接 pd.DataFrame(RawBar 列表) 的兼容性问题
    df = c.bars_raw_df.tail(300).reset_index(drop=True).copy()
    df["DIFF"], df["DEA"], df["MACD"] = MACD(df["close"])

    # 3 行子图：K 线 / 成交量 / MACD
    chart = KlineChart(n_rows=3, row_heights=(0.6, 0.2, 0.2), title="自定义 KlineChart 演示")
    chart.add_kline(df, name="")
    chart.add_sma(df, ma_seq=(5, 20, 60), row=1, line_width=1, visible=False)
    chart.add_vol(df, row=2)
    chart.add_macd(df, row=3)

    # 叠加分型与笔
    fx_df = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in c.fx_list])
    fx_df = fx_df[fx_df["dt"] >= df["dt"].iloc[0]]
    if not fx_df.empty:
        chart.add_scatter_indicator(
            fx_df["dt"], fx_df["fx"], name="分型", row=1, mode="lines",
            line_dash="dot", line_width=1, marker_color="white",
        )
    if c.bi_list:
        bi_points = (
            [{"dt": x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list]
            + [{"dt": c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
        )
        bi_df = pd.DataFrame(bi_points)
        bi_df = bi_df[bi_df["dt"] >= df["dt"].iloc[0]]
        chart.add_scatter_indicator(bi_df["dt"], bi_df["bi"], name="笔", row=1, line_width=1.6)

    return chart.fig.to_html(include_plotlyjs="cdn", full_html=True)


def main() -> None:
    df = generate_symbol_kines("000001", "30分钟", "20230101", "20240301", seed=42)
    c = CZSC(format_standard_kline(df, freq=Freq.F30))
    print(f"[数据] {c.symbol} {c.freq}  K 线={len(c.bars_raw)} 笔={len(c.bi_list)}")

    # 方式 A：直接调用 plot_czsc_chart（最简）
    html_a = chart_with_plot_czsc_chart(c)

    # 方式 B：手工构造 KlineChart（最灵活）
    html_b = chart_with_kline_chart_class(c)

    # 把两份图拼到一个 HTML 文件里输出
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write("<h2>方式 A：plot_czsc_chart 一行直出</h2>\n")
        f.write(html_a)
        f.write("<hr><h2>方式 B：KlineChart 自定义</h2>\n")
        f.write(html_b)

    print(f"[输出] 已生成 {OUT_HTML}，可在浏览器中打开查看")


if __name__ == "__main__":
    main()
