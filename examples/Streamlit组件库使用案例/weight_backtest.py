import sys

sys.path.insert(0, ".")
sys.path.insert(0, "..")

import czsc
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(layout="wide")

st.write(czsc.__version__)

# czsc.show_weight_backtest(
#     dfw, fee=2, digits=2, show_drawdowns=True, show_monthly_return=True, show_yearly_stats=True, show_splited_daily=True
# )

df = pd.read_feather(r"A:\桌面临时数据\标准K线数据.feather")
df['weight'] = df.groupby('symbol')['close'].pct_change().fillna(0)
df['weight'] = np.sign(df['weight'])

with st.container(border=True):
    st.subheader("CTA后验收益分类", divider="rainbow")
    czsc.show_cta_periods_classify(
        df, fee_rate=0.00, digits=2, weight_type='ts', q1=0.15, q2=0.4
    )

with st.container(border=True):
    st.subheader("波动率后验收益分类", divider="rainbow")
    czsc.show_volatility_classify(
        df, fee_rate=0.00, digits=2, weight_type='ts', kind='ts', window=20, q1=0.2, q2=0.2
    )
