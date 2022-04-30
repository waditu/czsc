# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/4/29 12:06
describe: 使用聚宽的数据对任意标的、任意时刻的状态进行策略快照
"""
from czsc.data.jq import get_init_bg
from czsc import create_advanced_trader
from examples import tactics


def trader_tactic_snapshot(symbol, tactic: dict, end_dt=None, file_html=None, fq=True, max_count=1000):
    """使用聚宽的数据对任意标的、任意时刻的状态进行策略快照

    :param symbol: 交易标的
    :param tactic: 择时交易策略
    :param end_dt: 结束时间，精确到分钟
    :param file_html: 结果文件
    :param fq: 是否复权
    :param max_count: 最大K线数量
    :return: trader
    """
    base_freq = tactic['base_freq']
    freqs = tactic['freqs']
    bg, data = get_init_bg(symbol, end_dt, base_freq=base_freq, freqs=freqs, max_count=max_count, fq=fq)
    trader = create_advanced_trader(bg, data, tactic)
    if file_html:
        trader.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        trader.open_in_browser()
    return trader


if __name__ == '__main__':
    ct = trader_tactic_snapshot("000001.XSHG", end_dt="20070427 15:15", tactic=tactics.trader_strategy_example())

