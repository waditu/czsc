# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/10 22:27
describe: 使用掘金数据查看信号的实际效果

环境：
pip install czsc -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install streamlit -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install streamlit_echarts -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pyecharts -i https://pypi.tuna.tsinghua.edu.cn/simple
"""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")
import czsc
import streamlit as st
import czsc.connectors.gm_connector as gmc

st.set_page_config(layout="wide", page_title="CZSC 信号实际效果查看")

st.title("CZSC 信号实际效果查看")

with st.form(key='my_form'):
    col1, col2, col3 = st.columns([2, 3, 1], gap='small')
    with col1:
        symbol = st.text_input("输入股票代码", value="SHSE.600000")
    with col2:
        freqs = st.multiselect("选择频率",
                               options=["1分钟", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"],
                               default=["60分钟", "日线", "周线", "月线"], help="注意：基础周期必须是分钟线")
        freqs = czsc.freqs_sorted(freqs)
    with col3:
        submit_button = st.form_submit_button(label='查看K线图', use_container_width=True,
                                              help="注意：基础周期必须是分钟线；如果没有数据，可能是掘金数据源的问题")


tabs = st.tabs(freqs)
if submit_button:
    ct = gmc.gm_take_snapshot(symbol, freqs=freqs)
    for i, freq in enumerate(freqs):
        with tabs[i]:
            chart = ct.kas[freq].to_plotly()
            st.plotly_chart(chart, height='800px', use_container_width=True)
