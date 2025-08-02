# coding: utf-8
import os
import pandas as pd
import random
from czsc.utils import echarts_plot as plot
from czsc.analyze import CZSC, RawBar
from czsc.enum import Freq

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_kline_pro():
    from czsc import mock

    # 使用mock数据替代硬编码数据文件
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'], # type: ignore
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'], amount=row['vol']*row['close'])
            for i, row in df.iterrows()]
    ka = CZSC(bars)
    # ka.open_in_browser()
    file_html = 'czsc_render.html'
    chart = ka.to_echarts()
    chart.render(file_html)
    assert os.path.exists(file_html)
    os.remove(file_html)
