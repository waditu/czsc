# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:26
describe: 使用掘金数据验证买卖点
"""
# from czsc.gm_utils import trader_tactic_snapshot
# from czsc.strategies import trader_strategy_a as strategy
#
# if __name__ == '__main__':
#     _symbol = "SZSE.300669"
#     ct = trader_tactic_snapshot(_symbol, end_dt="2022-03-18 13:15", strategy=strategy)

import numpy as np
from czsc.gm_utils import trader_tactic_snapshot
from czsc.strategies import trader_strategy_a as strategy
from czsc.signals.utils import check_cross_info
try:
    import talib as ta
except:
    from czsc.utils import ta


if __name__ == '__main__':
    _symbol = "SHSE.000001"
    ct = trader_tactic_snapshot(_symbol, end_dt="2022-07-03 15:15", strategy=strategy)
    close = np.array([x.close for x in ct.kas['60分钟'].bars_raw])
    fast = ta.SMA(close, timeperiod=5)
    slow = ta.SMA(close, timeperiod=13)
    cross = check_cross_info(fast.round(2), slow.round(2))



