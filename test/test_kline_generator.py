# coding: utf-8
import os
import pandas as pd
from tqdm import tqdm

from czsc.objects import RawBar, Freq
from czsc.utils.kline_generator import KlineGenerator, KlineGeneratorD, freq_end_time
from test.test_analyze import read_1min

cur_path = os.path.split(os.path.realpath(__file__))[0]
kline = read_1min()


def test_freq_end_time():
    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.F1) == pd.to_datetime("2021-11-11 09:43")
    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.F5) == pd.to_datetime("2021-11-11 09:45")

    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.F15) == pd.to_datetime("2021-11-11 09:45")
    assert freq_end_time(pd.to_datetime("2021-11-11 09:45"), Freq.F15) == pd.to_datetime("2021-11-11 09:45")
    assert freq_end_time(pd.to_datetime("2021-11-11 14:56"), Freq.F15) == pd.to_datetime("2021-11-11 15:00")

    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.F30) == pd.to_datetime("2021-11-11 10:00")
    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.F60) == pd.to_datetime("2021-11-11 10:30")
    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.D) == pd.to_datetime("2021-11-11")
    assert freq_end_time(pd.to_datetime("2021-11-11 09:43"), Freq.W) == pd.to_datetime("2021-11-12")

    assert freq_end_time(pd.to_datetime("2021-03-05"), Freq.M) == pd.to_datetime("2021-03-31")


def test_kline_generator():
    # 验证指定级别
    bars = kline[:2000]

    kg = KlineGenerator(freqs=['周线', '日线', '30分钟', '5分钟', '1分钟'])
    for row in tqdm(bars):
        kg.update(row)

    assert not kg.m60 and not kg.m15 and not kg.M

    bars = kline[:20000]
    kg = KlineGenerator(max_count=2000)
    for row in tqdm(bars):
        kg.update(row)

    assert kg.m60 and kg.m15

    # 验证K线获取
    klines = kg.get_klines({'1分钟': 100, '5分钟': 100})
    for k, v in klines.items():
        assert len(v) == 100

    # 数量验证
    assert len(kg.m1) == 2000
    assert len(kg.m5) == 4001
    assert len(kg.m15) == 1334
    assert len(kg.m60) == 334
    assert len(kg.D) == 84
    assert len(kg.W) == 17
    assert len(kg.M) == 5

    # 测试实盘连续输入
    for _ in range(5):
        kg.update(bars[-1])
        assert len(kg.m1) == 2000


def test_kgd():
    df = pd.read_csv(os.path.join(cur_path, './data/000001.SH_D.csv'))
    bars = []
    for i, row in df.iterrows():
        bars.append(RawBar(symbol=row.symbol, id=i, freq=Freq.D, dt=pd.to_datetime(row['dt']),
                           open=row.open, close=row.close, high=row.high, low=row.low, vol=row.vol))
    kgd = KlineGeneratorD()
    for bar in bars:
        kgd.update(bar)

    assert kgd.end_dt == pd.to_datetime('2020-07-16 15:00:00')
    assert len(kgd.bars['月线']) == 165
    assert len(kgd.bars['年线']) == 15
    assert kgd.bars['月线'][-2].id > kgd.bars['月线'][-3].id

    kgd = KlineGeneratorD(freqs=[Freq.D.value, Freq.W.value, Freq.M.value])
    for bar in bars:
        kgd.update(bar)

    assert kgd.end_dt == pd.to_datetime('2020-07-16 15:00:00')
    assert len(kgd.bars['月线']) == 165
    assert Freq.Y.value not in kgd.bars.keys()
