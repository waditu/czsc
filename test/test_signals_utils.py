# coding: utf-8
import warnings
import os
import numpy as np
import pandas as pd
import czsc
from czsc.signals.utils import down_cross_count, kdj_gold_cross, kdj_dead_cross, return_to_label
from czsc.objects import RawBar
from czsc.enum import Freq
from czsc import CZSC
from czsc.signals.utils import is_bis_down, is_bis_up, get_zs_seq
from test.test_analyze import read_daily
warnings.warn(f"czsc version is {czsc.__version__}_{czsc.__date__}")

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_return_to_label():
    assert return_to_label(100, th=99) == "超强"
    assert return_to_label(100, th=101) == "强势"
    assert return_to_label(-100, th=101) == "弱势"
    assert return_to_label(-110, th=101) == "超弱"


def test_kdj_cross():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
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


def test_bis_direction():
    bars = read_daily()
    c = CZSC(bars)
    assert is_bis_up(c.bi_list[-3:])
    assert not is_bis_down(c.bi_list[-3:])
    assert not is_bis_up(c.bi_list[-4:-1])
    assert is_bis_down(c.bi_list[-10:-5])


def test_get_zs_seq():
    bars = read_daily()
    c = CZSC(bars)
    zs_seq = get_zs_seq(c.bi_list)
    assert len(zs_seq) == 7
    assert len(zs_seq[-1].bis) == 20

