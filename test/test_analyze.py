# coding: utf-8

import sys
import warnings
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import pandas as pd
import czsc
from czsc.analyze import KlineAnalyze

warnings.warn(f"czsc version is {czsc.__version__}")

cur_path = os.path.split(os.path.realpath(__file__))[0]
file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)


def test_kline_analyze():
    ka = KlineAnalyze(kline, name="日线")

    # 测试绘图
    file_img = "kline.png"
    ka.to_image(file_img, max_k_count=5000)
    assert os.path.exists(file_img)
    os.remove(file_img)

    file_html = "kline.html"
    ka.to_html(file_html)
    assert os.path.exists(file_html)
    os.remove(file_html)

    # 测试分型识别结果
    assert ka.fx_list[-1]['fx_mark'] == 'g' and ka.fx_list[-1]['fx'] == 3456.97
    assert ka.fx_list[-5]['fx_mark'] == 'g' and ka.fx_list[-5]['fx'] == 2983.44

    # 测试笔识别结果
    assert ka.bi_list[-1]['fx_mark'] == 'g' and ka.bi_list[-1]['bi'] == 3456.97
    assert ka.bi_list[-4]['fx_mark'] == 'd' and ka.bi_list[-4]['bi'] == 2646.8

    # 测试线段识别结果
    assert ka.xd_list[-2]['fx_mark'] == 'g' and ka.xd_list[-2]['xd'] == 3288.45
    assert ka.xd_list[-3]['fx_mark'] == 'd' and ka.xd_list[-3]['xd'] == 2440.91

    # 测试增量更新
    ka_raw_len = len(ka.kline_raw)
    for x in [2890, 2910, 2783, 3120]:
        k = dict(ka.kline_raw[-1])
        k['close'] = x
        ka.update(k)
        assert len(ka.kline_raw) == ka_raw_len
        assert ka.kline_raw[-1]['close'] == x

