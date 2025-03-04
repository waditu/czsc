import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")

import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

df = pd.read_feather(r"C:\Users\zengb\Downloads\ST组件样例数据\日收益样例数据.feather")
df['returns'] = df['total']
df = df[['dt', 'returns']].copy()

st.header("两段样本内外对比", divider="rainbow")
czsc.show_outsample_by_dailys(df, outsample_sdt1="2022-01-01")

st.header("三段样本内外对比", divider="rainbow")
czsc.show_outsample_by_dailys(df, outsample_sdt1="2022-01-01", outsample_sdt2="2023-01-01")
