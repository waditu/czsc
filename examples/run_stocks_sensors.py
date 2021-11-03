# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:21
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import pandas as pd
from czsc.data.ts_cache import TsDataCache
from czsc.sensors.stocks import StrongStocksSensor

dc = TsDataCache(data_path=r'C:\ts_data', sdt='2019-01-01', edt='20211029')

if __name__ == '__main__':
    sss = StrongStocksSensor(dc)
    results = sss.validate(sdt='20200101', edt='20201231')

    # res = sss.process_one_day(trade_date='20211029')
    #
    # s = sss.get_share_hist_signals(ts_code='000001.SZ', trade_date=pd.to_datetime('20211029'))
    # n = sss.get_share_hist_returns(ts_code='000001.SZ', trade_date=pd.to_datetime('20211029'))
