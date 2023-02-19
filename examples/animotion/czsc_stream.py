# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/7/12 14:22
describe: CZSC 逐K线播放
https://pyecharts.org/#/zh-cn/web_flask

环境：
streamlit-echarts
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
os.environ['czsc_max_bi_num'] = '20'
import time
import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.utils import freqs_sorted
from czsc.connectors import qmt_connector as qmc

st.set_page_config(layout="wide")


with st.sidebar:
    st.title("CZSC 逐K回放")
    symbol = st.selectbox("选择合约", options=qmc.get_symbols('train'), index=0)
    freqs = st.multiselect("选择频率", options=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'], default=['30分钟', '日线'])
    freqs = freqs_sorted(freqs)
    sleep_time = st.number_input("播放速度", value=6, min_value=1, max_value=100, step=1)
    counts = st.number_input("K线数量", value=100, min_value=1, max_value=1000, step=5)
    auto_play = st.checkbox("自动播放", value=True)


bars = qmc.get_raw_bars(symbol, freqs[0], sdt="20150101", edt='20230101')
bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
for bar in bars[:-counts]:
    bg.update(bar)
cs, remain_bars = CzscSignals(bg), bars[-counts:]

with st.empty():
    while auto_play and remain_bars:
        bar = remain_bars.pop(0)
        cs.update_signals(bar)
        with st.container():
            # logger.info(f"当前K线：{bar.dt}, {bar.close}, freqs: {freqs}")
            st.write(f"当前K线：{bar.dt}")
            for i, freq in enumerate(freqs):
                # st.subheader(f"{freq}")
                df = pd.DataFrame(cs.kas[freq].bars_raw)
                df['text'] = ""
                fig = go.Figure(data=[
                    go.Candlestick(x=df['dt'], open=df["open"], high=df["high"], low=df["low"],
                                   close=df["close"], text=df['text']),
                ])
                fig.update_layout(title=f"{symbol} {freq}")
                fig = fig.update_yaxes(showgrid=True, automargin=True, autorange=True)
                fig = fig.update_xaxes(type='category', rangeslider_visible=True, showgrid=False, automargin=True,
                                       showticklabels=False)
                st.plotly_chart(fig, use_container_width=True, height=300)
        time.sleep(sleep_time)

st.success(f'{symbol} {freqs} K线回放完成！', icon="✅")

