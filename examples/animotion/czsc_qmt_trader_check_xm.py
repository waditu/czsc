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
strategy_path = 'C:\\czsc_realtime\\strategys'
sys.path.insert(0, strategy_path)
sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
import os

os.environ.setdefault('czsc_max_bi_num', '50')  # ming 如果想看多一点以前的k线，就可以把这个调大点，缺省是50
import streamlit as st
import pandas as pd
from datetime import datetime
import czsc
from czsc.objects import Freq, Operate
from czsc.utils import KlineChart
from czsc.strategies import CzscStrategyBase
from czsc.traders.base import CzscSignals, BarGenerator, CzscTrader
from czsc.utils import freqs_sorted
from czsc.connectors import qmt_connector as qmc
from xm_util import indicator_xm
import inspect
import glob
import importlib
# from st_aggrid import AgGrid

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
@st.cache_data
def get_strategys():
    strategys = []
    pathnames = glob.glob(os.path.join(strategy_path, '*.py'))
    for pathname in pathnames:
        strategyfilename = os.path.basename(pathname)[:-3]
        module = importlib.import_module(strategyfilename)
        for clsname, obj in inspect.getmembers(module, inspect.isclass):
            # print('name',name)
            # print('obj',obj)
            if clsname.startswith('CzscStrategy') and clsname != 'CzscStrategyBase':
                strategys.append(strategyfilename + '.' + clsname)
    strategys = set(strategys)
    return strategys

with st.sidebar:
    st.title("CZSC复盘工具")
    strategys = get_strategys()

    # print('策略列表',strategys)
    strategy_name = st.selectbox("选择策略", options=strategys, index=0)
    symbol = st.selectbox("选择合约", options=qmc.get_symbols('stock'), index=0)
    sdt = st.date_input("开始日期", value=datetime(2022, 1, 1))
    edt = st.date_input("结束日期", value=datetime.now())
    # freqs = st.multiselect("选择周期", options=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'],
    #                        default=['15分钟', '30分钟', '60分钟', '日线', '周线'])  # ming from 频率 to 周期 ,default修改
    # freqs = freqs_sorted(freqs)

#########trader begin
# strategy_name = 'corab.CzscStocksV230316'
# print(strategy_name)
czsc_strategy = czsc.import_by_name(strategy_name)
codes = inspect.getsource(czsc_strategy)
tactic:CzscStrategyBase = czsc_strategy(symbol=symbol)
freqs = freqs_sorted(tactic.freqs)
# print(freqs)
bars = qmc.get_raw_bars(symbol, freqs[0], sdt=sdt, edt=edt)
mdt = max(sdt,edt-pd.Timedelta(days=60))
trader:CzscTrader = tactic.init_trader(bars, sdt=mdt)
# print(trader.positions[0].pairs)

#########trader end
tabnames = []
tabnames.extend(freqs)
tabnames.append('最后信号')
tabnames.append('策略脚本')
# print(tabnames)
tabs = st.tabs(tabnames)

i=0
# K线页
for freq in freqs:
    c = trader.kas[freq]
    df = pd.DataFrame(c.bars_raw)
    df['text'] = "测试"
    kline = KlineChart(n_rows=4, title='', width="100%", height=600)  # ming title=f"{freq} K线" to '',再添加height
    kline.add_kline(df, name="")  # ming name='' from "K线"
    if len(c.bi_list) > 0:
        bi = pd.DataFrame(
            [{'dt': x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value} for x in c.bi_list] +
            [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx,
              "text": c.bi_list[-1].fx_b.mark.value}])
        fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
        kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=0.6, visible=False)  # ming line_width from 1.2 to 0.6 ,add visibal
        kline.add_scatter_indicator(bi['dt'], bi['bi'], name="笔", text='', row=1, line_width=1.5)  # ming text=bi['text'] to ''

    kline.add_sma(df, ma_seq=(5, 10, 21), row=1, visible=True, line_width=0.6)  # ming add line_width
    kline.add_sma(df, ma_seq=(34, 55, 89, 144), row=1, visible=False, line_width=0.6)  # ming add line_width
    kline.add_vol(df, row=2, line_width=1)
    kline.add_macd(df, row=3, line_width=1)
    s, m, l, bar = indicator_xm(df)  # s,m,l分别是短，中，长线型指标，b是bar型指标
    kline.add_indicator(dt=df['dt'], scatters=[s, m, l], scatternames=['短', '中', '长'], bar=bar, barname='柱', row=4)
    #买卖点begin
    from czsc.utils.bar_generator import freq_end_time

    bs = []
    for pos in trader.positions:
        for op in pos.operates:
            if op['dt'] >= c.bars_raw[0].dt:
                _op = dict(op)
                _op['op_desc'] = f"{pos.name} | {_op['op_desc']}"
                _op['dt'] = freq_end_time(op['dt'], Freq(freq))
                if op['op'] == Operate.LO:
                    _op['tag'] = 'triangle-up'
                    _op['color'] = 'red'
                else:
                    _op['tag'] = 'triangle-down'
                    _op['color'] = 'silver'
                bs.append(_op)
    bs_df = pd.DataFrame(bs)
    kline.add_marker_indicator(bs_df['dt'],bs_df['price'],name='OP',text=bs_df['op_desc'], row=1, line_width=0.5,tag=bs_df['tag'],color=bs_df['color'])
    #买卖点end


    with tabs[i]:
        st.plotly_chart(kline.fig, use_container_width=True, config=config)  # ming 删除height，height通过构造函数送入，在里面通过updatelayout实现
    i += 1

# 信号页
with tabs[i]:
    for freq in freqs:
        st.text(freq)
        if len(trader.s):
            s = trader.s.copy()
            for k in ['freq', 'cache','symbol','dt','close','id','open','high','low','vol','amount']:
                s.pop(k)
            st.write(s)
i += 1

# 策略脚本页
with tabs[i]:
    st.text(codes)
i += 1