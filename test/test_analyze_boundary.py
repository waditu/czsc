# -*- coding: utf-8 -*-
"""
test_analyze_boundary.py - CZSC 分析核心模块边界情况测试

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20220101-20250101（3年数据）
- 频率: 日线、5分钟线
- Seed: 42（确保可重现）

测试覆盖:
- 少量K线数据（不足以形成笔）
- 多频率分析一致性
- 增量更新正确性
- format_standard_kline 边界情况
"""
import pytest
import pandas as pd
import numpy as np
from czsc import mock
from czsc.core import CZSC, Freq, format_standard_kline


def get_daily_bars(symbol="000001", sdt="20220101", edt="20250101"):
    """获取日线 mock 数据"""
    df = mock.generate_symbol_kines(symbol, "日线", sdt=sdt, edt=edt, seed=42)
    return format_standard_kline(df, freq=Freq.D)


class TestCZSCBoundary:
    """CZSC 分析边界情况测试"""

    def test_minimal_bars(self):
        """测试最少K线（不足以形成笔）"""
        bars = get_daily_bars()[:5]
        c = CZSC(bars)
        assert len(c.bars_raw) == 5
        assert len(c.bi_list) == 0, "5根K线不应形成笔"

    def test_moderate_bars(self):
        """测试中等数量K线"""
        bars = get_daily_bars()[:50]
        c = CZSC(bars)
        # CZSC 可能因 max_bi_num 裁剪旧K线，因此使用 <= 判断
        assert len(c.bars_raw) <= 50
        assert len(c.bars_raw) > 0
        assert len(c.bars_ubi) > 0

    def test_large_dataset(self):
        """测试完整3年数据"""
        bars = get_daily_bars()
        c = CZSC(bars)
        assert len(c.bars_raw) > 500
        assert len(c.bi_list) > 10, "3年数据应形成多笔"
        assert len(c.fx_list) > 0, "应有分型"

    def test_incremental_update(self):
        """测试增量更新"""
        bars = get_daily_bars()
        # 先用前100根K线初始化
        c = CZSC(bars[:100])
        initial_bi_count = len(c.bi_list)
        initial_bars_count = len(c.bars_raw)

        # 逐根增加K线
        for bar in bars[100:200]:
            c.update(bar)

        # CZSC 可能因 max_bi_num 裁剪旧K线，bars_raw 应增长但不一定恰好等于200
        assert len(c.bars_raw) > initial_bars_count, "增量更新后K线数应增加"
        assert len(c.bi_list) >= initial_bi_count, "增量更新后笔数不应减少"

    def test_max_bi_num(self):
        """测试 max_bi_num 限制"""
        bars = get_daily_bars()
        c = CZSC(bars, max_bi_num=10)
        assert len(c.bi_list) <= 10, "笔数量应被 max_bi_num 限制"

    def test_different_symbols(self):
        """测试不同品种"""
        for symbol in ["000001", "000002", "600001"]:
            df = mock.generate_symbol_kines(symbol, "日线", sdt="20220101", edt="20250101", seed=42)
            bars = format_standard_kline(df, freq=Freq.D)
            c = CZSC(bars)
            assert c.symbol == symbol

    def test_ubi_structure(self):
        """测试 ubi 结构完整性"""
        bars = get_daily_bars()
        c = CZSC(bars)
        ubi = c.ubi
        assert "direction" in ubi
        assert "high_bar" in ubi
        assert "low_bar" in ubi


class TestFormatStandardKline:
    """format_standard_kline 函数测试"""

    def test_basic_conversion(self):
        """测试基本转换"""
        df = mock.generate_symbol_kines("000001", "日线", sdt="20220101", edt="20250101", seed=42)
        bars = format_standard_kline(df, freq=Freq.D)
        assert len(bars) > 0
        assert bars[0].freq == Freq.D
        assert bars[0].symbol == "000001"

    def test_preserves_data(self):
        """测试数据保留完整性"""
        df = mock.generate_symbol_kines("000001", "日线", sdt="20220101", edt="20250101", seed=42)
        bars = format_standard_kline(df, freq=Freq.D)
        # 验证第一根K线数据
        first_row = df.iloc[0]
        assert bars[0].open == first_row["open"]
        assert bars[0].close == first_row["close"]
        assert bars[0].high == first_row["high"]
        assert bars[0].low == first_row["low"]

    def test_5min_frequency(self):
        """测试5分钟频率"""
        df = mock.generate_symbol_kines("000001", "5分钟", sdt="20220101", edt="20220201", seed=42)
        bars = format_standard_kline(df, freq=Freq.F5)
        assert len(bars) > 0
        assert bars[0].freq == Freq.F5

    def test_sorted_by_time(self):
        """测试按时间排序"""
        df = mock.generate_symbol_kines("000001", "日线", sdt="20220101", edt="20250101", seed=42)
        bars = format_standard_kline(df, freq=Freq.D)
        for i in range(1, len(bars)):
            assert bars[i].dt >= bars[i - 1].dt, "K线应按时间升序排列"
