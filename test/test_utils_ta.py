# -*- coding: utf-8 -*-
"""
describe: czsc.utils.ta 单元测试 - 技术分析指标
author: Claude Code
create_dt: 2026/2/15

Mock数据格式说明：
- 使用 czsc.mock.generate_symbol_kines 生成
- 日期范围：20200101-20250101（5年数据，满足3年+要求）
- K线格式：OHLCVA（开高低收成交量成交额）
- 频率：支持 1分钟、5分钟、15分钟、30分钟、日线
"""
import pytest
import numpy as np
import pandas as pd
from czsc import mock
from czsc.core import format_standard_kline, Freq
from czsc.utils.ta import SMA, EMA, MACD, RSI, BOLL, ATR, KDJ


def get_daily_bars(symbol="000001", sdt="20200101", edt="20250101"):
    """获取日线K线数据（5年数据，满足3年+要求）

    Args:
        symbol: 品种代码
        sdt: 开始日期，格式 YYYYMMDD
        edt: 结束日期，格式 YYYYMMDD

    Returns:
        list[RawBar]: 原始K线对象列表
    """
    df = mock.generate_symbol_kines(symbol, "日线", sdt=sdt, edt=edt, seed=42)
    return format_standard_kline(df, freq=Freq.D)


def test_sma():
    """测试简单移动平均线指标"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    # 测试不同周期
    for period in [5, 10, 20, 60]:
        ma = SMA(closes, period)
        assert len(ma) == len(closes), f"SMA长度应该与输入数据一致，period={period}"
        assert ma[period-1] > 0, f"SMA在period={period}后应该有有效值"

        # 验证SMA计算正确性
        expected = np.mean(closes[:period])
        assert abs(ma[period-1] - expected) < 0.01, f"SMA计算值不正确，period={period}"


def test_ema():
    """测试指数移动平均线指标"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    for period in [5, 12, 26]:
        ema = EMA(closes, period)
        assert len(ema) == len(closes), f"EMA长度应该与输入数据一致，period={period}"
        # EMA的第一个有效值应该在period位置附近
        assert not np.isnan(ema[-1]), f"EMA最后值不应为NaN，period={period}"


def test_macd():
    """测试MACD指标"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    diff, dea, macd = MACD(closes, fast=12, slow=26, signal_period=9)

    assert len(diff) == len(closes), "MACD diff长度应该与输入数据一致"
    assert len(dea) == len(closes), "MACD dea长度应该与输入数据一致"
    assert len(macd) == len(closes), "MACD长度应该与输入数据一致"

    # 验证MACD柱状图 = 2 * (diff - dea)
    for i in range(len(macd)):
        if not np.isnan(diff[i]) and not np.isnan(dea[i]):
            expected_macd = 2 * (diff[i] - dea[i])
            assert abs(macd[i] - expected_macd) < 0.001, f"MACD计算值不正确，i={i}"


def test_rsi():
    """测试RSI相对强弱指标"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    for period in [6, 14, 24]:
        rsi = RSI(closes, period)
        assert len(rsi) == len(closes), f"RSI长度应该与输入数据一致，period={period}"

        # RSI值应该在0-100之间
        valid_rsi = rsi[~np.isnan(rsi)]
        assert len(valid_rsi) > 0, f"RSI应该有有效值，period={period}"
        assert np.all((valid_rsi >= 0) & (valid_rsi <= 100)), f"RSI值应该在0-100之间，period={period}"


