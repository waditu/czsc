# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/26 15:06
describe: 测试绘图
"""
import os
import pandas as pd
from czsc import CZSC, KlineChart
from test.test_analyze import read_daily


def test_kline_chart():
    """测试K线图"""
    bars = read_daily()
    c = CZSC(bars, max_bi_num=50)

    df = pd.DataFrame(c.bars_raw)
    df['text'] = "测试"
    kline = KlineChart(n_rows=3)
    kline.add_kline(df, name="K线")
    kline.add_sma(df, ma_seq=(5, 10, 21), row=1, visible=True, line_width=1.2)
    kline.add_sma(df, ma_seq=(34, 55, 89, 144), row=1, visible=False, line_width=1.2)
    kline.add_vol(df, row=2)
    kline.add_macd(df, row=3)
    if len(c.bi_list) > 0:
        bi1 = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value} for x in c.bi_list]
        bi2 = [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx, "text": c.bi_list[-1].fx_b.mark.value}]
        bi = pd.DataFrame(bi1 + bi2)
        fx = pd.DataFrame([{'dt': x.dt, "fx": x.fx} for x in c.fx_list])
        kline.add_scatter_indicator(fx['dt'], fx['fx'], name="分型", row=1, line_width=2)
        kline.add_scatter_indicator(bi['dt'], bi['bi'], name="笔", text=bi['text'], row=1, line_width=2)
    # kline.open_in_browser()
    file_html = "kline_chart_test.html"
    kline.fig.write_html(file_html)
    assert os.path.exists(file_html)
    os.remove(file_html)
    assert not os.path.exists(file_html)
