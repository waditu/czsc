import pandas as pd

from czsc.utils.plotting.backtest import plot_long_short_comparison


def test_plot_long_short_comparison_uses_separate_legends():
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    dailys_pivot = pd.DataFrame(
        {
            "策略多头": [0.01, -0.005, 0.008, 0.003, -0.002],
            "策略空头": [-0.004, 0.006, -0.003, 0.002, 0.001],
            "基准等权": [0.002, -0.001, 0.003, 0.001, 0.0],
        },
        index=dates,
    )
    stats_df = pd.DataFrame(
        {
            "策略名称": ["策略多头", "策略空头", "基准等权"],
            "年化": [0.12, 0.06, 0.08],
            "夏普": [1.2, 0.9, 1.0],
            "卡玛": [1.5, 0.8, 1.1],
            "最大回撤": [0.05, 0.08, 0.04],
            "年化波动率": [0.18, 0.16, 0.15],
            "交易胜率": [0.58, 0.52, 0.55],
            "单笔收益": [12.0, 6.0, 8.0],
            "持仓K线数": [120, 118, 121],
            "多头占比": [1.0, 0.0, 0.5],
            "空头占比": [0.0, 1.0, 0.5],
        }
    )

    fig = plot_long_short_comparison(dailys_pivot, stats_df, to_html=False)

    top_trace_count = len(dailys_pivot.columns)
    adjusted_trace_count = len(dailys_pivot.columns) + 1

    top_traces = fig.data[:top_trace_count]
    adjusted_traces = fig.data[top_trace_count : top_trace_count + adjusted_trace_count]

    assert {trace.legend for trace in top_traces} == {"legend"}
    assert {trace.legend for trace in adjusted_traces} == {"legend2"}
    assert fig.layout.legend.title.text == "累计收益曲线"
    assert fig.layout.legend2.title.text == "波动率调整后收益"
