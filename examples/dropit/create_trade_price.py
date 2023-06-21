# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 14:37
describe: 在1分钟周期上计算可交易价格
"""
import os
import pandas as pd
from tqdm import tqdm
from typing import List, Union
from czsc.objects import RawBar
from czsc.connectors import qmt_connector as qmc
from czsc import cal_trade_price


def test_trade_price():
    # symbol = '000001.SZ'
    # parquet 和 feather 性能测试对比
    # 存储空间，parquet 少 30%以上
    # 读取速度，parquet 慢 10%左右
    symbols = qmc.get_symbols('train')
    results_path = r"D:\QMT投研\A股交易价_20170101_20230301"
    os.makedirs(results_path, exist_ok=True)
    for symbol in tqdm(symbols, desc='计算交易价'):
        try:
            bars = qmc.get_raw_bars(symbol, '1分钟', '20170101', '20230301')
            df = cal_trade_price(bars)
            df.to_parquet(os.path.join(results_path, f"{symbol}_price.parquet"))
            # df.to_feather(os.path.join(results_path, f"{symbol}_price.feather"))
        except:
            print(f"fail on {symbol}")
