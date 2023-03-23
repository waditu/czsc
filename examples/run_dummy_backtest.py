# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/23 19:23
describe: 使用 DummyBacktest 进行快速回测迭代式研究
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import czsc
from czsc.connectors import qmt_connector as qmc
from czsc.strategies import CzscStocksBeta


dummy = czsc.DummyBacktest(strategy=CzscStocksBeta, read_bars=qmc.get_raw_bars, sdt='20200101', edt='20230301',
                           signals_path=r'D:\QMT投研\CzscStocksBeta\signals',
                           results_path=r'D:\QMT投研\CzscStocksBeta\results_20200101_20230301')

# 查看某个品种的交易回放
dummy.replay('000001.SZ')

# 定义需要回测的品种，这里可以自定义
symbols = qmc.get_symbols('train')
dummy.execute(symbols, n_jobs=4)




