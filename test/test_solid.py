# coding: utf-8
import sys
from functools import lru_cache
from cobra.data.kline import get_klines
sys.path.insert(0, r'C:\git_repo\zengbin93\chan')
sys.path.insert(0, r'C:\git_repo\zengbin93\cobra')

import chan
from chan import KlineAnalyze, SolidAnalyze


def test_solid_analyze():
    ts_code = "300033.SZ"
    klines = get_klines(ts_code, end_date='2020-04-03 14:00:00', asset='E', freqs='1min,5min,30min,D')

    for k, v in klines.items():
        print(k, v.tail(5), '\n\n')

    sa = SolidAnalyze(klines)

    for func in [sa.is_first_buy, sa.is_first_sell, sa.is_second_buy, sa.is_second_sell,
                 sa.is_third_buy, sa.is_third_sell, sa.is_xd_buy, sa.is_xd_sell]:
        for freq in ['1分钟', '5分钟', '30分钟']:
            b, detail = func(freq, tolerance=0.1)
            if b:
                print(detail)



