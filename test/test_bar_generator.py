# coding: utf-8
import os
import pandas as pd
from tqdm import tqdm

from czsc.objects import RawBar, Freq
from czsc.utils.bar_generator import BarGenerator, freq_end_time
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


def test_bg_on_f1():
    """验证从1分钟开始生成各周期K线"""
    bg = BarGenerator(base_freq='1分钟', freqs=['周线', '日线', '30分钟', '5分钟'], max_count=2000)
    for row in tqdm(kline):
        bg.update(row)

    assert "60分钟" not in bg.bars.keys() and "15分钟" not in bg.bars.keys()
    bars_len = {f: len(bg.bars[f]) for f in dict(bg.bars).keys()}

    assert bars_len['1分钟'] == 2000
    assert bars_len['5分钟'] == 2000
    assert bars_len['30分钟'] == 2000

    # 验证具体某根K线
    assert bg.bars['周线'][-10].dt == pd.to_datetime('2018-12-07')
    assert bg.bars['周线'][-10].open == 2647.13
    assert bg.bars['周线'][-10].close == 2605.89
    assert bg.bars['周线'][-10].high == 2666.03
    assert bg.bars['周线'][-10].low == 2599.35
    assert bg.bars['周线'][-10].vol == 78065820800

    # 测试重复输入
    for _ in range(5):
        bg.update(kline[-1])
        for freq, l in bars_len.items():
            assert len(bg.bars[freq]) == l


def test_bg_on_d():
    df = pd.read_csv(os.path.join(cur_path, './data/000001.SH_D.csv'))
    bars = []
    for i, row in df.iterrows():
        bars.append(RawBar(symbol=row.symbol, id=i, freq=Freq.D, dt=pd.to_datetime(row['dt']),
                           open=row.open, close=row.close, high=row.high, low=row.low, vol=row.vol))

    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线', '季线', '年线'], max_count=2000)
    for bar in bars:
        bg.update(bar)

    assert bg.end_dt == pd.to_datetime('2020-07-16 15:00:00')
    assert len(bg.bars['月线']) == 165
    assert len(bg.bars['年线']) == 15
    assert bg.bars['月线'][-2].id > bg.bars['月线'][-3].id
