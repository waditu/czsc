# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/7/1 11:24
describe: 期货CTA投研，支持按板块统计表现
"""
import os
import czsc
import json
import glob
import hashlib
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
from tqdm import tqdm
from typing import List
from loguru import logger
from czsc import subtract_fee, net_value_stats
from multiprocessing import cpu_count
from czsc.connectors.research import get_symbols, get_raw_bars
from czsc import CzscStrategyBase, Position


class JsonStreamStrategy(CzscStrategyBase):
    """读取 streamlit 传入的 json 策略，进行回测"""
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


st.set_page_config(layout="wide", page_title="期货CTA投研", page_icon="🏕️")

future_plates = {
    "股指": ['SFIH9001', 'SFIC9001', 'SFIF9001', 'SFIM9001'],
    "黑色金属": ['ZZSF9001', 'ZZSM9001', 'SQhc9001', 'DLi9001', 'SQrb9001', 'SQss9001'],
    "轻工": ['SQsp9001', 'ZZFG9001', 'SEnr9001'],
    "软商品": ['ZZCF9001', 'ZZSR9001'],
    "贵金属": ['SQag9001', 'SQau9001'],
    "谷物": ['DLa9001', 'DLc9001'],
    "煤炭": ['DLj9001', 'DLjm9001'],
    "油脂油料": ['DLp9001', 'ZZRM9001', 'DLm9001', 'ZZOI9001', 'DLy9001'],
    "有色金属": ['SQsn9001', 'SQni9001', 'SQcu9001', 'SQzn9001', 'SQpb9001', 'SQal9001', 'SEbc9001'],
    "原油": ['SQfu9001', 'SEsc9001', 'DLpg9001', 'SElu9001'],
    "化工": [
        'SQbu9001',
        'DLeg9001',
        'ZZMA9001',
        'SQru9001',
        'DLl9001',
        'DLv9001',
        'ZZTA9001',
        'DLpp9001',
        'ZZUR9001',
        'DLeb9001',
        'ZZSA9001',
        'ZZPF9001',
    ],
    "农副": ['DLjd9001', 'DLlh9001', 'ZZAP9001', 'ZZPK9001'],
}

page_params = {"data_path": Path(r"D:\czsc_bi_datas\期货CTA投研")}
page_params['data_path'].mkdir(exist_ok=True, parents=True)


with st.sidebar:
    form = st.form(key='my_form_cta')
    files = form.file_uploader(label='上传策略文件', type='json', accept_multiple_files=True, key="files_cta")
    bar_sdt = form.date_input(label='行情开始日期', value=pd.to_datetime('2018-01-01'), key="bar_sdt_cta")
    sdt = form.date_input(label='回测开始日期', value=pd.to_datetime('2019-01-01'), key="sdt_cta")
    edt = form.date_input(label='回测结束日期', value=pd.to_datetime('2022-01-01'), key="edt_cta")
    max_workers = form.number_input(
        label='指定进程数量', value=cpu_count() // 4, min_value=1, max_value=cpu_count() // 2, key="max_workers_cta"
    )
    fee = int(form.number_input(label='单边手续费（单位：BP）', value=2, min_value=0, max_value=100, key="fee_cta"))
    submit_button = form.form_submit_button(label='开始回测')


@st.cache_data()
def read_holds_and_pairs(files_traders, pos_name, fee=1):
    holds, pairs = [], []
    for file in tqdm(files_traders):
        try:
            trader = czsc.dill_load(file)
            pos = trader.get_position(pos_name)
            if not pos.holds:
                logger.info(f"{trader.symbol} {pos_name} 无持仓，跳过")
                continue

            hd = pd.DataFrame(pos.holds)
            hd['symbol'] = trader.symbol
            hd = subtract_fee(hd, fee=fee)
            holds.append(hd)

            pr = pd.DataFrame(pos.pairs)
            pairs.append(pr)
        except Exception as e:
            logger.warning(f"{file} {pos_name} 读取失败: {e}")

    dfh = pd.concat(holds, ignore_index=True)
    dfp = pd.concat(pairs, ignore_index=True)
    return dfh, dfp


@st.cache_data()
def get_daily_nv(df):
    """获取每日净值"""
    res = []
    for symbol, hd in tqdm(df.groupby('symbol')):
        hd = hd.sort_values('dt', ascending=True)
        try:
            daily = hd.groupby('date').agg({'edge_pre_fee': 'sum', 'edge_post_fee': 'sum'}).reset_index()
            daily['symbol'] = symbol
            res.append(daily)
        except Exception as e:
            logger.exception(f"{symbol} 日收益获取失败: {e}")

    dfr = pd.concat(res, ignore_index=True)
    return dfr


def show_pos_detail(file_trader, pos_name):
    """显示持仓策略详情"""
    trader = czsc.dill_load(file_trader)
    pos = trader.get_position(pos_name)
    with st.expander(f"{pos_name} 持仓策略详情", expanded=False):
        _pos = pos.dump()
        _pos.pop('symbol')
        st.json(_pos)


def show_traders(file_traders, pos_name, fee=1):
    dfh, dfp = read_holds_and_pairs(file_traders, pos_name, fee=fee)
    dfr = get_daily_nv(dfh)
    show_pos_detail(file_traders[0], pos_name)

    st.subheader("一、单笔收益评价")
    from czsc import PairsPerformance

    pp = PairsPerformance(dfp)
    # st.write(pp.basic_info)
    df1 = pp.agg_statistics('标的代码')
    _res = pp.basic_info
    _res['标的代码'] = "全部品种"
    df1 = pd.concat([pd.DataFrame([_res]), df1], ignore_index=True)
    _cols = [
        '标的代码',
        '开始时间',
        '结束时间',
        '交易标的数量',
        '总体交易次数',
        '平均持仓K线数',
        '平均单笔收益',
        '单笔收益标准差',
        '交易胜率',
        '单笔盈亏比',
        '累计盈亏比',
        '盈亏平衡点',
        '每根K线收益',
    ]
    df1 = df1[_cols].set_index('标的代码')
    color_cols = ['交易标的数量', '总体交易次数', '平均持仓K线数', '平均单笔收益', '单笔收益标准差', 
                  '交易胜率', '单笔盈亏比', '累计盈亏比', '盈亏平衡点', '每根K线收益']
    df1 = df1.style.format('{0:,.2f}', subset=color_cols, na_rep="-").background_gradient(cmap='RdYlGn_r', subset=color_cols)

    st.dataframe(df1, use_container_width=True)

    st.divider()

    st.subheader("二、品种等权收益曲线")
    dfg = dfr.groupby('date').agg({'edge_pre_fee': 'mean', 'edge_post_fee': 'mean'}).cumsum()
    dfg.rename({'edge_pre_fee': '等权费前收益', 'edge_post_fee': f'双边扣费{2*fee}BP'}, axis=1, inplace=True)

    fig = px.line(dfg, x=dfg.index, y=['等权费前收益', f'双边扣费{2*fee}BP'], labels=[], title="全部品种日收益等权")
    st.plotly_chart(fig, use_container_width=True, height=600)

    dfg['dt'] = dfg.index.to_list()
    stats = []
    for col in ['等权费前收益', f'双边扣费{2*fee}BP']:
        dfg_ = dfg[['dt', col]].copy().rename(columns={col: 'edge'}).reset_index(drop=True)
        dfg_['edge'] = dfg_['edge'].diff()
        stats_ = net_value_stats(dfg_, sub_cost=False)
        stats_['name'] = col
        stats.append(stats_)
    st.dataframe(pd.DataFrame(stats).set_index('name'), use_container_width=True)


if files and sdt and max_workers:
    strategies = {file.name: json.loads(file.getvalue().decode("utf-8")) for file in files}
    symbols = get_symbols("期货主力")
    hash_code = hashlib.sha256(f"{str(strategies)}_{str(symbols)}".encode('utf-8')).hexdigest()[:8].upper()
    results_path = page_params['data_path'] / f"{sdt}_{edt}_{hash_code}"

    with st.sidebar.expander("策略详情", expanded=False):
        tactic = JsonStreamStrategy(json_strategies=strategies, symbol='symbol')
        st.caption(f"K线周期列表：{tactic.freqs}")
        st.caption("独立信号列表：")
        st.json(tactic.unique_signals)
        st.caption("信号函数配置：")
        st.json(tactic.signals_config)

    if not os.path.exists(results_path):
        os.makedirs(results_path, exist_ok=True)
        params = {"sdt": str(sdt), "edt": str(edt), "symbols": symbols}
        czsc.save_json(params, os.path.join(results_path, "params.json"))

        cta = czsc.CTAResearch(
            JsonStreamStrategy,
            get_raw_bars,
            results_path=results_path,
            json_strategies=strategies,
            signals_module_name='czsc.signals',
        )
        with st.spinner('正在执行策略回测，请耐心等候 ...'):
            cta.backtest(symbols, max_workers=int(max_workers), bar_sdt=bar_sdt, sdt=sdt, edt=edt)

    tabs = st.tabs(["所有品种", "行业板块"])
    with tabs[0]:
        file_traders = glob.glob(fr"{results_path}\backtest_*\traders\*.trader")
        all_pos_names = [x.name for x in czsc.dill_load(file_traders[0]).positions]
        pos_name = st.selectbox("选择持仓", all_pos_names, index=0, key="pos_name")
        show_traders(file_traders, pos_name, fee=fee)

    with tabs[1]:
        col1, col2 = st.columns([2, 4])
        plate = col1.selectbox("选择板块", list(future_plates.keys()), index=0, key="plate")
        symbols = future_plates[plate]  # type: ignore
        st.caption(f"板块包含品种：{symbols}")
        file_traders = glob.glob(fr"{results_path}\backtest_*\traders\*.trader")
        file_traders = [x for x in file_traders if os.path.basename(x).split(".")[0] in symbols]
        all_pos_names = [x.name for x in czsc.dill_load(file_traders[0]).positions]
        pos_name = col2.selectbox("选择持仓", all_pos_names, index=0, key="plate_pos_name")
        show_traders(file_traders, pos_name, fee=fee)
