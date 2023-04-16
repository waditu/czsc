# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/15 12:54
describe: 检查MACD增量更新带来的影响
"""
import sys
sys.path.insert(0, '../..')
import czsc
czsc.welcome()
import talib as ta
from test.test_analyze import read_1min

bars = read_1min()
signals_config = [{'name': "czsc.signals.tas_macd_base_V230320", 'freq': '1分钟', 'di': 1}]
df = czsc.generate_czsc_signals(bars, signals_config=signals_config, signals_module_name='czsc.signals', df=True)
df['dif'], df['dea'], df['macd'] = ta.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
# parse cache
df['cache_macd'] = df['cache'].apply(lambda x: x['MACD12#26#9']['macd'])
df['cache_dif'] = df['cache'].apply(lambda x: x['MACD12#26#9']['dif'])
df['cache_dea'] = df['cache'].apply(lambda x: x['MACD12#26#9']['dea'])

df = df.tail(10000)
print('macd 差异', (df['macd'] - df['cache_macd']).abs().sum())
print('dif 差异', (df['dif'] - df['cache_dif']).abs().sum())
print('dea 差异', (df['dea'] - df['cache_dea']).abs().sum())

