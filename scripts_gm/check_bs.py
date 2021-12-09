# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/28 22:11
describe: 使用掘金的数据，查看任意时刻的标的状态，精确到分钟
"""

from src.utils.bt import GmCzscTrader
from czsc.signals.signals import get_default_signals


if __name__ == '__main__':
    get_signals = get_default_signals

    # ct = GmCzscTrader("SZSE.300511", end_dt='2021-07-15 14:38:00+08:00', get_signals=get_signals)
    ct = GmCzscTrader("SZSE.300511", get_signals=get_signals)
    ct.open_in_browser()

