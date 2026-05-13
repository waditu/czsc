"""案例 11：Streamlit UI —— 用 CzscTrader 看多周期交易决策

本案例完整跑通"事件驱动 -> 多级别决策"的可视化链路：

1. 用 ``BarGenerator`` 维护多周期 K 线
2. 用两个 ``Position``（30 分钟 / 60 分钟）驱动 ``CzscTrader``
3. 在 Streamlit 中渲染：
   - 每个周期的 K 线 + 分型 + 笔（``KlineChart``）
   - 基础周期叠加每个 Position 的开仓/平仓标记
   - 当前最新信号字典 + 各 Position 的最新仓位

启动：
    streamlit run docs/examples/11_streamlit_trader.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import czsc
from czsc import (
    BarGenerator,
    CzscTrader,
    Event,
    KlineChart,
    Position,
    format_standard_kline,
    freqs_sorted,
    get_signals_config,
)
from czsc.mock import generate_symbol_kines


def build_positions(symbol: str) -> list[Position]:
    """构造两个简单的多空 Position（30 分钟 / 60 分钟）。"""

    def long_short(base_freq: str, name: str) -> Position:
        opens = [
            Event.load(
                {
                    "operate": "开多",
                    "signals_all": [f"{base_freq}_D1_表里关系V230101_向上_任意_任意_0"],
                }
            ),
            Event.load(
                {
                    "operate": "开空",
                    "signals_all": [f"{base_freq}_D1_表里关系V230101_向下_任意_任意_0"],
                }
            ),
        ]
        return Position(
            name=name, symbol=symbol, opens=opens, exits=[],
            interval=3600 * 4, timeout=16 * 30, stop_loss=500,
        )

    return [long_short("30分钟", "30分钟非多即空"), long_short("60分钟", "60分钟非多即空")]


@st.cache_resource(show_spinner="正在准备 CzscTrader…")
def build_trader(symbol: str, sdt: str, edt: str, seed: int) -> CzscTrader:
    df = generate_symbol_kines(symbol, "30分钟", sdt, edt, seed=seed)
    bars = format_standard_kline(df, freq="30分钟")
    bg = BarGenerator(base_freq="30分钟", freqs=["30分钟", "60分钟", "日线"], max_count=5000)

    positions = build_positions(symbol)
    sig_keys: list[str] = []
    for pos in positions:
        sig_keys.extend(pos.unique_signals)
    signals_config = get_signals_config(sig_keys)

    trader = CzscTrader(bg, positions=positions, signals_config=signals_config)
    for bar in bars:
        trader.update(bar)
    return trader


def render_freq_chart(trader: CzscTrader, freq: str, max_k: int) -> None:
    """单个周期：K 线 + 均线 + 成交量 + MACD + 分型 + 笔，
    并在基础周期上叠加各 Position 的开/平仓标记。"""
    from czsc.utils.ta import MACD

    c = trader.kas[freq]
    df = c.bars_raw_df.tail(max_k).reset_index(drop=True).copy()
    df["DIFF"], df["DEA"], df["MACD"] = MACD(df["close"])
    sdt = df["dt"].iloc[0]

    chart = KlineChart(n_rows=3, row_heights=(0.55, 0.2, 0.25), title="", height=820)
    chart.add_kline(df, name="")
    chart.add_sma(df, ma_seq=(5, 20, 60), row=1, line_width=1, visible=False)
    chart.add_vol(df, row=2)
    chart.add_macd(df, row=3)

    # 分型 + 笔
    if c.fx_list:
        fx_df = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in c.fx_list])
        fx_df = fx_df[fx_df["dt"] >= sdt]
        chart.add_scatter_indicator(
            fx_df["dt"], fx_df["fx"], name="分型", row=1, mode="lines",
            line_dash="dot", line_width=1, marker_color="white",
        )
    if c.bi_list:
        bi_pts = (
            [{"dt": x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list]
            + [{"dt": c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
        )
        bi_df = pd.DataFrame(bi_pts)
        bi_df = bi_df[bi_df["dt"] >= sdt]
        chart.add_scatter_indicator(bi_df["dt"], bi_df["bi"], name="笔", row=1, line_width=1.6)

    # 仅在基础周期上叠加开/平仓标记
    if freq == trader.base_freq:
        open_op_codes = {"LO", "SO"}
        for pos in trader.positions:
            if not pos.operates:
                continue
            ops_df = pd.DataFrame(pos.operates)
            # operates 的 dt 是 unix 时间戳（float 秒），统一转 datetime 后再过滤
            ops_df["dt"] = pd.to_datetime(ops_df["dt"], unit="s")
            ops_df = ops_df[ops_df["dt"] >= pd.Timestamp(sdt)]
            if ops_df.empty:
                continue
            ops_df["tag"] = ops_df["op"].apply(
                lambda x: "triangle-up" if str(x) in open_op_codes else "triangle-down"
            )
            ops_df["color"] = ops_df["op"].apply(
                lambda x: "red" if str(x) in open_op_codes else "white"
            )
            chart.add_scatter_indicator(
                ops_df["dt"], ops_df["price"], name=pos.name,
                text=ops_df.get("op_desc", ops_df["op"].astype(str)),
                row=1, mode="markers", marker_size=14,
                marker_symbol=ops_df["tag"], marker_color=ops_df["color"],
                visible=False, hover_template="%{x}<br>%{y:.2f}<br>%{text}<extra></extra>",
            )

    st.plotly_chart(chart.fig, use_container_width=True, config={"scrollZoom": True})


def main() -> None:
    st.set_page_config(page_title="czsc 交易决策面板", layout="wide")
    st.title("🎯 CzscTrader 多级别交易决策面板")
    st.caption(f"czsc=={czsc.__version__}  |  KlineChart 自定义渲染 + Position 信号叠加")

    with st.sidebar:
        st.header("参数")
        symbol = st.text_input("品种代码", value="000001")
        sdt = st.text_input("起始日期 (YYYYMMDD)", value="20220101")
        edt = st.text_input("结束日期 (YYYYMMDD)", value="20240601")
        seed = st.number_input("mock 随机种子", value=42)
        max_k = st.slider("每个周期展示多少根 K 线", 100, 800, 300, step=50)

    trader = build_trader(symbol, sdt, edt, int(seed))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("品种", trader.symbol)
    col2.metric("基础周期", trader.base_freq)
    col3.metric("最新时间", str(trader.end_dt))
    col4.metric("策略数", len(trader.positions))

    # 多周期标签页：仅展示 trader.kas 中实际维护的周期
    sorted_freq = freqs_sorted(list(trader.kas.keys()))
    tabs = st.tabs(sorted_freq + ["策略详情"])
    for tab, freq in zip(tabs[:-1], sorted_freq, strict=False):
        with tab:
            render_freq_chart(trader, freq, max_k=max_k)

    with tabs[-1]:
        st.subheader("最新信号字典")
        sig_dict = {k: v for k, v in trader.s.items() if len(k.split("_")) == 3}
        st.json(sig_dict)
        for pos in trader.positions:
            st.divider()
            st.markdown(f"**{pos.name}**  当前仓位 = `{pos.pos}`")
            st.json(pos.dump(with_data=False))


if __name__ == "__main__":
    main()
