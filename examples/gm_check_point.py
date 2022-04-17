# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from examples import tactics
from examples.gm_utils import *


def trader_tactic_snapshot(symbol, tactic: dict, end_dt=None, file_html=None, adjust=ADJUST_PREV, max_count=1000):
    """使用掘金的数据对任意标的、任意时刻的状态进行策略快照

    :param symbol: 交易标的
    :param tactic: 择时交易策略
    :param end_dt: 结束时间，精确到分钟
    :param file_html: 结果文件
    :param adjust: 复权类型
    :param max_count: 最大K线数量
    :return: trader
    """
    base_freq = tactic['base_freq']
    freqs = tactic['freqs']
    get_signals = tactic['get_signals']

    long_states_pos = tactic.get('long_states_pos', None)
    long_events = tactic.get('long_events', None)
    long_min_interval = tactic.get('long_min_interval', None)

    short_states_pos = tactic.get('short_states_pos', None)
    short_events = tactic.get('short_events', None)
    short_min_interval = tactic.get('short_min_interval', None)

    if not end_dt:
        end_dt = datetime.now().strftime(dt_fmt)

    if long_states_pos:
        long_pos = PositionLong(symbol, T0=False,
                                long_min_interval=long_min_interval,
                                hold_long_a=long_states_pos['hold_long_a'],
                                hold_long_b=long_states_pos['hold_long_b'],
                                hold_long_c=long_states_pos['hold_long_c'])
    else:
        long_pos = None

    if short_states_pos:
        short_pos = PositionShort(symbol, T0=False,
                                  short_min_interval=short_min_interval,
                                  hold_short_a=short_states_pos['hold_short_a'],
                                  hold_short_b=short_states_pos['hold_short_b'],
                                  hold_short_c=short_states_pos['hold_short_c'])
    else:
        short_pos = None

    bg, data = get_init_bg(symbol, end_dt, base_freq=base_freq, freqs=freqs, max_count=max_count, adjust=adjust)
    trader = GmCzscTrader(bg, get_signals, long_events, long_pos, short_events, short_pos,
                          signals_n=tactic.get('signals_n', 0))
    for bar in data:
        trader.update(bar)

    if file_html:
        trader.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        trader.open_in_browser()
    return trader


if __name__ == '__main__':
    # ct = gm_take_snapshot("SZSE.300669", end_dt="2022-03-20", file_html=None,
    #                       get_signals=tactics.trader_strategy_a()['get_signals'],
    #                       adjust=ADJUST_PREV, max_count=1000)

    ct = trader_tactic_snapshot("SZSE.300669", end_dt="2022-03-18 13:15", tactic=tactics.trader_strategy_a())


