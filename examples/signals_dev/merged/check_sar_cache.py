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
signals_config = [{'name': "czsc.signals.tas_sar_base_V230425", 'freq': '1分钟', 'di': 1, 'max_overlap': 5}]
df = czsc.generate_czsc_signals(bars, signals_config=signals_config, signals_module_name='czsc.signals', df=True)
df['sar'] = ta.SAR(df.high, df.low)
# parse cache
df['cache_sar'] = df['cache'].apply(lambda x: x['SAR'])

df = df.tail(10000)
print('SAR 差异', (df['sar'] - df['cache_sar']).abs().sum())

