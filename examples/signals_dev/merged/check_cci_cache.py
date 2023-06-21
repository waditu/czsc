# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/15 12:54
describe: 检查CCI增量更新带来的影响
"""
import sys
sys.path.insert(0, '../..')
import czsc
czsc.welcome()
import talib as ta
from test.test_analyze import read_1min

bars = read_1min()
signals_config = [{'name': "czsc.signals.tas_cci_base_V230402", 'freq': '1分钟', 'di': 1, 'timeperiod': 20}]
df = czsc.generate_czsc_signals(bars, signals_config=signals_config, signals_module_name='czsc.signals', df=True)
df['cci'] = ta.CCI(df.high, df.low, df.close, timeperiod=20)
# parse cache
df['cache_cci'] = df['cache'].apply(lambda x: x['CCI20'])

df = df.tail(10000)
print('CCI 差异', (df['cci'] - df['cache_cci']).abs().sum())

