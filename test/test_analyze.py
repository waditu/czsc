# coding: utf-8
import sys
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import chan
from chan import KlineAnalyze
from chan.analyze import is_bei_chi

print(chan.__version__)


def test_bei_chi():
    df = get_kline(ts_code="000001.SH", end_dt="2020-04-28 15:00:00", freq='D', asset='I')
    ka = KlineAnalyze(df)

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


def test_kline_analyze():
    df = get_kline(ts_code="300008.SZ", end_dt="2020-03-23 15:00:00", freq='30min', asset='E')
    ka = KlineAnalyze(df)

    # 测试识别结果
    assert ka.bi[-1]['fx_mark'] == 'g'
    assert ka.xd[-1]['fx_mark'] == 'g'

    # 测试背驰识别
    assert not ka.bi_bei_chi()
    assert not ka.xd_bei_chi()
    print(ka.zs[-2])


