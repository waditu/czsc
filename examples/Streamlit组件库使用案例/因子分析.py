import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")

import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

def prepare_data():
    df = pd.read_feather(r"C:\Users\zengb\Downloads\ST组件样例数据\因子数据样例.feather")
    factor = [x for x in df.columns if x.startswith("F#")][0]
    df = df[df['symbol'] == 'DLj9001'][['dt', 'open', 'close', 'high', 'low', 'vol', factor]]
    return df, factor

def main():
    df, factor = prepare_data()
    st.header("因子值可视化", divider="rainbow")
    czsc.show_factor_value(df, factor)


if __name__ == "__main__":
    main()

