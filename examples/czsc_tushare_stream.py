# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/7/12 14:22
describe: 用 tushare 数据复盘K线行情
环境：
streamlit-echarts
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import streamlit as st
from datetime import datetime
import streamlit_echarts as st_echarts
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.utils import freqs_sorted
from czsc.data import TsDataCache, get_symbols


st.set_page_config(layout="wide")

dc = TsDataCache(data_path=r"D:\ts_data")

with st.sidebar:
    st.title("使用 tushare 数据复盘K线行情")
    symbol = st.selectbox("选择合约", options=get_symbols(dc, 'index'), index=0)
    edt = st.date_input("结束时间", value=datetime.now())


ts_code, asset = symbol.split('#')
bars = dc.pro_bar_minutes(ts_code=ts_code, asset=asset, freq='5min', sdt="20150101", edt=edt)
st.success(f'{symbol} K线加载完成！', icon="✅")
freqs = ['5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线']
counts = 100
bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
for bar in bars[:-counts]:
    bg.update(bar)
cs, remain_bars = CzscSignals(bg), bars[-counts:]
for bar in remain_bars:
    cs.update_signals(bar)

for freq in freqs:
    st.subheader(f"{freq} K线")
    st_echarts.st_pyecharts(cs.kas[freq].to_echarts(), width='100%', height='600px')



