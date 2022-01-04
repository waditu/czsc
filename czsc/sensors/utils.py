# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 18:50
"""
import os
import warnings
import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime, timedelta
from typing import Callable, List, AnyStr

from ..traders.advanced import CzscAdvancedTrader, BarGenerator
from ..data.ts_cache import TsDataCache
from ..objects import RawBar, Signal
from ..signals.signals import get_default_signals
from ..utils.cache import home_path


def get_index_beta(dc: TsDataCache, sdt: str, edt: str, freq='D', file_xlsx=None, indices=None):
    """获取基准指数的Beta

    :param dc: 数据缓存对象
    :param sdt: 开始日期
    :param edt: 结束日期
    :param freq: K线周期，D 日线，W 周线，M 月线
    :param file_xlsx: 结果保存文件
    :param indices: 定义指数列表
    :return:
    """
    if not indices:
        indices = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']

    beta = {}
    p = []
    for ts_code in indices:
        df = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq=freq, asset="I", raw_bar=False)
        beta[ts_code] = df
        df = df.fillna(0)
        start_i, end_i, mdd = max_draw_down(df['n1b'].to_list())
        start_dt = df.iloc[start_i]['trade_date']
        end_dt = df.iloc[end_i]['trade_date']
        row = {
            '标的': ts_code,
            "开始日期": sdt,
            "结束日期": edt,
            "最大回撤": mdd,
            "回撤开始": start_dt,
            "回撤结束": end_dt,
            "交易次数": len(df),
            "交易胜率": round(len(df[df.n1b > 0]) / len(df), 4),
            "累计收益": round(df.n1b.sum(), 4),
        }
        cols = [x for x in df.columns if x[0] == 'n' and x[-1] == 'b']
        row.update({x: round(df[x].mean(), 4) for x in cols})
        p.append(row)

    dfp = pd.DataFrame(p)
    if file_xlsx:
        f = pd.ExcelWriter(file_xlsx)
        dfp.to_excel(f, index=False, sheet_name="指数表现")
        for name, df_ in beta.items():
            df_.to_excel(f, index=False, sheet_name=name)
        f.close()
    else:
        beta['dfp'] = dfp
        return beta


def generate_signals(bars: List[RawBar],
                     sdt: AnyStr,
                     base_freq: AnyStr,
                     freqs: List[AnyStr],
                     get_signals: Callable,
                     max_bi_count: int = 50,
                     bi_min_len: int = 7,
                     signals_n: int = 0,
                     ):
    """获取历史信号

    :param bars: 日线
    :param sdt: 信号计算开始时间
    :param base_freq: 合成K线的基础周期
    :param freqs: K线周期列表
    :param get_signals: 单级别信号计算函数
    :param max_bi_count: 单个级别最大保存笔的数量
    :param bi_min_len: 一笔最小无包含K线数量
    :param signals_n: 见 `CZSC` 对象
    :return: signals
    """
    sdt = pd.to_datetime(sdt)
    bars_left = [x for x in bars if x.dt < sdt]
    if len(bars_left) <= 500:
        bars_left = bars[:500]
        bars_right = bars[500:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]

    if len(bars_right) == 0:
        warnings.warn("右侧K线为空，无法进行信号生成", category=RuntimeWarning)
        return []

    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    signals = []
    ct = CzscAdvancedTrader(bg, get_signals, max_bi_count=max_bi_count,
                            bi_min_len=bi_min_len, signals_n=signals_n)
    for bar in tqdm(bars_right, desc=f'generate signals of {bg.symbol}'):
        ct.update(bar)
        signals.append(dict(ct.s))
    return signals


def check_signals_acc(bars: List[RawBar],
                      signals: List[Signal],
                      freqs: List[AnyStr],
                      get_signals: Callable = get_default_signals) -> None:
    """人工验证形态信号识别的准确性的辅助工具：

    输入基础周期K线和想要验证的信号，输出信号识别结果的快照

    :param bars: 原始K线
    :param signals: 需要验证的信号列表
    :param freqs: 周期列表
    :param get_signals: 信号计算函数
    :return:
    """
    base_freq = bars[-1].freq.value
    assert bars[2].dt > bars[1].dt > bars[0].dt and bars[2].id > bars[1].id, "bars 中的K线元素必须按时间升序"
    if len(bars) < 600:
        return

    bars_left = bars[:500]
    bars_right = bars[500:]
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    ct = CzscAdvancedTrader(bg, get_signals)
    last_dt = {signal.key: ct.end_dt for signal in signals}

    for bar in tqdm(bars_right, desc=f'generate snapshots of {bg.symbol}'):
        ct.update(bar)

        for signal in signals:
            html_path = os.path.join(home_path, signal.key)
            os.makedirs(html_path, exist_ok=True)
            if bar.dt - last_dt[signal.key] > timedelta(days=5) and signal.is_match(ct.s):
                file_html = f"{bar.symbol}_{signal.key}_{ct.s[signal.key]}_{bar.dt.strftime('%Y%m%d_%H%M')}.html"
                file_html = os.path.join(html_path, file_html)
                print(file_html)
                ct.take_snapshot(file_html)
                last_dt[signal.key] = bar.dt


def max_draw_down(n1b: List):
    """最大回撤

    参考：https://blog.csdn.net/weixin_38997425/article/details/82915386

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 最大回撤起止位置和最大回撤
    """
    curve = np.cumsum(n1b)
    curve += 10000
    # 获取结束位置
    i = np.argmax((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve))
    if i == 0:
        return 0, 0, 0

    # 获取开始位置
    j = np.argmax(curve[:i])
    mdd = int((curve[j] - curve[i]) / curve[j] * 10000) / 10000
    return j, i, mdd


def turn_over_rate(df_holds: pd.DataFrame) -> [pd.DataFrame, float]:
    """计算持仓明细对应的组合换手率

    :param df_holds: 每个交易日的持仓明细
    :return: 组合换手率
    """
    trade_dates = sorted(df_holds['成分日期'].unique().tolist())
    daily_holds = {date: dfg for date, dfg in df_holds.groupby('成分日期')}

    turns = []
    for date_i, date in tqdm(enumerate(trade_dates), desc='turn_over_rate'):
        if date_i == 0:
            turns.append({'date': date, 'change': 1})
            continue

        dfg = daily_holds[date]
        dfg_last = daily_holds[trade_dates[date_i-1]]
        com_symbols = list(set(dfg['证券代码'].to_list()).intersection(dfg_last['证券代码'].to_list()))

        dfg_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg.iterrows()}
        dfg_last_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg_last.iterrows()}

        change = 0
        change += sum([abs(dfg_pos[symbol] - dfg_last_pos[symbol]) for symbol in com_symbols])
        change += sum([v for symbol, v in dfg_pos.items() if symbol not in com_symbols])
        change += sum([v for symbol, v in dfg_last_pos.items() if symbol not in com_symbols])
        turns.append({'date': date, 'change': change})

    df_turns = pd.DataFrame(turns)
    return df_turns, round(df_turns.change.sum() / 2, 4)


def compound_returns(n1b: List):
    """复利收益计算

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 累计复利收益，逐个结算周期的复利收益
    """
    v = 10000
    detail = []
    for n in n1b:
        v = v * (1 + n / 10000)
        detail.append(v-10000)
    return v-10000, detail

