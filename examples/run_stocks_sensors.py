# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:21
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from czsc.data.ts_cache import TsDataCache
from czsc.sensors.stocks import StrongStocksSensor

dc = TsDataCache(data_path=r'C:\ts_data', sdt='2015-01-01', edt='20211029')

sss = StrongStocksSensor(dc)

sss.process_one_day(trade_date='20211029')

