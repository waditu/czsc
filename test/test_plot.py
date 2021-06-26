# coding: utf-8
import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
import pandas as pd
import random
from czsc.utils import echarts_plot as plot
from czsc.analyze import CZSC, RawBar, Mark

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_heat_map():
    data = [{"x": "{}hour".format(i), "y": "{}day".format(j), "heat": random.randint(0, 50)}
            for i in range(24) for j in range(7)]
    x_label = ["{}hour".format(i) for i in range(24)]
    y_label = ["{}day".format(i) for i in range(7)]
    hm = plot.heat_map(data, x_label=x_label, y_label=y_label)
    hm.render()


def test_kline_pro():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    bars = [RawBar(symbol=row['symbol'], open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for _, row in kline.iterrows()]
    ka = CZSC(bars, freq="日线")

    # bs = []
    # for x in ka.bi_list:
    #     if x.fx_b.mark == Mark.D:
    #         mark = "buy"
    #     else:
    #         mark = "sell"
    #     bs.append({"dt": x.f, "mark": mark, mark: x.fx_b.fx})
    #
    # chart = plot.kline_pro(ka.bars_ubi, fx=ka.fx_list, bi=ka.bi_list, xd=ka.xd_list, bs=bs)
    # chart.render()

