# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/6/7 22:09
describe: 使用 SignalAnalyzer 进行信号验证的示例
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import hashlib
from loguru import logger
from sklearn.model_selection import ParameterGrid
from czsc.connectors.research import get_raw_bars, get_symbols
from czsc import SignalAnalyzer

task_list = [
    # https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_accelerate_V221110.html
    {'name': ['czsc.signals.bar_accelerate_V221110'],
     'freq': ['30分钟', '60分钟', '日线', '周线'],
     'di': [1, 3], 'window': [13, 21, 34]},

    # https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_bpm_V230227.html
    {'name': ['czsc.signals.bar_bpm_V230227'],
     'freq': ['30分钟', '60分钟', '日线', '周线'],
     'di': [1, 5, 9], 'n': [10, 21, 34],
     'th': [500, 1000, 1500, 2000]},

    # https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_single_V230214.html
    {'name': ['czsc.signals.bar_single_V230214'],
     'freq': ['30分钟', '60分钟', '日线', '周线'],
     'di': [1, 2, 3, 4, 5], 't': [10, 15, 20]},
]

if __name__ == '__main__':
    name = '中证500成分股'
    symbols = get_symbols(name)
    for task in task_list:
        try:
            signals_config = list(ParameterGrid(task))
            sig_name = signals_config[0]['name'].split('.')[-1]
            md5 = hashlib.sha256((str(signals_config) + str(symbols)).encode('utf-8')).hexdigest()[:8].upper()
            sa = SignalAnalyzer(symbols, read_bars=get_raw_bars, signals_config=signals_config,
                                results_path=fr"D:\号验证结果\{name}#{sig_name}#{md5}")
            sa.execute(max_workers=25)
        except Exception as e:
            logger.error(e)
