# -*- coding: utf-8 -*-
import os

os.environ['czsc_max_bi_num'] = '20'
os.environ['czsc_research_cache'] = r"D:\CZSC投研数据"
os.environ['signals_module_name'] = 'czsc.signals'
import json
import streamlit as st
import pandas as pd
from typing import List
from copy import deepcopy
from czsc.utils.bar_generator import freq_end_time
from czsc.connectors.research import get_symbols, get_raw_bars
from czsc import CzscStrategyBase, Position, CzscTrader, KlineChart, Freq, Operate

st.set_page_config(layout="wide")

class Strategy(CzscStrategyBase):
    @property
    def positions(self) -> List[Position]:
        """返回当前的持仓策略"""
        json_strategies = self.kwargs.get("json_strategies")
        assert json_strategies, "请在初始化策略时，传入参数 json_strategies"
        positions = []
        for _, pos in json_strategies.items():
            pos["symbol"] = self.symbol
            positions.append(Position.load(pos))
        return positions

if 'bar_edt_index' not in st.session_state:
    st.session_state.bar_edt_index = 1

if 'run' not in st.session_state:
    st.session_state.run = False

if 'refresh' not in st.session_state:
    st.session_state.refresh = True

def update_bar_edt():
    bar_edt_ = pd.Timestamp(st.session_state.bar_edt)
    i = 1
    for x in bars_right:
        if x.dt >= bar_edt_:
            break
        i += 1
    st.session_state.bar_edt_index = i

def update_change():
    st.session_state.refresh = True
    st.session_state.bar_edt_index = 1

@st.cache_data
def get_bars(symbol_, base_freq_, sdt_, edt_):
    return get_raw_bars(symbol_, base_freq_, sdt=sdt_ - pd.Timedelta(days=365 * 3), edt=edt_)

with st.sidebar:
    st.title("CZSC策略回放工具")
    symbol = st.selectbox("选择标的：", get_symbols('ALL'), index=0, on_change=update_change)
    sdt = st.date_input("开始日期：", value=pd.to_datetime('2022-01-01'), on_change=update_change)
    edt = st.date_input("结束日期：", value=pd.to_datetime('2022-12-31'), on_change=update_change)
    files = st.file_uploader(label='上传策略文件', type='json', accept_multiple_files=True, on_change=update_change)

    if files:
        if st.session_state.refresh:
            json_strategies = {file.name: json.loads(file.getvalue().decode("utf-8")) for file in files}
            tactic: CzscStrategyBase = Strategy(
                symbol=symbol, signals_module_name=os.environ['signals_module_name'], json_strategies=json_strategies
            )
            bars = get_bars(symbol, tactic.base_freq, sdt, edt)
            bg, bars_right = tactic.init_bar_generator(bars, sdt=sdt)
            bars_num = len(bars_right)
            if bars_num > 1000:
                st.warning("回放数据量较大（超过1000根K线），建议缩小回放时间范围")
        else:
            st.session_state.refresh = False

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
    tabs = st.tabs(freqs + ['最后信号', '收益分析', '策略详情'])

    i = 0
    for freq in freqs:
        c = trader.kas[freq]
        df = pd.DataFrame(c.bars_raw)
        kline = KlineChart(n_rows=3, title='', width="100%", height=800)
        kline.add_kline(df, name="")

        if len(c.bi_list) > 0:
            bi = pd.DataFrame(
                [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list]
                + [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
            )
            fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
            kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=1.2, visible=True)
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
                kline.add_scatter_indicator(
                    bs_df['dt'],
                    bs_df['price'],
                    name=pos.name,
                    text=bs_df['op_desc'],
                    row=1,
                    mode='text+markers',
                    marker_size=15,
                    marker_symbol=bs_df['tag'],
                    marker_color=bs_df['color'],
                )

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
                    'hoverCompareCartesian',
                ],
            }
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
        for file in files:
            st.subheader(file.name)
            st.write(json.loads(file.getvalue().decode("utf-8")))

if files:
    if st.session_state.run:
        trader = CzscTrader(bg=bg, positions=deepcopy(tactic.positions), signals_config=deepcopy(tactic.signals_config))
        bars1 = bars_right[0 : st.session_state.bar_edt_index].copy()
        while bars1:
            bar_ = bars1.pop(0)
            trader.on_bar(bar_)

        bars2 = bars_right[st.session_state.bar_edt_index :].copy()
        with st.empty():
            while bars2:
                bar_ = bars2.pop(0)
                trader.on_bar(bar_)
                show_trader(trader)
                st.session_state.bar_edt_index += 1

    else:
        trader = CzscTrader(bg=bg, positions=deepcopy(tactic.positions), signals_config=deepcopy(tactic.signals_config))
        bars2 = bars_right[0 : st.session_state.bar_edt_index].copy()
        with st.empty():
            while bars2:
                bar_ = bars2.pop(0)
                trader.on_bar(bar_)
            show_trader(trader)
