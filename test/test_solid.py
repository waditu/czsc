# coding: utf-8
import sys
import warnings
from cobra.data.kline import get_klines
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import czsc
from czsc.solid import SolidAnalyze, is_in_tolerance
warnings.warn(f"czsc version is {czsc.__version__}")


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

    for name in sa.bs_func.keys():
        for freq in ['1分钟', '5分钟', '30分钟']:
            detail = sa.check_bs(freq, name, pf=False, tolerance=0.03)
            print(detail, "\n\n")



