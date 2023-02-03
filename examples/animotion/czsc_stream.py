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
import streamlit as st
from streamlit_echarts import st_pyecharts
from tqdm import tqdm
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.utils import freqs_sorted
from czsc.connectors import qmt_connector as qmc

st.set_page_config(layout="wide")


@st.cache(allow_output_mutation=True)
def init_czsc_signals(freqs, counts, symbol):

    def __get_freq_bars(freq):
        bars = qmc.get_kline(symbol, '5m', start_time="20150101", end_time='20230101',
                             count=-1, dividend_type='back', df=False)
        bg = BarGenerator(base_freq='5分钟', freqs=[freq], max_count=1000000)
        for bar in tqdm(bars[:-1]):
            bg.update(bar)
        return bg.bars[freq]

    bars = __get_freq_bars(freqs[0])
    bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
    for bar in bars[:-counts]:
        bg.update(bar)
    return CzscSignals(bg), bars[-counts:]


symbols = qmc.get_symbols('train')
freqs = freqs_sorted(['15分钟', '日线'])
cs, remain_bars = init_czsc_signals(freqs, counts=100, symbol=symbols[0])


def next_bar():
    bar = remain_bars.pop(0)
    cs.update_signals(bar)

    with st.container():
        st.write(f"当前K线：{bar.dt}")
        for i, freq in enumerate(freqs):
            st.subheader(f"{freq}")
            st_pyecharts(cs.kas[freq].to_echarts(), height='300px')


with st.sidebar:
    st.title("CZSC 逐K线播放")
    st.write(f"当前合约：{symbols[0]}")
    st.write(f"当前频率：{freqs}")
    but = st.button("下一根K线", on_click=next_bar)


