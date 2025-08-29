# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/16 20:31
describe: czsc.utils.bar_generator 单元测试
"""
import pytest
import pandas as pd
from czsc import mock
from czsc.objects import Freq, RawBar
from czsc.utils.bar_generator import BarGenerator, freq_end_time, resample_bars, check_freq_and_market, freq_market_times


def get_mock_1min_bars():
    """获取1分钟mock数据"""
    df = mock.generate_symbol_kines("000001", "1分钟", sdt="20240101", edt="20240110", seed=42)
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row['symbol'], 
            id=i, 
            freq=Freq.F1, 
            open=row['open'], 
            dt=row['dt'],
            close=row['close'], 
            high=row['high'], 
            low=row['low'], 
            vol=row['vol'], 
            amount=row['amount']
        )
        bars.append(bar)
    return bars


def get_mock_daily_bars():
    """获取日线mock数据"""
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row['symbol'], 
            id=i, 
            freq=Freq.D, 
            open=row['open'], 
            dt=row['dt'],
            close=row['close'], 
            high=row['high'], 
            low=row['low'], 
            vol=row['vol'], 
            amount=row['amount']
        )
        bars.append(bar)
    return bars


def test_check_freq_and_market():
    time_seq = ['11:00', '15:00', '23:00', '01:00', '02:30']
    assert check_freq_and_market(time_seq, freq='120分钟') == ('120分钟', '期货')

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

    for key, time_seq in freq_market_times.items():
        freq, market = key.split("_")
        assert check_freq_and_market(time_seq, freq) == (freq, market)


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
    """测试K线重采样功能"""
    kline = get_mock_1min_bars()
    df = pd.DataFrame([bar.__dict__ for bar in kline])
    
    _f30_bars = resample_bars(df, Freq.F30, raw_bars=True)
    assert len(_f30_bars) > 0, "30分钟K线数据不应为空"

    _d_bars = resample_bars(df, Freq.D, raw_bars=True)
    assert len(_d_bars) > 0, "日线数据不应为空"

    _f60_bars = resample_bars(df, Freq.F60, raw_bars=True)
    assert len(_f60_bars) > 0, "60分钟K线数据不应为空"

    _f30_bars = resample_bars(df, Freq.F30, raw_bars=True, market='A股')
    assert len(_f30_bars) > 0, "A股市场30分钟K线数据不应为空"

    _d_bars = resample_bars(df, Freq.D, raw_bars=True, market='A股')
    assert len(_d_bars) > 0, "A股市场日线数据不应为空"

    _f60_bars = resample_bars(df, Freq.F60, raw_bars=True, market='A股')
    assert len(_f60_bars) > 0, "A股市场60分钟K线数据不应为空"


def test_bg_on_f1():
    """验证从1分钟开始生成各周期K线"""
    kline = get_mock_1min_bars()
    bg = BarGenerator(base_freq='1分钟', freqs=['周线', '日线', '30分钟', '5分钟'], max_count=2000)
    
    for bar in kline:
        bg.update(bar)

    assert "60分钟" not in bg.bars.keys() and "15分钟" not in bg.bars.keys()
    bars_len = {f: len(bg.bars[f]) for f in dict(bg.bars).keys()}

    assert bars_len['1分钟'] > 0, "1分钟K线数据不应为空"
    assert bars_len['5分钟'] > 0, "5分钟K线数据不应为空"
    assert bars_len['30分钟'] > 0, "30分钟K线数据不应为空"

    assert isinstance(bg.bars['日线'][-1].dt, pd.Timestamp), "日线时间应该是Timestamp类型"
    assert bg.bars['日线'][-1].open > 0, "开盘价应该大于0"
    assert bg.bars['日线'][-1].close > 0, "收盘价应该大于0"
    assert bg.bars['日线'][-1].high >= bg.bars['日线'][-1].close, "最高价应该大于等于收盘价"
    assert bg.bars['日线'][-1].low <= bg.bars['日线'][-1].close, "最低价应该小于等于收盘价"

    # 测试重复输入
    initial_lens = {freq: len(bars) for freq, bars in bg.bars.items()}
    for _ in range(5):
        bg.update(kline[-1])
        for freq, initial_len in initial_lens.items():
            assert len(bg.bars[freq]) == initial_len, f"{freq}重复输入后长度不应改变"


def test_bg_on_d():
    """测试日线级别的BarGenerator"""
    bars = get_mock_daily_bars()
    bg = BarGenerator(base_freq='日线', freqs=['周线', '月线'], max_count=2000)
    
    for bar in bars:
        bg.update(bar)

    assert isinstance(bg.end_dt, pd.Timestamp), "结束时间应该是Timestamp类型"
    assert len(bg.bars['月线']) > 0, "月线数据不应为空"
    assert len(bg.bars['周线']) > 0, "周线数据不应为空"
    
    if len(bg.bars['月线']) >= 2:
        assert bg.bars['月线'][-2].id < bg.bars['月线'][-1].id, "月线ID应该递增"


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
