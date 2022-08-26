# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
from czsc.gm_utils import trader_tactic_snapshot, gm_take_snapshot
from czsc.strategies import trader_strategy_a as strategy

if __name__ == '__main__':
    # _symbol = "SZSE.300669"
    # ct = trader_tactic_snapshot(_symbol, end_dt="2022-03-18 13:15", strategy=strategy)
    _symbol = "SHSE.000016"
    ct = trader_tactic_snapshot(_symbol, end_dt="2022-07-27 13:15", strategy=strategy)
    # ct = gm_take_snapshot('SHSE.000001')




