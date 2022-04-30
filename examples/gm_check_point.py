# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
from czsc.gm_utils import trader_tactic_snapshot
from examples import tactics


if __name__ == '__main__':
    ct = trader_tactic_snapshot("SZSE.300669", end_dt="2022-03-18 13:15", tactic=tactics.trader_strategy_a())


