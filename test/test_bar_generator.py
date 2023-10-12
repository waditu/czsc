# coding: utf-8
import os
import pandas as pd
from tqdm import tqdm
from czsc.objects import Freq
from czsc.utils.bar_generator import BarGenerator, freq_end_time, resample_bars, check_freq_and_market, freq_market_times
from test.test_analyze import read_1min, read_daily

cur_path = os.path.split(os.path.realpath(__file__))[0]
kline = read_1min()


def test_check_freq_and_market():
    time_seq = ['11:00', '15:00', '23:00', '01:00', '02:30']
    assert check_freq_and_market(time_seq) == ('120分钟', '期货')

    time_seq = [
        '09:31',
        '09:32',
        '09:33',
        '09:34',
        '09:35',
        '09:36',
        '09:37',
        '09:38',
        '09:39',
        '09:40',
        '09:41',
        '09:42',
        '09:43',
        '09:44',
        '09:45',
        '09:46',
        '09:47',
        '09:48',
        '09:49',
        '09:50',
        '09:51',
        '09:52',
        '09:53',
        '09:54',
        '09:55',
        '09:56',
        '09:57',
        '09:58',
        '09:59',
        '10:00',
        '10:01',
        '10:02',
        '10:03',
        '10:04',
        '10:05',
        '10:06',
        '10:07',
        '10:08',
        '10:09',
        '10:10',
        '10:11',
        '10:12',
        '10:13',
        '10:14',
        '10:15',
        '10:16',
        '10:17',
        '10:18',
        '10:19',
        '10:20',
        '10:21',
        '10:22',
        '10:23',
        '10:24',
        '10:25',
        '10:26',
        '10:27',
        '10:28',
        '10:29',
        '10:30',
        '10:31',
        '10:32',
        '10:33',
        '10:34',
        '10:35',
        '10:36',
        '10:37',
        '10:38',
        '10:39',
        '10:40',
        '10:41',
        '10:42',
        '10:43',
        '10:44',
        '10:45',
        '10:46',
        '10:47',
        '10:48',
        '10:49',
        '10:50',
        '10:51',
        '10:52',
        '10:53',
        '10:54',
        '10:55',
        '10:56',
        '10:57',
        '10:58',
        '10:59',
        '11:00',
        '11:01',
        '11:02',
        '11:03',
        '11:04',
        '11:05',
        '11:06',
        '11:07',
        '11:08',
        '11:09',
        '11:10',
        '11:11',
        '11:12',
        '11:13',
        '11:14',
        '11:15',
        '11:16',
        '11:17',
        '11:18',
        '11:19',
        '11:20',
        '11:21',
        '11:22',
        '11:23',
        '11:24',
        '11:25',
        '11:26',
        '11:27',
        '11:28',
        '11:29',
        '11:30',
        '13:01',
        '13:02',
        '13:03',
        '13:04',
        '13:05',
        '13:06',
        '13:07',
        '13:08',
        '13:09',
        '13:10',
        '13:11',
        '13:12',
        '13:13',
        '13:14',
        '13:15',
        '13:16',
        '13:17',
        '13:18',
        '13:19',
        '13:20',
        '13:21',
        '13:22',
        '13:23',
        '13:24',
        '13:25',
        '13:26',
        '13:27',
        '13:28',
        '13:29',
        '13:30',
        '13:31',
        '13:32',
        '13:33',
        '13:34',
        '13:35',
        '13:36',
        '13:37',
        '13:38',
        '13:39',
        '13:40',
        '13:41',
        '13:42',
        '13:43',
        '13:44',
        '13:45',
        '13:46',
        '13:47',
        '13:48',
        '13:49',
        '13:50',
        '13:51',
        '13:52',
        '13:53',
        '13:54',
        '13:55',
        '13:56',
        '13:57',
        '13:58',
        '13:59',
        '14:00',
        '14:01',
        '14:02',
        '14:03',
        '14:04',
        '14:05',
        '14:06',
        '14:07',
        '14:08',
        '14:09',
        '14:10',
        '14:11',
        '14:12',
        '14:13',
        '14:14',
        '14:15',
        '14:16',
        '14:17',
        '14:18',
        '14:19',
        '14:20',
        '14:21',
        '14:22',
        '14:23',
        '14:24',
        '14:25',
        '14:26',
        '14:27',
        '14:28',
        '14:29',
        '14:30',
        '14:31',
        '14:32',
        '14:33',
        '14:34',
        '14:35',
        '14:36',
        '14:37',
        '14:38',
        '14:39',
        '14:40',
        '14:41',
        '14:42',
        '14:43',
        '14:44',
        '14:45',
        '14:46',
        '14:47',
        '14:48',
        '14:49',
        '14:50',
        '14:51',
        '14:52',
        '14:53',
        '14:54',
        '14:55',
        '14:56',
        '14:57',
        '14:58',
        '15:00',
    ]
    assert check_freq_and_market(time_seq, freq='1分钟') == ('1分钟', 'A股')

    for key, values in freq_market_times.items():
        assert check_freq_and_market(values) == (key.split("_")[0], key.split("_")[1])


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


