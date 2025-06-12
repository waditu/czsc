# coding: utf-8
import os
import pandas as pd
import random
from czsc.utils import echarts_plot as plot
from czsc.analyze import CZSC, RawBar
from czsc.enum import Freq

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_kline_pro():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'], # type: ignore
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'], amount=row['vol']*row['close'])
            for i, row in kline.iterrows()]
    ka = CZSC(bars)
    # ka.open_in_browser()
    file_html = 'czsc_render.html'
    chart = ka.to_echarts()
    chart.render(file_html)
    assert os.path.exists(file_html)
    os.remove(file_html)
