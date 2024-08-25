import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

dfw = pd.read_feather(r"C:\Users\zengb\Downloads\ST组件样例数据\截面持仓权重样例数据.feather")
st.subheader("截面数据回测", divider="rainbow", anchor="截面数据回测")
czsc.show_holds_backtest(
    dfw,
    fee=2,
    digits=2,
    show_drawdowns=True,
    show_splited_daily=True,
    show_monthly_return=True,
    show_yearly_stats=True,
)
