"""案例 12：Streamlit UI —— 一站式量化研究面板

把 ``czsc`` 的回测引擎与 ``czsc.utils.plotting`` 中的绘图函数组合成
一个完整研究面板，覆盖：

- **回测**：``WeightBacktest`` 直接对权重数据回测，配合 ``plot_backtest_stats``
- **收益分析**：``plot_cumulative_returns`` / ``plot_drawdown_analysis`` /
  ``plot_monthly_heatmap`` / ``plot_daily_return_distribution``
- **相关性**：``czsc.svc.show_correlation`` 与 ``show_ts_rolling_corr``
  （这两个组件不依赖 WeightBacktest，可放心使用）
- **因子分析**：``czsc.svc.show_factor_layering`` / ``show_feature_returns``
- **统计分析**：``czsc.svc.show_yearly_stats`` / ``show_describe``

> 注：``czsc.svc.show_weight_backtest`` 当前在内部使用了旧版
> ``WeightBacktest(dfw=…)`` 关键字，与最新的 wbt 不兼容；
> 因此本面板"回测"页面**直接构造 WeightBacktest**，绕开此问题。

启动：
    streamlit run docs/examples/12_streamlit_research.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import czsc
from czsc import WeightBacktest, svc
from czsc.mock import generate_klines_with_weights
from czsc.utils.plotting.backtest import (
    plot_backtest_stats,
    plot_cumulative_returns,
    plot_daily_return_distribution,
    plot_drawdown_analysis,
    plot_monthly_heatmap,
)


@st.cache_data(show_spinner="生成模拟权重数据…")
def make_weight_df(seed: int) -> pd.DataFrame:
    df = generate_klines_with_weights(seed=seed)
    return df[["dt", "symbol", "weight", "price"]].copy()


@st.cache_data
def make_daily_returns(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=600, freq="B")
    cols = {f"strategy_{x}": rng.normal(0.0008, 0.012, 600) for x in "ABCDE"}
    df = pd.DataFrame(cols, index=dates)
    df.index.name = "dt"
    return df


@st.cache_data
def make_factor_df(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 6000
    factor = rng.normal(0, 1, n)
    noise = rng.normal(0, 1, n)
    returns = 0.3 * factor + 0.05 * noise
    return pd.DataFrame(
        {
            "dt": pd.date_range("2022-01-01", periods=n, freq="h"),
            "symbol": rng.choice(["A", "B", "C", "D"], size=n),
            "factor_main": factor,
            "factor_noise": noise,
            "returns": returns,
        }
    )


@st.cache_resource(show_spinner="跑 WeightBacktest…")
def run_weight_backtest(seed: int, fee_bp: int) -> WeightBacktest:
    dfw = make_weight_df(seed)
    yearly_days = czsc.cal_yearly_days(dts=dfw["dt"].unique())
    return WeightBacktest(
        data=dfw,
        fee_rate=fee_bp / 10000,
        digits=2,
        weight_type="ts",
        yearly_days=yearly_days,
    )


def page_backtest() -> None:
    st.subheader("权重回测（直接调用 WeightBacktest，绕过 svc 旧 API）")
    seed = int(st.number_input("mock seed", value=42, key="bt_seed"))
    fee = int(st.slider("单边手续费 (BP)", 0, 20, 2))
    wb = run_weight_backtest(seed, fee)

    cols = st.columns(5)
    for col, (label, key) in zip(cols, [
        ("年化收益", "年化收益"),
        ("夏普比率", "夏普比率"),
        ("最大回撤", "最大回撤"),
        ("年胜率", "年胜率"),
        ("交易胜率", "交易胜率"),
    ], strict=False):
        v = wb.stats.get(key)
        col.metric(label, f"{v:.2%}" if isinstance(v, float) and abs(v) < 5 else str(v))

    daily = wb.daily_return.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date")

    st.markdown("**累计收益（含年度分隔线）**")
    st.plotly_chart(plot_cumulative_returns(daily), use_container_width=True)

    st.markdown("**综合统计：回撤 + 月度热力图 + 日收益分布**")
    st.plotly_chart(plot_backtest_stats(daily, ret_col="total"), use_container_width=True)


def page_returns() -> None:
    st.subheader("日收益分析")
    df = make_daily_returns()
    st.plotly_chart(plot_cumulative_returns(df, title="多策略累计收益"), use_container_width=True)
    ret_col = st.selectbox("查看哪条日收益的细节", df.columns.tolist(), index=0)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(plot_drawdown_analysis(df, ret_col=ret_col), use_container_width=True)
    with c2:
        st.plotly_chart(plot_daily_return_distribution(df, ret_col=ret_col), use_container_width=True)
    st.plotly_chart(plot_monthly_heatmap(df, ret_col=ret_col), use_container_width=True)


def page_correlation() -> None:
    st.subheader("相关性分析")
    df = make_daily_returns()
    svc.show_correlation(df, fig_title="策略间相关性矩阵")
    cols = df.columns.tolist()
    if len(cols) >= 2:
        x = st.selectbox("x", cols, index=0)
        y = st.selectbox("y", cols, index=1)
        svc.show_ts_rolling_corr(df, col1=x, col2=y, window=60)


def page_factor() -> None:
    st.subheader("因子分析")
    df = make_factor_df()
    feature_cols = [c for c in df.columns if c.startswith("factor_")]
    svc.show_feature_returns(df, features=feature_cols, ret_col="returns")

    # 自实现的简易分层（绕过 svc.show_factor_layering 内部对 wbt 旧 API 的依赖）
    factor_choice = st.selectbox("分层因子", feature_cols, index=0)
    n = st.slider("层数", 3, 10, 5)
    data = df[[factor_choice, "returns"]].dropna().copy()
    data["layer"] = pd.qcut(
        data[factor_choice], q=n,
        labels=[f"第{i + 1}层" for i in range(n)], duplicates="drop",
    )
    layer_mean = data.groupby("layer", observed=True)["returns"].mean()
    layer_std = data.groupby("layer", observed=True)["returns"].std()
    layer_count = data.groupby("layer", observed=True)["returns"].size()
    layer_summary = pd.DataFrame(
        {"层均值收益": layer_mean, "层收益波动": layer_std, "样本数": layer_count}
    ).round(6)
    st.dataframe(layer_summary, use_container_width=True)
    st.bar_chart(layer_mean)


def page_statistics() -> None:
    st.subheader("统计分析")
    df = make_daily_returns()
    yearly_days = 252
    # 用 numpy 数组喂给 daily_performance，按年聚合得到年度绩效
    rows = []
    for year, sub in df.groupby(df.index.year):
        for col in df.columns:
            arr = sub[col].to_numpy(dtype=np.float64)
            if arr.size < 30:
                continue
            row = czsc.daily_performance(arr, yearly_days=yearly_days)
            row["年度"] = year
            row["策略"] = col
            rows.append(row)
    yearly_df = pd.DataFrame(rows).set_index(["年度", "策略"])
    st.markdown("**年度绩效汇总**")
    st.dataframe(yearly_df.round(4), use_container_width=True)

    svc.show_describe(df, sub_title="日收益描述性统计")
    # show_normality_check 接收单条 Series（不是 DataFrame）
    target = st.selectbox("正态性检验目标列", df.columns.tolist(), index=0)
    svc.show_normality_check(df[target])


def main() -> None:
    st.set_page_config(page_title="czsc 量化研究面板", layout="wide")
    st.title("🧪 czsc 量化研究综合面板")
    st.caption(
        f"czsc=={czsc.__version__}  |  组件来自 czsc.svc + czsc.utils.plotting"
    )

    pages = {
        "回测":    page_backtest,
        "收益":    page_returns,
        "相关性":  page_correlation,
        "因子":    page_factor,
        "统计":    page_statistics,
    }
    choice = st.sidebar.radio("选择面板", list(pages.keys()))
    pages[choice]()


if __name__ == "__main__":
    main()
