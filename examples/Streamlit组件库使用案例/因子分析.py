import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

df = pd.read_feather(r"C:\Users\zengb\Downloads\ST组件样例数据\因子数据样例.feather")
factor = [x for x in df.columns if x.startswith("F#")][0]
# czsc.show_factor_layering(df, factor=factor, target="n1b", n=10)

# czsc.show_feature_returns(df, factor, target="n1b", fit_intercept=True)

czsc.show_sectional_ic(df, factor, "n1b", show_factor_histgram=True, show_cumsum_ic=True)
