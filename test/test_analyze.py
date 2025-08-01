# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/16 20:31
describe: czsc.analyze 单元测试
"""
import pytest
import pandas as pd
from czsc import mock
from czsc.analyze import CZSC, RawBar, NewBar, remove_include, FX, check_fx, Direction, kline_pro
from czsc.enum import Freq


def get_mock_bars(freq=Freq.D, symbol="000001", n_days=100):
    """获取mock K线数据并转换为RawBar对象"""
    if freq == Freq.F1:
        df = mock.generate_symbol_kines(symbol, "1分钟", sdt="20240101", edt="20240110", seed=42)
    elif freq == Freq.F5:
        df = mock.generate_symbol_kines(symbol, "5分钟", sdt="20240101", edt="20240110", seed=42)
    elif freq == Freq.D:
        df = mock.generate_symbol_kines(symbol, "日线", sdt="20230101", edt="20240101", seed=42)
    else:
        df = mock.generate_klines(seed=42)
        df = df[df['symbol'] == symbol].head(n_days) if symbol in df['symbol'].values else df.head(n_days)
    
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row['symbol'], 
            id=i, 
            freq=freq, 
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


def test_find_bi():
    """测试笔的识别功能"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=200)
    
    bars1 = []
    for bar in bars:
        if len(bars1) < 2:
            bars1.append(NewBar(
                symbol=bar.symbol, id=bar.id, freq=bar.freq,
                dt=bar.dt, open=bar.open, close=bar.close, 
                high=bar.high, low=bar.low, vol=bar.vol, 
                amount=bar.amount, elements=[bar]
            ))
        else:
            k1, k2 = bars1[-2:]
            has_include, k3 = remove_include(k1, k2, bar)
            if has_include:
                bars1[-1] = k3
            else:
                bars1.append(k3)

    fxs = []
    for i in range(1, len(bars1) - 1):
        fx = check_fx(bars1[i - 1], bars1[i], bars1[i + 1])
        if isinstance(fx, FX):
            fxs.append(fx)
    
    assert len(fxs) > 0, "应该识别出分型"
    assert all(isinstance(fx, FX) for fx in fxs), "所有识别出的对象都应该是FX类型"


def test_czsc_basic():
    """测试CZSC基础功能"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=200)
    c = CZSC(bars)
    
    assert c.symbol == "000001", "symbol应该正确设置"
    assert c.freq == Freq.D, "频率应该正确设置"
    assert len(c.bars_raw) > 0, "原始K线数据不应为空"
    assert len(c.bars_ubi) > 0, "去除包含关系后的K线数据不应为空"
    assert len(c.bi_list) > 0, "笔的列表不应为空"


def test_czsc_signals():
    """测试CZSC信号计算"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=200)
    c = CZSC(bars, get_signals=None)
    
    assert isinstance(c.signals, dict), "signals应该是字典类型"


def test_czsc_ubi_properties():
    """测试CZSC的ubi属性"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=200)
    c = CZSC(bars)
    
    ubi = c.ubi
    assert 'direction' in ubi, "ubi应该包含direction字段"
    assert 'high_bar' in ubi, "ubi应该包含high_bar字段"
    assert 'low_bar' in ubi, "ubi应该包含low_bar字段"
    assert isinstance(ubi['direction'], Direction), "direction应该是Direction类型"


def test_remove_include():
    """测试包含关系处理功能"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=50)
    
    if len(bars) >= 3:
        k1 = NewBar(
            symbol=bars[0].symbol, id=bars[0].id, freq=bars[0].freq,
            dt=bars[0].dt, open=bars[0].open, close=bars[0].close,
            high=bars[0].high, low=bars[0].low, vol=bars[0].vol,
            amount=bars[0].amount, elements=[bars[0]]
        )
        k2 = NewBar(
            symbol=bars[1].symbol, id=bars[1].id, freq=bars[1].freq,
            dt=bars[1].dt, open=bars[1].open, close=bars[1].close,
            high=bars[1].high, low=bars[1].low, vol=bars[1].vol,
            amount=bars[1].amount, elements=[bars[1]]
        )
        
        has_include, k3 = remove_include(k1, k2, bars[2])
        assert isinstance(has_include, bool), "has_include应该是布尔类型"
        assert isinstance(k3, NewBar), "k3应该是NewBar类型"


def test_check_fx():
    """测试分型检测功能"""
    bars = get_mock_bars(freq=Freq.D, symbol="000001", n_days=50)
    
    if len(bars) >= 3:
        bars_new = []
        for bar in bars[:3]:
            bars_new.append(NewBar(
                symbol=bar.symbol, id=bar.id, freq=bar.freq,
                dt=bar.dt, open=bar.open, close=bar.close,
                high=bar.high, low=bar.low, vol=bar.vol,
                amount=bar.amount, elements=[bar]
            ))
        
        fx = check_fx(bars_new[0], bars_new[1], bars_new[2])
        assert fx is None or isinstance(fx, FX), "fx应该是None或FX类型"
