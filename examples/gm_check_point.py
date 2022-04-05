# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
from examples import tactics
from examples.gm_utils import *


if __name__ == '__main__':
    ct = gm_take_snapshot("SZSE.300669", end_dt="2022-03-20", file_html=None,
                          get_signals=tactics.trader_strategy_a()['get_signals'],
                          adjust=ADJUST_PREV, max_count=1000)

