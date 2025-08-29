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
sys.path.insert(0, '../..')
import os

os.environ['czsc_max_bi_num'] = '20'
import time
import streamlit as st
import pandas as pd
from czsc.utils import KlineChart
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.utils import freqs_sorted
from czsc.connectors import qmt_connector as qmc

st.set_page_config(layout="wide")

with st.sidebar:
    st.title("CZSC 逐K回放")
    symbol = st.selectbox("选择合约", options=qmc.get_symbols('train'), index=0)
    freqs = st.multiselect("选择频率", options=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'],
                           default=['30分钟', '日线'])
    freqs = freqs_sorted(freqs)
    sleep_time = st.number_input("播放速度", value=6, min_value=1, max_value=100, step=1)
    counts = st.number_input("K线数量", value=100, min_value=1, max_value=1000, step=5)
    auto_play = st.checkbox("自动播放", value=True)

bars = qmc.get_raw_bars(symbol, freqs[0], sdt="20150101", edt='20230101')
bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
for bar in bars[:-counts]:
    bg.update(bar)
cs, remain_bars = CzscSignals(bg), bars[-counts:]

config = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    'modeBarButtonsToRemove': [
        'zoom2d',
        'toggleSpikelines',
        'pan2d',
        'select2d',
        'zoomIn2d',
        'zoomOut2d',
        'lasso2d',
        'autoScale2d',
        'hoverClosestCartesian',
        'hoverCompareCartesian']}

with st.empty():
    while auto_play and remain_bars:
        bar = remain_bars.pop(0)
        cs.update_signals(bar)
        with st.container():
            # logger.info(f"当前K线：{bar.dt}, {bar.close}, freqs: {freqs}")
            st.write(f"当前K线：{bar.dt}")

            for i, freq in enumerate(freqs):
                c = cs.kas[freq]
                df = pd.DataFrame(c.bars_raw)
                df['text'] = "测试"
                kline = KlineChart(n_rows=3, title=f"{freq} K线", width="100%")
                kline.add_kline(df, name="K线")
                kline.add_sma(df, ma_seq=(5, 10, 21), row=1, visible=True)
                kline.add_sma(df, ma_seq=(34, 55, 89, 144), row=1, visible=False)
                kline.add_vol(df, row=2)
                kline.add_macd(df, row=3)
                if len(c.bi_list) > 0:
                    bi = pd.DataFrame(
                        [{'dt': x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value} for x in c.bi_list] +
                        [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx,
                          "text": c.bi_list[-1].fx_b.mark.value}])
                    fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
                    kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=1.2)
                    kline.add_scatter_indicator(bi['dt'], bi['bi'], name="笔", text=bi['text'], row=1, line_width=1.2)
                st.plotly_chart(kline.fig, use_container_width=True, height=300, config=config)
        time.sleep(sleep_time)

st.success(f'{symbol} {freqs} K线回放完成！', icon="✅")
