# coding: utf-8

import sys
import warnings
from cobra.data.kline import get_kline
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import pandas as pd
import czsc
from czsc.analyze_v2 import KlineAnalyze, is_bei_chi, FX, BI, XD

warnings.warn(f"czsc version is {czsc.__version__}")

kline = get_kline(ts_code="000001.SH", end_dt="2020-07-16 15:00:00", freq='D', asset='I')
# ka = KlineAnalyze(kline, name="日线")
# print(ka)


def test_objects():
    if isinstance(kline, pd.DataFrame):
        columns = kline.columns.to_list()
        bars = [{k: v for k, v in zip(columns, row)} for row in kline.values]
    else:
        bars = kline

    # 测试分型序列更新过程
    fxs_raw = [FX()]
    for bar in bars:
        fx = fxs_raw[-1]
        assert not fx.is_end
        fx.update(bar)
        fxs_raw[-1] = fx
        if fx.is_end:
            new_fx = FX()
            for bar_ in fx.elements[-2:]:
                new_fx.update(bar_)
            fxs_raw.append(new_fx)

    fxs = [fxs_raw[0]]
    for fx in fxs_raw[1:]:
        last_fx = fxs[-1]
        if (fx.mark == "g" and fx.price >= last_fx.price) \
                or (fx.mark == "d" and fx.price <= last_fx.price):
            fxs.pop(-1)
        fxs.append(fx)


def test_kline_analyze():
    assert ka.bis[-1].mark == 'g'
    assert ka.xds[-2].mark == 'd'

    ka.to_html("kline.html")
    ka.to_image("kline.png")


def test_bei_chi():
    # 线段背驰
    zs1 = {"start_dt": ka.xds[-3].dt, "end_dt": ka.xds[-2].dt, "direction": "down"}
    zs2 = {"start_dt": ka.xds[-5].dt, "end_dt": ka.xds[-4].dt, "direction": "down"}
    assert is_bei_chi(ka, zs1, zs2, mode='xd', adjust=0.9)

    # 笔背驰
    zs1 = {"start_dt": '2019-05-17 15:00:00', "end_dt": '2019-05-27 15:00:00'}
    zs2 = {"start_dt": '2019-04-08 15:00:00', "end_dt": '2019-05-10 15:00:00'}
    assert is_bei_chi(ka, zs1, zs2, mode='bi', adjust=0.9)


