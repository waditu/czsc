# coding: utf-8

import unittest
from chan.a import get_kline
import chan.utils as u


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.kline = get_kline(ts_code='600977.SH', start_date='20190501', end_date='20190725', freq='5min')

    def test_utils(self):
        kline_new = u.preprocess(self.kline)
        self.assertTrue(len(kline_new) < len(self.kline))

        kline_bi = u.find_bi(kline_new)
        self.assertTrue("bi_mark" in kline_bi.columns)

        kline_xd = u.find_xd(kline_bi)
        self.assertTrue("xd_mark" in kline_xd.columns)

        kline_macd = u.macd(kline_xd)
        self.assertTrue("macd" in kline_macd.columns)

        kline_boll = u.boll(kline_macd)
        self.assertTrue("boll-top" in kline_boll.columns)


if __name__ == "__main__":
    unittest.main()


