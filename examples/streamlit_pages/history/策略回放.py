# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/11 20:49
describe: CZSC策略回放
"""
import os
os.environ['czsc_max_bi_num'] = '20'
os.environ['czsc_research_cache'] = r"D:\CZSC投研数据"
os.environ['signals_module_name'] = 'czsc.signals'
import inspect
import streamlit as st
import pandas as pd
from typing import List
from copy import deepcopy
from czsc.utils.bar_generator import freq_end_time
from czsc.connectors.research import get_symbols, get_raw_bars
from czsc import CzscStrategyBase, Position, CzscTrader, KlineChart, Freq, Operate

st.set_page_config(layout="wide")

# ======================================================================================================================
# 将策略的代码放在这里，命名是 Strategy
# ----------------------------------------------------------------------------------------------------------------------

# 可以直接导入策略类，也可以直接写在这里
from czsc.strategies import CzscStrategyExample2 as Strategy


# class Strategy(CzscStrategyBase):
#
#     @staticmethod
#     def create_long_bi(symbol, freq1='5分钟', freq2='60分钟'):
#         """
#
#         :param symbol:
#         :param freq1:
#         :param freq2:
#         :return:
#         """
#         _pos_name = f'{freq1}#{freq2}向下笔多头'
#         _pos = {'symbol': symbol,
#                 'name': _pos_name,
#                 'opens': [
#                     {'operate': '开多',
#                      'factors': [
#                          {'name': f'{freq1}向下笔停顿分型',
#                           'signals_all': [
#                               f'{freq1}_D0停顿分型_BE辅助V230106_看多_任意_任意_0',
#                               f'{freq2}_D0停顿分型_BE辅助V230106_看多_任意_任意_0'
#                           ]},
#
#                          {'name': f'{freq1}向下笔验证分型',
#                           'signals_all': [
#                               f'{freq1}_D0验证分型_BE辅助V230107_看多_任意_任意_0'
#                           ]},
#                      ]}
#                 ],
#                 'exits': [
#                     {'operate': '平多',
#                      'factors': [
#                          {'name': f'{freq1}停顿分型止盈',
#                           'signals_all': [
#                               f'{freq1}_D0停顿分型_BE辅助V230106_看空_任意_任意_0'
#                           ]},
#
#                          {'name': f'{freq1}验证分型止盈',
#                           'signals_all': [
#                               f'{freq1}_D0验证分型_BE辅助V230107_看空_任意_任意_0'
#                           ]},
#                      ]},
#                 ],
#                 'interval': 7200,
#                 'timeout': 1000,
#                 'stop_loss': 300,
#                 'T0': True}
#
#         return Position.load(_pos)
#
#     @property
#     def positions(self) -> List[Position]:
#         _pos_list = [
#             self.create_long_bi(symbol=self.symbol, freq1='5分钟', freq2='60分钟'),
#             # self.create_long_bi(symbol=self.symbol, freq1='15分钟', freq2='60分钟'),
#         ]
#         return _pos_list


# ======================================================================================================================
# 以下代码不用修改
# ----------------------------------------------------------------------------------------------------------------------
if 'bar_edt_index' not in st.session_state:
    st.session_state.bar_edt_index = 1

if 'run' not in st.session_state:
    st.session_state.run = False

if 'date_change' not in st.session_state:
    st.session_state.date_change = True


def update_bar_edt():
    bar_edt_ = pd.Timestamp(st.session_state.bar_edt)
    i = 1
    for x in bars_right:
        if x.dt >= bar_edt_:
            break
        i += 1
    st.session_state.bar_edt_index = i


def update_date_change():
    st.session_state.date_change = True
    st.session_state.bar_edt_index = 1


@st.cache_data
def get_bars(symbol_, base_freq_, sdt_, edt_):
    delta_days_map = {
        '1分钟': 6,
        '5分钟': 45,
        '15分钟': 90,
        '30分钟': 180,
        '60分钟': 365,
        '日线': 365 * 3,
        '周线': 365 * 7,
    }
    return get_raw_bars(symbol_, base_freq_, sdt=sdt_ - pd.Timedelta(days=delta_days_map[base_freq_]), edt=edt_)


