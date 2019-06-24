# coding: utf-8

import unittest
from chan.a import get_kline
from chan.analyze import *


class TestAnalyze(unittest.TestCase):
    def test_analyze(self):
        kline = get_kline(ts_code='600122.SH', start_date='20190501', end_date='20190620', freq='5min')
        kline = preprocess(kline)
        kline = find_fx(kline)




