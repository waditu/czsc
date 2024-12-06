import inspect
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


def ARB001(df: pd.DataFrame, **kwargs):
    """期货套利因子样例

    ARB 是 arbitrage 的缩写，意为套利。套利因子是指用于判断套利机会的指标，通常是两个或多个标的之间的价格差异。

    动态监控豆油/棕榈油的价格比值的阈值；
    当比值 >1.2, 且比值是下降趋势，即比值的当前值与比值序列的MA20 形成一个死叉时，做多豆油，做空棕榈油；比值到1.15左右平仓

    :param df: pd.DataFrame, 包含 DLy9001 和 DLp9001 两个品种的行情数据；至少包含以下列：dt, symbol, close;
        数据样例：

        ===================  ========  =======
        dt                   symbol      close
        ===================  ========  =======
        2017-01-03 00:00:00  DLy9001   5975.07
        2017-01-04 00:00:00  DLy9001   5914.89
        2017-01-05 00:00:00  DLy9001   5909.73
        2017-01-03 00:00:00  DLp9001   5975.07
        2017-01-04 00:00:00  DLp9001   5914.89
        2017-01-05 00:00:00  DLp9001   5909.73
        ===================  ========  =======

    :param kwargs: dict, 其他参数

        - window: int, 默认20, 计算均线的窗口
        - tag: str, 默认"DEFAULT", 因子标签

    """
    window = kwargs.get("window", 20)
    tag = kwargs.get("tag", "DEFAULT")

    # 获取函数名构建因子列名
    factor_name = inspect.currentframe().f_code.co_name
    factor_col = f"F#{factor_name}#{tag}"

    # 计算套利因子
    dfp = pd.pivot_table(df, index="dt", columns="symbol", values="close")
    dfp["ratio"] = dfp["DLy9001"] / dfp["DLp9001"]
    dfp["ratio_ma20"] = dfp["ratio"].rolling(window).mean()
    dfp["ratio_diff"] = dfp["ratio"] - dfp["ratio_ma20"]

    # 构建套利组合
    dfp["y_weight"] = 0
    dfp["p_weight"] = 0
    for i, row in dfp.iterrows():
        if row["ratio"] > 1.2 and row["ratio_diff"] < 0:
            dfp.loc[i, "y_weight"] = 1
            dfp.loc[i, "p_weight"] = -1
        if row["ratio"] < 1.15:
            dfp.loc[i, "y_weight"] = 0
            dfp.loc[i, "p_weight"] = 0

    # 合并到原始数据
    df.loc[df["symbol"] == "DLy9001", factor_col] = df.loc[df["symbol"] == "DLy9001", "dt"].map(dfp["y_weight"])
    df.loc[df["symbol"] == "DLp9001", factor_col] = df.loc[df["symbol"] == "DLp9001", "dt"].map(dfp["p_weight"])
    return df


def main():
    import czsc
    from czsc.connectors import cooperation as coo

    # 构建策略
    df1 = coo.get_raw_bars(symbol="DLy9001", freq="日线", sdt="20170101", edt="20221231", raw_bars=False, fq="后复权")
    df2 = coo.get_raw_bars(symbol="DLp9001", freq="日线", sdt="20170101", edt="20221231", raw_bars=False, fq="后复权")
    df = pd.concat([df1, df2], axis=0)
    df = ARB001(df)
    factor = [x for x in df.columns if x.startswith("F#ARB001")][0]
    df["weight"] = df[factor].fillna(0)
    df["price"] = df["close"]

    dfw = df[["dt", "symbol", "price", "weight"]].copy()

    # 执行回测
    st.title("期货套利研究")
    czsc.show_weight_backtest(
        dfw, fee_rate=0.0002, show_drawdowns=True, show_yearly_stats=True, show_monthly_return=True
    )


if __name__ == "__main__":
    main()
    # 启动说明：streamlit run examples/期货套利因子样例.py --theme.base=dark
