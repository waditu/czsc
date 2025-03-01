import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


def prepare_data():
    df = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")
    return df[['dt', 'symbol', 'weight']]


def main():
    df = prepare_data()
    st.header("策略在标的上的权重分布", divider="rainbow")
    czsc.show_weight_distribution(df, abs_weight=True)


if __name__ == "__main__":
    main()