def test_boll():
    """测试布林带指标"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    for period in [10, 20]:
        upper, middle, lower = BOLL(closes, period)
        assert len(upper) == len(closes), f"BOLL上轨长度应该与输入数据一致，period={period}"
        assert len(middle) == len(closes), f"BOLL中轨长度应该与输入数据一致，period={period}"
        assert len(lower) == len(closes), f"BOLL下轨长度应该与输入数据一致，period={period}"

        # 验证上轨 >= 中轨 >= 下轨
        for i in range(len(upper)):
            if not np.isnan(upper[i]) and not np.isnan(middle[i]) and not np.isnan(lower[i]):
                assert upper[i] >= middle[i] >= lower[i], \
                    f"BOLL应该满足上轨>=中轨>=下轨，i={i}, upper={upper[i]}, middle={middle[i]}, lower={lower[i]}"


def test_atr():
    """测试ATR平均真实波幅指标"""
    bars = get_daily_bars()

    highs = np.array([bar.high for bar in bars])
    lows = np.array([bar.low for bar in bars])
    closes = np.array([bar.close for bar in bars])

    for period in [14, 20]:
        atr = ATR(highs, lows, closes, period)
        assert len(atr) == len(closes), f"ATR长度应该与输入数据一致，period={period}"

        # ATR应该非负
        valid_atr = atr[~np.isnan(atr)]
        assert len(valid_atr) > 0, f"ATR应该有有效值，period={period}"
        assert np.all(valid_atr >= 0), f"ATR值应该非负，period={period}"


def test_kdj():
    """测试KDJ随机指标"""
    bars = get_daily_bars()

    highs = np.array([bar.high for bar in bars])
    lows = np.array([bar.low for bar in bars])
    closes = np.array([bar.close for bar in bars])

    for fastk_period in [9, 14]:
        k, d, j = KDJ(highs, lows, closes, fastk_period=fastk_period, slowk_period=3, slowd_period=3)

        assert len(k) == len(closes), f"KDJ K值长度应该与输入数据一致，fastk_period={fastk_period}"
        assert len(d) == len(closes), f"KDJ D值长度应该与输入数据一致，fastk_period={fastk_period}"
        assert len(j) == len(closes), f"KDJ J值长度应该与输入数据一致，fastk_period={fastk_period}"

        # KDJ值应该在0-100之间
        valid_k = k[~np.isnan(k)]
        valid_d = d[~np.isnan(d)]
        valid_j = j[~np.isnan(j)]

        assert len(valid_k) > 0, f"KDJ应该有有效K值，fastk_period={fastk_period}"
        assert np.all((valid_k >= 0) & (valid_k <= 100)), f"K值应该在0-100之间，fastk_period={fastk_period}"
        assert np.all((valid_d >= 0) & (valid_d <= 100)), f"D值应该在0-100之间，fastk_period={fastk_period}"
        # J值可以超出0-100范围
        assert len(valid_j) > 0, f"KDJ应该有有效J值，fastk_period={fastk_period}"


def test_indicators_with_different_frequencies():
    """测试不同频率K线的技术指标计算"""
    for freq in ["1分钟", "5分钟", "30分钟"]:
        # 生成3年+的数据
        df = mock.generate_symbol_kines("000001", freq, sdt="20220101", edt="20250101", seed=42)
        bars = format_standard_kline(df, freq=getattr(Freq, f"F{freq.replace('分钟', '')}" if freq != "日线" else Freq.D))

        if len(bars) > 20:
            closes = np.array([bar.close for bar in bars])

            # 测试SMA
            sma = SMA(closes, 5)
            assert len(sma) == len(closes), f"{freq} SMA长度应该与输入数据一致"

            # 测试RSI
            rsi = RSI(closes, 14)
            assert len(rsi) == len(closes), f"{freq} RSI长度应该与输入数据一致"


def test_edge_cases():
    """测试边界情况"""
    bars = get_daily_bars()
    closes = np.array([bar.close for bar in bars])

    # 测试空数组
    empty = np.array([])
    sma_empty = SMA(empty, 5)
    assert len(sma_empty) == 0, "空数组应该返回空结果"

    # 测试单个值
    single = np.array([100.0])
    sma_single = SMA(single, 5)
    assert len(sma_single) == 1, "单值数组应该返回单值结果"

    # 测试周期大于数据长度
    sma_large = SMA(closes[:10], 20)
    assert len(sma_large) == 10, "周期大于数据长度时，长度应与输入一致"
    # 最后一个值应该是所有10个值的平均
    assert not np.isnan(sma_large[-1]), "最后一个值不应该为NaN"
