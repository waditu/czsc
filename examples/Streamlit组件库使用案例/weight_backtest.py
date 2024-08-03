import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

dfw = pd.read_feather(r"C:\Users\zengb\Downloads\ST组件样例数据\时序持仓权重样例数据.feather")

if __name__ == "__main__":
    st.subheader("时序持仓策略回测样例", anchor="时序持仓策略回测样例", divider="rainbow")
    czsc.show_weight_backtest(
        dfw, fee=2, digits=2, show_drawdowns=True, show_monthly_return=True, show_yearly_stats=True
    )
