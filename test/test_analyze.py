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

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline1 = kline.iloc[:2000]
kline2 = kline.iloc[2000:]
ka = KlineAnalyze(kline1, name="日线", max_raw_len=2000, verbose=True)


def test_get_sub_section():
    sub_kn = ka.get_sub_section(ka.fx_list[-2]['dt'], ka.fx_list[-1]['dt'], mode='kn', is_last=True)
    assert sub_kn[0]['dt'] == ka.fx_list[-2]['dt'] and sub_kn[-1]['dt'] == ka.fx_list[-1]['dt']

    sub_fx = ka.get_sub_section(ka.bi_list[-2]['dt'], ka.bi_list[-1]['dt'], mode='fx', is_last=True)
    assert sub_fx[0]['dt'] == ka.bi_list[-2]['dt'] and sub_fx[-1]['dt'] == ka.bi_list[-1]['dt']

    sub_bi = ka.get_sub_section(ka.xd_list[-2]['dt'], ka.xd_list[-1]['dt'], mode='bi', is_last=True)
    assert sub_bi[0]['dt'] == ka.xd_list[-2]['dt'] and sub_bi[-1]['dt'] == ka.xd_list[-1]['dt']

    sub_xd = ka.get_sub_section(ka.xd_list[-10]['dt'], ka.xd_list[-1]['dt'], mode='xd', is_last=True)
    assert sub_xd[0]['dt'] == ka.xd_list[-10]['dt'] and sub_xd[-1]['dt'] == ka.xd_list[-1]['dt']


def test_kline_analyze():
    # 测试绘图
    file_img = "kline.png"
    ka.to_image(file_img, max_k_count=5000)
    assert os.path.exists(file_img)

    for _, row in kline2.iterrows():
        ka.update(row.to_dict())
        assert ka.kline_raw[-1]['dt'] == row['dt']

    # 测试分型识别结果
    assert ka.fx_list[-1]['fx_mark'] == 'g'
    assert ka.fx_list[-5]['fx_mark'] == 'g'

    # 测试笔识别结果
    assert ka.bi_list[-1]['fx_mark'] == 'g'
    assert ka.bi_list[-4]['fx_mark'] == 'd'

    # 测试线段识别结果
    assert ka.xd_list[-2]['fx_mark'] == 'g'
    assert ka.xd_list[-3]['fx_mark'] == 'd'

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
    x1 = ka.is_bei_chi(bi1, bi2, mode="bi", adjust=0.9)

    xd1 = {"start_dt": ka.xd_list[-4]['dt'], "end_dt": ka.xd_list[-3]['dt'], "direction": "down"}
    xd2 = {"start_dt": ka.xd_list[-6]['dt'], "end_dt": ka.xd_list[-5]['dt'], "direction": "down"}
    x2 = ka.is_bei_chi(xd1, xd2, mode='xd', adjust=0.9)
    print('背驰计算结果：{}，{}'.format(x1, x2))


def test_update_ta():
    ka = KlineAnalyze(kline, name="日线", max_raw_len=2000, verbose=False)
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


def test_find_zs():
    bi_zs = find_zs(ka.bi_list)
    xd_zs = find_zs(ka.xd_list)

    # 造数测试
    points = [
        {"dt": 0, "fx_mark": "d", "xd": 8},
        {"dt": 1, "fx_mark": "g", "xd": 10},
        {"dt": 2, "fx_mark": "d", "xd": 9},
        {"dt": 3, "fx_mark": "g", "xd": 11},
        {"dt": 4, "fx_mark": "d", "xd": 10.5},
        {"dt": 5, "fx_mark": "g", "xd": 12},
        {"dt": 6, "fx_mark": "d", "xd": 11.1},

        {"dt": 7, "fx_mark": "g", "xd": 14},
        {"dt": 8, "fx_mark": "d", "xd": 13},
        {"dt": 9, "fx_mark": "g", "xd": 13.8},
        {"dt": 10, "fx_mark": "d", "xd": 12.9},
        {"dt": 11, "fx_mark": "g", "xd": 14.5},
        {"dt": 12, "fx_mark": "d", "xd": 13.2},
        {"dt": 13, "fx_mark": "g", "xd": 15},
        {"dt": 14, "fx_mark": "d", "xd": 14.3},

        {"dt": 15, "fx_mark": "g", "xd": 16.2},
        {"dt": 16, "fx_mark": "d", "xd": 15.3},
        {"dt": 17, "fx_mark": "g", "xd": 17.6},
        {"dt": 18, "fx_mark": "d", "xd": 15.9},
        {"dt": 19, "fx_mark": "g", "xd": 18.2},
        {"dt": 20, "fx_mark": "d", "xd": 16.8},
        {"dt": 21, "fx_mark": "g", "xd": 17.8},
        {"dt": 22, "fx_mark": "d", "xd": 16.9},
        {"dt": 23, "fx_mark": "g", "xd": 18.1},
    ]
    zss = find_zs(points[:8])
    assert len(zss) == 1

    zss = find_zs(points[:15])
    assert len(zss) == 2

    zss = find_zs(points)
    assert len(zss) == 3 and zss[0]['ZG'] < zss[1]['ZD'] and zss[1]['ZG'] < zss[2]['ZD']

    # 获取用于比较趋势背驰的两端
    fd1 = [x for x in points if x['dt'] >= zss[2]['end_point']['dt']]
    fd2 = [x for x in points if zss[2]['start_point']['dt'] > x['dt'] >= zss[1]['end_point']['dt']]
    fd3 = [x for x in points if zss[1]['start_point']['dt'] > x['dt'] >= zss[0]['end_point']['dt']]
    fd4 = [x for x in points if x['dt'] <= zss[0]['start_point']['dt']]
    assert fd1[0]['fx_mark'] == fd2[0]['fx_mark'] == fd3[0]['fx_mark'] == fd4[0]['fx_mark'] == 'd'
    assert fd1[-1]['fx_mark'] == fd2[-1]['fx_mark'] == fd3[-1]['fx_mark'] == fd4[-1]['fx_mark'] == 'g'


