# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
from czsc.gms.gm_stocks import strategy_snapshot, gm_take_snapshot
from czsc.strategies import trader_strategy_a as strategy

if __name__ == '__main__':
    _symbol = "SHSE.000016"
    # 查看含策略交易信号的快照
    ct = strategy_snapshot(_symbol, end_dt="2022-07-27 13:15", strategy=strategy)

    # 仅查看分型、笔的程序化识别
    cts = gm_take_snapshot(_symbol, end_dt="2022-07-27 13:15", max_count=1000)
    cts.open_in_browser()




