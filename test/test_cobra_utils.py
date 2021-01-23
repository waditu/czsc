# coding: utf-8
import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import numpy as np
import pandas as pd
import czsc
from czsc.cobra.utils import down_cross_count, kdj_gold_cross, kdj_dead_cross

warnings.warn("czsc version is {}".format(czsc.__version__))

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_kdj_cross():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    bars = kline.to_dict("records")

    assert not kdj_gold_cross(kline, just=False)
    assert not kdj_gold_cross(bars, just=False)
    assert kdj_dead_cross(kline, just=False)
    assert kdj_dead_cross(bars, just=False)
    assert not kdj_dead_cross(kline, just=True)


def test_cross_count():
    x1 = [1, 1, 3, 4, 5, 12, 9, 8]
    x2 = [2, 2, 1, 5, 8, 9, 10, 10]
    assert down_cross_count(x1, x2) == 2
    assert down_cross_count(np.array(x1), np.array(x2)) == 2
    assert down_cross_count(x2, x1) == 2
    assert down_cross_count(np.array(x2), np.array(x1)) == 2





