import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


def prepare_data():
    df = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")
    wb = czsc.WeightBacktest(df[['dt', 'symbol', 'weight', 'price']], digits=2, fee_rate=0.0002, 
                             n_jobs=1, weight_type="ts", yearly_days=252)
    returns = wb.daily_return.copy()
    returns = returns.set_index('date')['total']
    return returns


def main():
    returns = prepare_data()
    czsc.show_seasonal_effect(returns)


if __name__ == "__main__":
    main()

