# coding: utf-8
import sys
import warnings
import os
import numpy as np
import pandas as pd
from copy import deepcopy

import czsc
from czsc.cobra.utils import down_cross_count, kdj_gold_cross, kdj_dead_cross
from czsc.cobra.utils import drop_duplicates_by_window
from czsc.objects import RawBar
from czsc.enum import Freq

warnings.warn(f"czsc version is {czsc.__version__}_{czsc.__date__}")

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_kdj_cross():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    # bars = kline.to_dict("records")
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for i, row in kline.iterrows()]

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


def test_drop_duplicates():
    seq1 = [1, 2, 3, 3, 2, 4, 5, 6, 8, 1]
    seq1_ = drop_duplicates_by_window(seq1, -1, window_size=5)
    assert seq1_[3] == -1
    assert seq1_[4] == -1

    seq2 = ['x1', 'x1', 'x2', 'x3', 'x4', 'x3', 'x2', 'x5', 'x6']
    seq2_ = drop_duplicates_by_window(deepcopy(seq2), 'other', window_size=5)
    assert seq2_[1] == seq2_[5] == seq2_[6] == 'other'
    seq2_ = drop_duplicates_by_window(deepcopy(seq2), 'other', window_size=3)
    assert seq2_[1] == seq2_[5] == 'other'

    seq3 = [0.1, 1.2, 2.3, 3.2, 1.2, 2.5, 0.1, 2.3]
    seq3_ = drop_duplicates_by_window(deepcopy(seq3), -0.1, window_size=5)
    assert seq3_[4] == -0.1
    seq3_ = drop_duplicates_by_window(deepcopy(seq3), -0.1, window_size=10)
    assert seq3_[4] == seq3_[6] == seq3_[7] == -0.1

    # 长序列性能：500 ms ± 3.14 ms per loop (mean ± std. dev. of 10 runs, 1 loop each)
    # seq = list(range(2000000))
    # %timeit -r 10 seq_ = drop_duplicates_by_window(seq, -1, window_size=5)
