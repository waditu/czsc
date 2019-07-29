# coding: utf-8

import unittest
from chan.a import get_kline
from chan.utils import preprocess, find_fx


class TestAnalyze(unittest.TestCase):
    def test_analyze(self):
        kline = get_kline(ts_code='600977.SH', start_date='20190501', end_date='20190725', freq='5min')
        kline_new = preprocess(kline)
        kline_fx = find_fx(kline_new)


