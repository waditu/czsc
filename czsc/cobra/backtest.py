# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/26 23:18
"""
import traceback
import pandas as pd
from typing import List, Callable, Tuple
from tqdm import tqdm

from ..objects import RawBar, Freq, Signal, Factor, Event, Freq, Operate
from ..signals import get_default_signals
from ..analyze import CzscTrader, KlineGenerator


def generate_signals(f1_raw_bars: List[RawBar],
                     init_count: int = 50000,
                     get_signals: Callable = get_default_signals) -> List[dict]:
    """输入1分钟K线，生成信号列表

    :param init_count: 用于初始化 kg 的1分钟K线数量，默认值为 50000
    :param f1_raw_bars: 1分钟K线列表，按时间升序
    :param get_signals: 自定义的信号计算函数
    :return: 计算好的信号列表
    """
    symbol = f1_raw_bars[0].symbol
    assert f1_raw_bars[0].freq == Freq.F1 \
           and f1_raw_bars[2].dt > f1_raw_bars[1].dt > f1_raw_bars[0].dt \
           and f1_raw_bars[2].id > f1_raw_bars[1].id, "f1_raw_bars 中的K线元素必须是1分钟周期，且按时间升序"
    assert len(f1_raw_bars) > init_count, "1分钟K线数量少于 init_count，无法进行信号计算"

    kg = KlineGenerator(max_count=5000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for bar in f1_raw_bars[:init_count]:
        kg.update(bar)

    ct = CzscTrader(kg, get_signals, events=[])
    signals = []
    for bar in tqdm(f1_raw_bars[init_count:], desc=f"generate signals of {symbol}"):
        try:
            ct.check_operate(bar)
            res = dict(bar.__dict__)
            res.update(ct.s)
            signals.append(res)
        except:
            traceback.print_exc()
    return signals


def long_trade_estimator(pairs: List[dict]):
    """在仿真交易结果上评估交易策略的表现

    :param pairs: `long_trade_simulator` 方法返回的交易对列表
    :return: res 交易的评估结果

    结果样例如下：
        {'标的代码': '000001.XSHG',
         '交易次数': 196,
         '累计收益（%）': 20.02,
         '单笔收益（%）': 0.1,
         '平均持仓分钟': 153,
         '胜率（%）': 39.28,
         '累计盈亏比': 2.27,
         '单笔盈亏比': 2.54}
    """
    df = pd.DataFrame(pairs)

    x_round = lambda x: int(x * 100) / 100

    res = {
        '标的代码': pairs[0]['标的代码'],
        '交易次数': len(pairs),
        '累计收益（%）': x_round(df['盈亏（%）'].sum()),
        '单笔收益（%）': x_round(df['盈亏（%）'].mean()),
        '平均持仓分钟': int(df['持仓分钟'].mean()),
        '胜率（%）': int(len(df[df['盈亏（%）'] > 0]) / len(df) * 10000) / 100,
        '累计盈亏比': int(df[df['盈亏（%）'] > 0]['盈亏（%）'].sum() /
                     abs(df[df['盈亏（%）'] < 0]['盈亏（%）'].sum()) * 100) / 100,
        '单笔盈亏比': int(df[df['盈亏（%）'] > 0]['盈亏（%）'].mean() /
                     abs(df[df['盈亏（%）'] < 0]['盈亏（%）'].mean()) * 100) / 100,
    }

    return res


def long_trade_simulator(signals: List[dict],
                         long_open_event: Event,
                         long_exit_event: Event) -> Tuple[List[dict], dict]:
    """多头交易模拟

    :param signals: 信号列表，必须按时间升序
    :param long_open_event: 开多事件
    :param long_exit_event: 平多事件
    :return: 交易对，绩效
    """
    assert len(signals) > 1000 and signals[1]['dt'] > signals[0]['dt']

    trades = []
    cache = {'long_stop_price': -1, 'last_op': None}

    for signal in signals:
        if cache['last_op'] == Operate.LO:
            m, f = long_exit_event.is_match(signal)
            if m:
                trades.append({
                    "标的代码": signal['symbol'],
                    '平仓时间': signal['dt'].strftime("%Y-%m-%d"),
                    '平仓价格': signal['close'],
                    '平仓理由': f,
                    'eid': signal['id'],
                })
                cache['last_op'] = Operate.LE
        else:
            m, f = long_open_event.is_match(signal)
            if m:
                trades.append({
                    "标的代码": signal['symbol'],
                    '开仓时间': signal['dt'].strftime("%Y-%m-%d"),
                    '开仓价格': signal['close'],
                    '开仓理由': f,
                    'oid': signal['id'],
                })
                cache['last_op'] = Operate.LO

    if len(trades) % 2 != 0:
        trades = trades[:-1]

    pairs = []
    for i in range(0, len(trades), 2):
        o, e = dict(trades[i]), dict(trades[i + 1])
        o.update(e)
        o['持仓分钟'] = o['eid'] - o['oid']
        o['盈亏（%）'] = int((o['平仓价格'] - o['开仓价格']) / o['开仓价格'] * 10000) / 100
        pairs.append(o)

    pf = long_trade_estimator(pairs)
    pf['基准收益（%）'] = int((signals[-1]['close'] - signals[0]['open']) / signals[0]['open'] * 10000) / 100
    pf['开始时间'] = signals[0]['dt'].strftime("%Y-%m-%d %H:%M")
    pf['结束时间'] = signals[-1]['dt'].strftime("%Y-%m-%d %H:%M")
    return pairs, pf


def one_event_estimator(signals: List[dict], event: Event) -> Tuple[List[dict], dict]:
    """评估单个事件的表现

    :param signals: 信号列表，必须按时间升序
    :param event: 事件
    :return: 交易对，绩效
    """
    assert len(signals) > 1000 and signals[1]['dt'] > signals[0]['dt']

    trades = []
    cache = {'long_stop_price': -1, 'last_op': None}

    for signal in signals:
        m, f = event.is_match(signal)
        if cache['last_op'] != Operate.LO and m:
            trades.append({
                "标的代码": signal['symbol'],
                '开仓时间': signal['dt'].strftime("%Y-%m-%d"),
                '开仓价格': signal['close'],
                '开仓理由': f,
                'oid': signal['id'],
            })
            cache['last_op'] = Operate.LO

        if cache['last_op'] == Operate.LO and not m:
            trades.append({
                "标的代码": signal['symbol'],
                '平仓时间': signal['dt'].strftime("%Y-%m-%d"),
                '平仓价格': signal['close'],
                '平仓理由': "事件空白",
                'eid': signal['id'],
            })
            cache['last_op'] = Operate.LE

    if len(trades) % 2 != 0:
        trades = trades[:-1]

    pairs = []
    for i in range(0, len(trades), 2):
        o, e = dict(trades[i]), dict(trades[i + 1])
        o.update(e)
        o['持仓分钟'] = o['eid'] - o['oid']
        o['盈亏（%）'] = int((o['平仓价格'] - o['开仓价格']) / o['开仓价格'] * 10000) / 100
        pairs.append(o)

    pf = long_trade_estimator(pairs)
    pf['基准收益（%）'] = int((signals[-1]['close'] - signals[0]['open']) / signals[0]['open'] * 10000) / 100
    pf['开始时间'] = signals[0]['dt'].strftime("%Y-%m-%d %H:%M")
    pf['结束时间'] = signals[-1]['dt'].strftime("%Y-%m-%d %H:%M")
    return pairs, pf

