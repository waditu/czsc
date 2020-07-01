# coding: utf-8
import sys
import warnings
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import czsc
from czsc import KlineAnalyze
from czsc.analyze import is_bei_chi, find_zs

warnings.warn(f"czsc version is {czsc.__version__}")

df = get_kline(ts_code="000001.SH", end_dt="2020-04-28 15:00:00", freq='D', asset='I')
ka = KlineAnalyze(df, name="日线", bi_mode='old')
print(ka)


def test_kline_analyze():
    assert ka.bi[-1]['fx_mark'] == 'g'
    assert ka.xd[-1]['fx_mark'] == 'd'

    # 测试背驰识别
    assert ka.bi_bei_chi()
    assert ka.xd_bei_chi()
    print(ka.zs[-2])

    ka.to_html("kline.html")
    ka.to_image("kline.png")


def test_bei_chi():
    # 线段背驰
    zs1 = {"start_dt": '2018-07-26 15:00:00', "end_dt": '2018-10-19 15:00:00', "direction": "down"}
    zs2 = {"start_dt": '2018-01-29 15:00:00', "end_dt": '2018-07-06 15:00:00', "direction": "down"}
    assert is_bei_chi(ka, zs1, zs2, mode='xd', adjust=0.9)

    zs1 = {"start_dt": '2013-12-10 15:00:00', "end_dt": '2014-01-20 15:00:00', "direction": "down"}
    zs2 = {"start_dt": '2013-09-12 15:00:00', "end_dt": '2013-11-14 15:00:00', "direction": "down"}
    assert not is_bei_chi(ka, zs1, zs2, mode='xd', adjust=0.9)

    # 笔背驰
    zs1 = {"start_dt": '2019-05-17 15:00:00', "end_dt": '2019-06-10 15:00:00'}
    zs2 = {"start_dt": '2019-04-08 15:00:00', "end_dt": '2019-05-10 15:00:00'}
    assert is_bei_chi(ka, zs1, zs2, mode='bi', adjust=0.9)

    zs1 = {"start_dt": '2018-09-28 15:00:00', "end_dt": '2018-10-19 15:00:00'}
    zs2 = {"start_dt": '2018-08-28 15:00:00', "end_dt": '2018-09-12 15:00:00'}
    assert not is_bei_chi(ka, zs1, zs2, mode='bi', adjust=0.9)


def test_find_zs():
    assert ka.down_zs_number() == 2
    assert ka.up_zs_number() == 1
    xd_zs = find_zs(ka.xd)
    bi_zs = find_zs(ka.bi)

    assert xd_zs[-2]["ZD"] == 2850.71
    assert xd_zs[-2]["ZG"] == 3684.57

    assert xd_zs[-1]["ZD"] == 2691.02
    assert xd_zs[-1]["ZG"] == 2827.34

    assert bi_zs[-2]['ZD'] == 2987.77
    assert bi_zs[-2]['ZG'] == 3125.02

    assert bi_zs[-1]['ZD'] == 2838.38
    assert bi_zs[-1]['ZG'] == 2956.78

