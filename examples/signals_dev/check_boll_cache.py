# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/15 12:54
describe: 检查ATR增量更新带来的影响
"""
import sys
sys.path.insert(0, '../..')
import czsc
czsc.welcome()
import talib as ta
from test.test_analyze import read_1min

bars = read_1min()
signals_config = [{'name': "czsc.signals.tas_boll_cc_V230312", 'freq': '1分钟', 'di': 1}]
df = czsc.generate_czsc_signals(bars, signals_config=signals_config, signals_module_name='czsc.signals', df=True)
df['u1'], df['m'], df['l1'] = ta.BBANDS(df.close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

# parse cache
df['cache_u1'] = df['cache'].apply(lambda x: x['BOLL20S20']['上轨'])
df['cache_m'] = df['cache'].apply(lambda x: x['BOLL20S20']['中线'])
df['cache_l1'] = df['cache'].apply(lambda x: x['BOLL20S20']['下轨'])

df = df.tail(10000)
print('u1 差异', (df['u1'] - df['cache_u1']).abs().sum())
print('m 差异', (df['m'] - df['cache_m']).abs().sum())
print('l1 差异', (df['l1'] - df['cache_l1']).abs().sum())
