# coding: utf-8
import os
import pandas as pd
from czsc.utils.kline_generator import KlineGeneratorBy1Min as KlineGenerator
from czsc.objects import RawBar


cur_path = os.path.split(os.path.realpath(__file__))[0]
# cur_path = r"D:\git_repo\offline\dealer\test\czsc"
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
kline = [RawBar(symbol=row['symbol'], open=row['open'], dt=row['dt'],
                close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
         for _, row in kline.iterrows()]


def test_kline_generator():
    # 验证指定级别
    kg = KlineGenerator(freqs=['周线', '日线', '30分钟', '5分钟', '1分钟'])
    for row in kline:
        kg.update(row)

    assert not kg.m60 and not kg.m15

    kg = KlineGenerator(max_count=2000, freqs=['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟'])
    for row in kline:
        kg.update(row)

    assert kg.m60 and kg.m15

    # 验证K线获取
    klines = kg.get_klines({'1分钟': 100, '5分钟': 100})
    for k, v in klines.items():
        assert len(v) == 100

    # 数量验证
    assert len(kg.m1) == 2000
    assert len(kg.m5) == len(kline) // 5
    assert len(kg.m15) == len(kline) // 15
    assert len(kg.m30) == len(kline) // 30
    assert len(kg.m60) == len(kline) // 60
    assert len(kg.D) == len(kline) // 240

    # 验证周线
    assert kg.W[-1].open == 3379.39
    assert kg.W[-1].close == 3361.3
    assert kg.W[-1].high == 3458.79
    assert kg.W[-1].low == 3345.75

    # 测试实盘连续输入
    for _ in range(5):
        kg.update(kline[-1])
        assert len(kg.m1) == 2000
        assert len(kg.m5) == len(kline) // 5
        assert len(kg.m30) == len(kline) // 30
        assert len(kg.D) == len(kline) // 240
        assert kg.W[-1].open == 3379.39
        assert kg.W[-1].close == 3361.3
        assert kg.W[-1].high == 3458.79
        assert kg.W[-1].low == 3345.75

