# coding: utf-8

import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import pandas as pd
import czsc
from czsc.analyze import KlineAnalyze, find_zs

warnings.warn("czsc version is {}".format(czsc.__version__))

cur_path = os.path.split(os.path.realpath(__file__))[0]
# cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline1 = kline.iloc[:2000]
kline2 = kline.iloc[2000:]
ka = KlineAnalyze(kline1, name="日线", max_raw_len=2000, verbose=True)

def test_update():
    for _, row in kline2.iterrows():
        ka.update(row.to_dict())
        assert ka.kline_raw[-1]['dt'] == row['dt']

def test_update_ta():
    ma_x1 = dict(ka.ma[-1])
    macd_x1 = dict(ka.macd[-1])
    ka.update(kline.iloc[-1].to_dict())
    ma_x2 = dict(ka.ma[-1])
    macd_x2 = dict(ka.macd[-1])
    assert ma_x1['dt'] == ma_x2['dt']
    assert [round(x, 2) for x in ma_x1.values() if isinstance(x, float)] == \
           [round(x, 2) for x in ma_x2.values() if isinstance(x, float)]

    assert macd_x1['dt'] == macd_x2['dt']
    assert [round(x, 2) for x in macd_x1.values() if isinstance(x, float)] == \
           [round(x, 2) for x in macd_x2.values() if isinstance(x, float)]


def test_kline_analyze():
    # 测试绘图
    file_img = "kline.png"
    ka.to_image(file_img, max_k_count=5000)
    assert os.path.exists(file_img)
    os.remove(file_img)

    # file_html = "kline.html"
    # ka.to_html(file_html)
    # assert os.path.exists(file_html)
    # os.remove(file_html)

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


def test_bei_chi():
    bi1 = {"start_dt": ka.bi_list[-11]['dt'], "end_dt": ka.bi_list[-10]['dt'], "direction": "down"}
    bi2 = {"start_dt": ka.bi_list[-13]['dt'], "end_dt": ka.bi_list[-12]['dt'], "direction": "down"}
    assert ka.is_bei_chi(bi1, bi2, mode="bi", adjust=0.9)

    xd1 = {"start_dt": ka.xd_list[-4]['dt'], "end_dt": ka.xd_list[-3]['dt'], "direction": "down"}
    xd2 = {"start_dt": ka.xd_list[-6]['dt'], "end_dt": ka.xd_list[-5]['dt'], "direction": "down"}
    assert ka.is_bei_chi(xd1, xd2, mode='xd', adjust=0.9)


def test_find_zs():
    bi_zs = find_zs(ka.bi_list)
    xd_zs = find_zs(ka.xd_list)
