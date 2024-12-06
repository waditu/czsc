import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


def show_df_describe(df: pd.DataFrame):
    """展示 DataFrame 的描述性统计信息

    :param df: pd.DataFrame，必须是 df.describe() 的结果
    """
    quantiles = [x for x in df.columns if "%" in x]
    df = df.style.background_gradient(cmap="RdYlGn_r", axis=None, subset=["mean"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["std"])
    df = df.background_gradient(cmap="RdYlGn_r", axis=None, subset=["max", "min"] + quantiles)

    format_dict = {
        "count": "{:.0f}",
        "mean": "{:.4f}",
        "std": "{:.4f}",
        "min": "{:.4f}",
        "max": "{:.4f}",
    }
    for q in quantiles:
        format_dict[q] = "{:.4f}"

    df = df.format(format_dict)
    st.dataframe(df, use_container_width=True)


def show_date_effect(df: pd.DataFrame, ret_col: str, **kwargs):
    """分析日收益数据的日历效应

    :param df: pd.DataFrame, 包含日期的日收益数据
    :param ret_col: str, 收益列名称
    :param kwargs: dict, 其他参数

        - show_weekday: bool, 是否展示星期效应，默认为 True
        - show_month: bool, 是否展示月份效应，默认为 True
        - percentiles: list, 分位数，默认为 [0.1, 0.25, 0.5, 0.75, 0.9]

    """
    show_weekday = kwargs.get("show_weekday", True)
    show_month = kwargs.get("show_month", True)
    percentiles = kwargs.get("percentiles", [0.1, 0.25, 0.5, 0.75, 0.9])

    assert ret_col in df.columns, f"ret_col 必须是 {df.columns} 中的一个"
    assert show_month or show_weekday, "show_month 和 show_weekday 不能同时为 False"

    if not df.index.dtype == "datetime64[ns]":
        df["dt"] = pd.to_datetime(df["dt"])
        df.set_index("dt", inplace=True)

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    df = df.copy()

    st.write(
        f"交易区间 {df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')}；总天数：{len(df)}"
    )

    if show_weekday:
        st.write("##### 星期效应")
        df["weekday"] = df.index.weekday
        sorted_weekday = sorted(df["weekday"].unique().tolist())
        weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        df["weekday"] = df["weekday"].map(weekday_map)
        sorted_rows = [weekday_map[i] for i in sorted_weekday]

        weekday_effect = df.groupby("weekday")[ret_col].describe(percentiles=percentiles)
        weekday_effect = weekday_effect.loc[sorted_rows]
        show_df_describe(weekday_effect)

    if show_month:
        st.write("##### 月份效应")
        df["month"] = df.index.month
        month_map = {i: f"{i}月" for i in range(1, 13)}
        sorted_month = sorted(df["month"].unique().tolist())
        sorted_rows = [month_map[i] for i in sorted_month]

        df["month"] = df["month"].map(month_map)
        month_effect = df.groupby("month")[ret_col].describe(percentiles=percentiles)
        month_effect = month_effect.loc[sorted_rows]
        show_df_describe(month_effect)

    st.caption("数据说明：count 为样本数量，mean 为均值，std 为标准差，min 为最小值，n% 为分位数，max 为最大值")


def main():
    df = pd.read_feather(r"A:\量化研究\BTC策略1H持仓权重和日收益241201\BTC_2H_001-daily_return.feather")
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= pd.to_datetime("2021-01-01")].copy()
    df.set_index("date", inplace=True)
    df["total"] = df.mean(axis=1) * 10000

    show_date_effect(df, ret_col="total")


if __name__ == "__main__":
    main()