with st.sidebar:
    st.title("CZSC策略回放")
    symbol = st.selectbox("选择标的：", get_symbols('ALL'), index=0, on_change=update_date_change)
    sdt = st.date_input("开始日期：", value=pd.to_datetime('2022-01-01'), on_change=update_date_change)
    edt = st.date_input("结束日期：", value=pd.to_datetime('2022-12-31'), on_change=update_date_change)
    czsc_strategy = Strategy
    tactic: CzscStrategyBase = czsc_strategy(symbol=symbol, signals_module_name=os.environ['signals_module_name'])

    if st.session_state.date_change:
        bars = get_bars(symbol, tactic.base_freq, sdt, edt)
        bg, bars_right = tactic.init_bar_generator(bars, sdt=sdt)
        if len(bars_right) > 1000:
            bars_right = bars_right[:1000]  # 限制回放的数据量
            st.warning("回放数据量过大，已限制为1000根K线")
        bars_num = len(bars_right)
    else:
        st.session_state.date_change = False

    c1, c2, c3, c4 = st.columns([5, 5, 5, 5])
    with c1:
        button_run = st.button('播放')
        if button_run:
            st.session_state.run = True

    with c2:
        button_run = st.button('暂停')
        if button_run:
            st.session_state.run = False

    with c3:
        button_dec = st.button('左移')
        if button_dec:
            st.session_state.bar_edt_index -= 1
            st.session_state.bar_edt_index = max(st.session_state.bar_edt_index, 0)

    with c4:
        button_inc = st.button('右移')
        if button_inc:
            st.session_state.bar_edt_index += 1
            st.session_state.bar_edt_index = min(st.session_state.bar_edt_index, bars_num)

    bar_edt = bars_right[st.session_state.bar_edt_index - 1].dt
    st.text_input('定位到指定时间', value=bar_edt.strftime('%Y-%m-%d %H:%M'), key="bar_edt", on_change=update_bar_edt)

    st.success(f"共{bars_num}根K线, 时间范围：{bars_right[0].dt} - {bars_right[-1].dt}; 当前K线：{bar_edt}")


def show_trader(trader: CzscTrader):
    freqs = trader.freqs
    tabs = st.tabs(freqs + ['最后信号', '收益分析', '策略脚本'])

    i = 0
    for freq in freqs:
        c = trader.kas[freq]
        df = pd.DataFrame(c.bars_raw)
        kline = KlineChart(n_rows=3, title='', width="100%", height=800)
        kline.add_kline(df, name="")

        if len(c.bi_list) > 0:
            bi = pd.DataFrame([{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list] +
                              [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}])
            fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
            kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=1.2,
                                        visible=True)
            kline.add_scatter_indicator(bi['dt'], bi['bi'], name="笔", row=1, line_width=1.5)

        kline.add_sma(df, ma_seq=(5, 20, 120, 240), row=1, visible=False, line_width=1)
        kline.add_vol(df, row=2, line_width=1)
        kline.add_macd(df, row=3, line_width=1)

        for pos in trader.positions:
            bs_df = pd.DataFrame([x for x in pos.operates if x['dt'] >= c.bars_raw[0].dt])
            if not bs_df.empty:
                bs_df['dt'] = bs_df['dt'].apply(lambda x: freq_end_time(x, Freq(freq)))
                bs_df['tag'] = bs_df['op'].apply(lambda x: 'triangle-up' if x == Operate.LO else 'triangle-down')
                bs_df['color'] = bs_df['op'].apply(lambda x: 'red' if x == Operate.LO else 'silver')
                kline.add_scatter_indicator(bs_df['dt'], bs_df['price'], name=pos.name, text=bs_df['op_desc'], row=1,
                                            mode='text+markers', marker_size=15, marker_symbol=bs_df['tag'],
                                            marker_color=bs_df['color'])

        with tabs[i]:
            config = {
                "scrollZoom": True,
                "displayModeBar": True,
                "displaylogo": False,
                'modeBarButtonsToRemove': [
                    'toggleSpikelines',
                    'select2d',
                    'zoomIn2d',
                    'zoomOut2d',
                    'lasso2d',
                    'autoScale2d',
                    'hoverClosestCartesian',
                    'hoverCompareCartesian']}
            st.plotly_chart(kline.fig, use_container_width=True, config=config)
        i += 1

    # 信号页
    with tabs[i]:
        if len(trader.s):
            s = {k: v for k, v in trader.s.items() if len(k.split('_')) == 3}
            st.write(s)
    i += 1

    with tabs[i]:
        df = pd.DataFrame([x.evaluate() for x in trader.positions])
        st.dataframe(df, use_container_width=True)

        with st.expander("分别查看多头和空头的表现", expanded=False):
            df1 = pd.DataFrame([x.evaluate('多头') for x in trader.positions])
            st.dataframe(df1, use_container_width=True)

            df2 = pd.DataFrame([x.evaluate('空头') for x in trader.positions])
            st.dataframe(df2, use_container_width=True)

    i += 1
    with tabs[i]:
        st.code(inspect.getsource(czsc_strategy))


if st.session_state.run:
    trader = CzscTrader(bg=bg, positions=deepcopy(tactic.positions), signals_config=deepcopy(tactic.signals_config))
    bars1 = bars_right[0:st.session_state.bar_edt_index].copy()
    while bars1:
        bar_ = bars1.pop(0)
        trader.on_bar(bar_)

    bars2 = bars_right[st.session_state.bar_edt_index:].copy()
    with st.empty():
        while bars2:
            bar_ = bars2.pop(0)
            trader.on_bar(bar_)
            show_trader(trader)
            st.session_state.bar_edt_index += 1

else:
    trader = CzscTrader(bg=bg, positions=deepcopy(tactic.positions), signals_config=deepcopy(tactic.signals_config))
    bars2 = bars_right[0:st.session_state.bar_edt_index].copy()
    with st.empty():
        while bars2:
            bar_ = bars2.pop(0)
            trader.on_bar(bar_)
        show_trader(trader)
