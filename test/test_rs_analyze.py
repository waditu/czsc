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
from rs_czsc import CZSC, RawBar, NewBar, FX, Direction
from rs_czsc import Freq


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
    c = CZSC(bars)
    
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
