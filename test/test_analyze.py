# coding: utf-8
import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import pandas as pd
from czsc.analyze import KlineAnalyze
from czsc.signals import find_zs

cur_path = os.path.split(os.path.realpath(__file__))[0]

def test_ka_update():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    kline1 = kline.iloc[:2000]
    kline2 = kline.iloc[2000:]

    ka1 = KlineAnalyze(kline, name="日线", max_count=1000, use_xd=True, verbose=False)
    ka2 = KlineAnalyze(kline1, name="日线", max_count=1000, use_xd=True, verbose=False)

    for _, row in kline2.iterrows():
        ka2.update(row.to_dict())

    assert ka1.kline_new[-1]['dt'] == ka2.kline_new[-1]['dt']
    assert ka1.fx_list[-1]['dt'] == ka2.fx_list[-1]['dt']
    assert ka1.bi_list[-1]['dt'] == ka2.bi_list[-1]['dt']
    assert ka1.xd_list[-1]['dt'] == ka2.xd_list[-1]['dt']

    ka3 = KlineAnalyze(kline, name="日线", max_count=1000, use_xd=False, verbose=False)
    assert ka3.kline_new[-1]['dt'] == ka2.kline_new[-1]['dt']
    assert ka3.fx_list[-1]['dt'] == ka2.fx_list[-1]['dt']
    assert ka3.bi_list[-1]['dt'] == ka2.bi_list[-1]['dt']
    assert not ka3.xd_list

def test_calculate_power():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    ka = KlineAnalyze(kline, name="日线", max_count=1000, use_xd=True, verbose=False)

    # 测试 macd 力度
    last_xd_power = ka.calculate_macd_power(start_dt=ka.xd_list[-2]['dt'], end_dt=ka.xd_list[-1]['dt'],
                                            mode='xd', direction="up" if ka.xd_list[-1]['fx_mark'] == 'g' else "down")

    last_bi_power = ka.calculate_macd_power(start_dt=ka.bi_list[-2]['dt'], end_dt=ka.bi_list[-1]['dt'], mode='bi')

    assert int(last_xd_power) == 389
    assert int(last_bi_power) == 300

    # 测试 vol 力度
    last_xd_power = ka.calculate_vol_power(start_dt=ka.xd_list[-2]['dt'], end_dt=ka.xd_list[-1]['dt'])
    last_bi_power = ka.calculate_vol_power(start_dt=ka.bi_list[-2]['dt'], end_dt=ka.bi_list[-1]['dt'])

    assert int(last_xd_power) == 13329239053
    assert int(last_bi_power) == 9291793337

def test_kline_analyze():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    ka = KlineAnalyze(kline, name="日线", max_count=1000, use_xd=True, verbose=False)

    # 测试绘图
    file_img = "kline.png"
    ka.to_image(file_img, max_k_count=5000)
    assert os.path.exists(file_img)

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
    for x in [2890, 2910, 2783, 3120]:
        k = dict(ka.kline_raw[-1])
        k['close'] = x
        ka.update(k)
        assert ka.kline_raw[-1]['close'] == x

def test_update_ta():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    ka = KlineAnalyze(kline, name="日线", max_count=1000, use_xd=True, verbose=False, use_ta=True)

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



