import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import czsc
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

df = pd.DataFrame({
    "dt": pd.date_range("20210101", periods=1000),
    "ret": np.random.randn(1000)
})

czsc.show_daily_return(df)

czsc.show_monthly_return(df, ret_col="ret")
