"""案例 10：Streamlit UI —— 缠论 K 线交互式看图

本案例演示如何在 Streamlit 中"打开浏览器即可看缠论结构图"。
界面提供：

- 品种 / 周期 / 时间区间 选择
- 缠论分型、笔的可视化叠加
- 均线 / 成交量 / MACD 多子图布局

启动方式：
    streamlit run docs/examples/10_streamlit_kline.py

依赖：streamlit、plotly（czsc 的 svc 模块默认会装上）。
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import czsc
from czsc import CZSC, Freq, KlineChart, format_standard_kline
from czsc.mock import generate_symbol_kines

# 仅在分钟级别上做演示，避免日线/周线在 mock 数据上展示效果不佳
FREQ_MAP = {
    "30分钟": Freq.F30,
    "60分钟": Freq.F60,
    "日线": Freq.D,
}


def render_chart(c: CZSC, max_k: int) -> None:
    """渲染缠论 K 线图：3 行子图（K 线 / 成交量 / MACD），叠加分型/笔。"""
    # 用 bars_raw_df 拿到规范化的 DataFrame，避免 pd.DataFrame(RawBar 列表) 的兼容性问题
    df = c.bars_raw_df.tail(max_k).reset_index(drop=True).copy()

    # add_macd 在缺少 DIFF/DEA/MACD 列时会自动计算
    chart = KlineChart(n_rows=3, row_heights=(0.6, 0.2, 0.2), title="", height=900)
    chart.add_kline(df, name="")
    chart.add_sma(df, ma_seq=(5, 20, 60), row=1, line_width=1, visible=False)
    chart.add_vol(df, row=2)
    chart.add_macd(df, row=3)

    if c.fx_list:
        fx = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in c.fx_list])
        fx = fx[fx["dt"] >= df["dt"].iloc[0]]
        chart.add_scatter_indicator(
            fx["dt"], fx["fx"], name="分型", row=1, mode="lines",
            line_dash="dot", line_width=1, marker_color="white",
        )
    if c.bi_list:
        bi_pts = (
            [{"dt": x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list]
            + [{"dt": c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
        )
        bi = pd.DataFrame(bi_pts)
        bi = bi[bi["dt"] >= df["dt"].iloc[0]]
        chart.add_scatter_indicator(bi["dt"], bi["bi"], name="笔", row=1, line_width=1.6)

    st.plotly_chart(chart.fig, use_container_width=True, config={"scrollZoom": True})


def main() -> None:
    st.set_page_config(page_title="czsc 缠论看图", layout="wide")
    st.title("📈 czsc 缠论 K 线交互看图")
    st.caption(
        f"czsc=={czsc.__version__}  |  数据来自 czsc.mock，可在侧边栏选择品种/周期/时间窗口"
    )

    with st.sidebar:
        st.header("参数")
        symbol = st.text_input("品种代码", value="000001")
        freq_label = st.selectbox("K 线周期", list(FREQ_MAP.keys()), index=0)
        sdt = st.date_input("起始日期", value=pd.to_datetime("2023-01-01")).strftime("%Y%m%d")
        edt = st.date_input("结束日期", value=pd.to_datetime("2024-06-01")).strftime("%Y%m%d")
        max_k = st.slider("展示最近多少根 K 线", 100, 1000, 300, step=50)
        seed = st.number_input("mock 随机种子", value=42)

    df = generate_symbol_kines(symbol, freq_label, sdt, edt, seed=int(seed))
    if df.empty:
        st.error("数据为空，请调整时间区间")
        return

    bars = format_standard_kline(df, freq=FREQ_MAP[freq_label])
    c = CZSC(bars)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("K 线数", len(c.bars_raw))
    col2.metric("分型数", len(c.fx_list))
    col3.metric("完成笔数", len(c.bi_list))
    last_dir = c.bi_list[-1].direction if c.bi_list else "—"
    col4.metric("最后笔方向", str(last_dir))

    render_chart(c, max_k=max_k)

    with st.expander("最近 5 笔详情", expanded=False):
        rows = []
        for bi in c.bi_list[-5:]:
            rows.append(
                {
                    "方向": str(bi.direction),
                    "起点时间": bi.sdt,
                    "终点时间": bi.edt,
                    "高": bi.high,
                    "低": bi.low,
                    "长度": bi.length,
                    "力度": round(bi.power, 3),
                    "SNR": round(bi.SNR, 3),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


if __name__ == "__main__":
    main()