def test_resample_bars():
    df = pd.DataFrame(kline)
    _f30_bars = resample_bars(df, Freq.F30, raw_bars=True)
    assert len(_f30_bars) == 7991

    _d_bars = resample_bars(df, Freq.D, raw_bars=True)
    assert len(_d_bars) == 1000

    _f60_bars = resample_bars(df, Freq.F60, raw_bars=True)
    assert len(_f60_bars) == 3996

    _f30_bars = resample_bars(df, Freq.F30, raw_bars=True, market='A股')
    assert len(_f30_bars) == 7991

    _d_bars = resample_bars(df, Freq.D, raw_bars=True, market='A股')
    assert len(_d_bars) == 1000

    _f60_bars = resample_bars(df, Freq.F60, raw_bars=True, market='A股')
    assert len(_f60_bars) == 3996


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
    bars = read_daily()
    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线', '季线', '年线'], max_count=2000)
    for bar in bars:
        bg.update(bar)

    assert bg.end_dt == pd.to_datetime('2020-07-16 15:00:00')
    assert len(bg.bars['月线']) == 165
    assert len(bg.bars['年线']) == 15
    assert bg.bars['月线'][-2].id > bg.bars['月线'][-3].id


def test_is_trading_time():
    from datetime import datetime
    from czsc.utils.bar_generator import is_trading_time

    # Test for A股 market
    assert not is_trading_time(datetime(2022, 1, 3, 9, 30), market="A股")
    assert is_trading_time(datetime(2022, 1, 3, 9, 31), market="A股")
    assert is_trading_time(datetime(2022, 1, 3, 11, 30), market="A股")
    assert not is_trading_time(datetime(2022, 1, 3, 12, 59), market="A股")
    assert is_trading_time(datetime(2022, 1, 3, 15, 0), market="A股")
    assert not is_trading_time(datetime(2022, 1, 3, 20, 0), market="A股")

    # Test for other markets
    assert is_trading_time(datetime(2022, 1, 3, 9, 30), market="期货")
    assert not is_trading_time(datetime(2022, 1, 3, 10, 25), market="期货")
    assert not is_trading_time(datetime(2022, 1, 3, 12, 59), market="期货")
    assert is_trading_time(datetime(2022, 1, 3, 15, 0), market="期货")
    assert not is_trading_time(datetime(2022, 1, 3, 20, 0), market="期货")


def test_get_intraday_times():
    from czsc.utils.bar_generator import get_intraday_times

    assert get_intraday_times(freq='60分钟', market='A股') == ['10:30', '11:30', '14:00', '15:00']
    assert get_intraday_times(freq='120分钟', market='A股') == ['11:30', '15:00']
    assert get_intraday_times(freq='120分钟', market='期货') == ['11:00', '15:00', '23:00', '01:00', '02:30']
    x = ['02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00', '00:00']
    assert get_intraday_times(freq='120分钟', market='默认') == x
