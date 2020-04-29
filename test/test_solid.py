# coding: utf-8
import sys
from cobra.data.kline import get_klines
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import chan
from chan.solid import SolidAnalyze, nested_intervals, is_in_tolerance
print(chan.__version__)


def test_in_tolerance():
    assert not is_in_tolerance(10, 10.31, tolerance=0.03)
    assert not is_in_tolerance(10, 9.61, tolerance=0.03)
    assert not is_in_tolerance(10, 9, tolerance=0.03)
    assert is_in_tolerance(10, 10.3, tolerance=0.03)
    assert is_in_tolerance(10, 10.15, tolerance=0.03)
    assert is_in_tolerance(10, 9.8, tolerance=0.03)


def test_solid_analyze():
    ts_code = "000001.SH"
    klines = get_klines(ts_code, end_date='2020-04-03 14:00:00', asset='I', freqs='1min,5min,30min,D')
    sa = SolidAnalyze(klines)

    ka = sa.kas['30分钟']
    ka1 = sa.kas['日线']
    ka2 = sa.kas['5分钟']
    print(nested_intervals(ka, ka1, ka2))

    # for func in [sa.is_first_buy, sa.is_first_sell, sa.is_second_buy, sa.is_second_sell,
    #              sa.is_third_buy, sa.is_third_sell, sa.is_xd_buy, sa.is_xd_sell]:
    #     for freq in ['1分钟', '5分钟', '30分钟']:
    #         b, detail = func(freq, tolerance=0.1)
    #         if b:
    #             print(detail)



