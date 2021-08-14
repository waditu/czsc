# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/9 16:42
describe: 快速回测样例

快速回测二步走：
1）通过聚宽获取最近三年的1分钟数据，生成signals，signals可以重复使用
2）设定 long_open_event, long_exit_event 执行快速回测，查看回测结果
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
from collections import OrderedDict
from czsc import signals, CZSC
from czsc.data import jq
from czsc.objects import Signal, Factor, Event, Freq, Operate
from czsc.utils.io import read_pkl, save_pkl
from czsc.cobra.backtest import generate_signals, long_trade_simulator, one_event_estimator

# data_path = os.path.expanduser('~')
data_path = r"D:\research\jq_data\backtest"
os.makedirs(data_path, exist_ok=True)
symbol = '000001.XSHG'


def get_user_signals(c: CZSC) -> OrderedDict:
    """自定义在 CZSC 对象上计算哪些信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})

    s.update(signals.get_s_d0_bi(c))
    s.update(signals.get_s_three_k(c, 1))
    s.update(signals.get_s_di_bi(c, 1))
    s.update(signals.get_s_macd(c, 1))
    s.update(signals.get_s_k(c, 1))
    s.update(signals.get_s_bi_status(c))
    s.update(signals.get_s_three_bi(c, di=1))
    s.update(signals.get_s_base_xt(c, di=1))
    s.update(signals.get_s_like_bs(c, di=1))
    return s


# 通过聚宽获取最近三年的1分钟数据，生成signals，signals可以重复使用
file_signals = os.path.join(data_path, f'{symbol}_signals.pkl')
if os.path.exists(file_signals):
    signals = read_pkl(file_signals)
else:
    f1_raw_bars = jq.get_kline_period(symbol=symbol, freq='1min', start_date='20180801', end_date='20210801')
    signals = generate_signals(f1_raw_bars, init_count=50000, get_signals=get_user_signals)
    save_pkl(signals, file_signals)


def evaluate_event():
    """对单个事件进行表现评估"""
    event = Event(name="单事件", operate=Operate.LO, factors=[
        Factor(name="60分钟DIF多头向上", signals_all=[
            Signal("60分钟_DIF_状态_多头_向上_任意_0"),
        ]),
    ])

    pairs1, pf1 = one_event_estimator(signals, event)

    event = Event(name="单事件", operate=Operate.LO, factors=[
        Factor(name="60分钟DIF空头向下", signals_all=[
            Signal("60分钟_DIF_状态_空头_向下_任意_0"),
        ]),
    ])

    pairs2, pf2 = one_event_estimator(signals, event)


def evaluate_trade():
    """设定 long_open_event, long_exit_event 执行快速回测，查看回测结果"""
    long_open_event = Event(name='开多', operate=Operate.LO, factors=[
        Factor(name="15分钟一买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
        Factor(name="15分钟二买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
        Factor(name="15分钟三买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
    ])
    long_exit_event = Event(name="一卖", operate=Operate.LE, factors=[
        Factor(name="15分钟一卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
        Factor(name="15分钟二卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
        Factor(name="15分钟三卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三卖_任意_任意_0")])
    ])

    pairs, pf = long_trade_simulator(signals, long_open_event, long_exit_event)


if __name__ == '__main__':
    evaluate_event()
    evaluate_trade()
