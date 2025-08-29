
import czsc
import streamlit as st
import pandas as pd


st.set_page_config(page_title="策略回测", layout="wide")


def show_yearly_backtest(df: pd.DataFrame, **kwargs):
    """
    按照年份进行回测
    """
    df = df[['dt', 'symbol', 'weight', 'price']].copy()
    df['year'] = df['dt'].dt.year
    wbs = {}
    for year, dfy in df.groupby('year'):
        dfy = dfy.copy().sort_values(['symbol', 'dt']).reset_index(drop=True)
        wbs[f"{year}年"] = czsc.WeightBacktest(dfy, **kwargs)

    czsc.svc.show_multi_backtest(wbs)
    return wbs

def show_symbol_backtest(df: pd.DataFrame, **kwargs):
    """
    按照交易标的进行回测
    """
    df = df[['dt', 'symbol', 'weight', 'price']].copy()

    wbs = {}
    for symbol, dfs in df.groupby('symbol'):
        dfs = dfs.copy().sort_values(['dt']).reset_index(drop=True)
        wbs[symbol] = czsc.WeightBacktest(dfs, **kwargs)

    czsc.svc.show_multi_backtest(wbs)
    return wbs


def show_long_short_backtest(df: pd.DataFrame, **kwargs):
    """
    分析多头、空头的收益
    """
    df = df[['dt', 'symbol', 'weight', 'price']].copy()
        
    dfl = df.copy()
    dfl['weight'] = dfl['weight'].clip(lower=0)
    
    dfs = df.copy()
    dfs['weight'] = dfs['weight'].clip(upper=0)
    
    wbs = {
        "原始策略": czsc.WeightBacktest(df, **kwargs),
        "策略多头": czsc.WeightBacktest(dfl, **kwargs),
        "策略空头": czsc.WeightBacktest(dfs, **kwargs)
    }
    czsc.svc.show_multi_backtest(wbs)
    return wbs


def show_weight_backtest(df: pd.DataFrame, **kwargs):

    yearly_days = kwargs.get("yearly_days", 252)
    tabs = st.tabs(["整体回测", "年度回测", "标的回测", "多空回测", "下载数据"])
    with tabs[0]:
        wb = czsc.svc.show_weight_backtest(df, fee=0.0, digits=2, yearly_days=yearly_days,
                                           show_drawdowns=True, show_splited_daily=True,)
    with tabs[1]:
        show_yearly_backtest(df, yearly_days=yearly_days, **kwargs)
        
    with tabs[2]:
        show_symbol_backtest(df, yearly_days=yearly_days, **kwargs)
        
    with tabs[3]:
        show_long_short_backtest(df, yearly_days=yearly_days, **kwargs)
        
    with tabs[4]:
        st.download_button("下载策略收益", data=wb.daily_return.to_csv(index=False), on_click="ignore",
                           file_name="strategy_returns.csv", mime="text/csv")
        st.download_button("下载多头收益", data=wb.long_daily_return.to_csv(index=False), on_click="ignore",
                           file_name="long_strategy_returns.csv", mime="text/csv")
        st.download_button("下载空头收益", data=wb.short_daily_return.to_csv(index=False), on_click="ignore",
                           file_name="short_strategy_returns.csv", mime="text/csv")


def main():
    from czsc import mock

    df = mock.generate_klines_with_weights(seed=42)
    dfw = df[['dt', 'symbol', 'weight', 'price']].copy()

    show_weight_backtest(dfw, fee_rate=0.0, digits=2, weight_type="ts")


main()

