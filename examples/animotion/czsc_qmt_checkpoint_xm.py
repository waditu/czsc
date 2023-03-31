# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/7/12 14:22
describe: 使用 QMT 数据进行 CZSC K线检查

环境：
streamlit-echarts
"""
import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
import os

os.environ.setdefault('czsc_welcome', '1')
os.environ.setdefault('czsc_max_bi_num', '50')

import streamlit as st
import pandas as pd
from loguru import logger
from datetime import datetime
from czsc.utils import KlineChart
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.utils import freqs_sorted
from czsc.connectors import qmt_connector as qmc
from xm_util import indicator_xm

st.set_page_config(layout="wide")

config = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    'modeBarButtonsToRemove': [
        # 'zoom2d', # ming 注释掉
        'toggleSpikelines',
        # 'pan2d', # ming 注释掉
        'select2d',
        'zoomIn2d',
        'zoomOut2d',
        'lasso2d',
        'autoScale2d',
        'hoverClosestCartesian',
        'hoverCompareCartesian']}

with st.sidebar:
    st.title("CZSC复盘工具")
    symbol = st.selectbox("选择合约", options=qmc.get_symbols('stock'), index=0)
    sdt = st.date_input("开始日期", value=datetime(2015, 1, 1))
    edt = st.date_input("结束日期", value=datetime.now())
    freqs = st.multiselect("选择周期", options=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'],
                           default=['15分钟', '30分钟', '60分钟', '日线', '周线'])  # ming from 频率 to 周期 ,default修改
    freqs = freqs_sorted(freqs)

bars = qmc.get_raw_bars(symbol, freqs[0], sdt=sdt, edt=edt)
bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
counts = 100
for bar in bars[:-counts]:
    bg.update(bar)
cs, remain_bars = CzscSignals(bg), bars[-counts:]
for bar in remain_bars:
    cs.update_signals(bar)

tabs = st.tabs(freqs)

for i, freq in enumerate(freqs):
    c = cs.kas[freq]
    df = pd.DataFrame(c.bars_raw)
    df['text'] = "测试"
    kline = KlineChart(n_rows=4, title='', width="100%", height=700)  # ming title=f"{freq} K线" to '',再添加height
    kline.add_kline(df, name="")  # ming name='' from "K线"
    kline.add_sma(df, ma_seq=(5, 10, 21), row=1, visible=True, line_width=0.6)  # ming add line_width
    kline.add_sma(df, ma_seq=(34, 55, 89, 144), row=1, visible=False, line_width=0.6)  # ming add line_width
    kline.add_vol(df, row=2, line_width=1)
    kline.add_macd(df, row=3, line_width=1)

    if len(c.bi_list) > 0:
        bi = pd.DataFrame(
            [{'dt': x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value} for x in c.bi_list] +
            [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx,
              "text": c.bi_list[-1].fx_b.mark.value}])
        fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
        kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=1.2, visible=False, line_dash='dash')
        kline.add_scatter_indicator(bi['dt'], bi['bi'], name="笔", text='', row=1, line_width=1.8)

    with tabs[i]:
        st.plotly_chart(kline.fig, use_container_width=True, config=config)
