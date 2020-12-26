# coding: utf-8
import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import pandas as pd
import czsc
from czsc.cobra.analyst import cal_nbar_income, cal_nbar_percentile

warnings.warn("czsc version is {}".format(czsc.__version__))

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"


def test_nbar():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    bars = kline.to_dict("records")

    i = 100
    n = 10
    k1 = bars[i]
    kn = bars[i+1: i+n+1]

    ni = cal_nbar_income(k1, kn, n)
    assert ni == 391.31

    np = cal_nbar_percentile(k1, kn, n)
    assert np == 87.06




