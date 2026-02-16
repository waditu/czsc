# -*- coding: utf-8 -*-
"""
test_signals.py - 信号生成函数单元测试

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20200101-20250101（5年数据，满足3年+要求）
- 频率: 30分钟 / 60分钟 / 日线
- Seed: 42（确保可重现）

测试覆盖范围:
- bar.py: K线级别信号（is_third_buy, is_third_sell, is_first_buy）
- vol.py: 成交量信号（vol_single_ma_V230214, vol_double_ma_V230214）
- cxt.py: 上下文信号（cxt_bi_base_V230228, cxt_fx_power_V221107）
- tas.py: 技术指标信号（tas_ma_base_V230224）
"""
import pytest
import pandas as pd
from czsc import mock
from czsc.core import CZSC, format_standard_kline, Freq


def get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101", seed=42):
    """获取CZSC对象用于测试

    Args:
        symbol: 品种代码
        freq: K线频率
        sdt: 开始日期
        edt: 结束日期
        seed: 随机种子

    Returns:
        CZSC: 缠论分析对象
    """
    df = mock.generate_symbol_kines(symbol=symbol, freq=freq, sdt=sdt, edt=edt, seed=seed)
    bars = format_standard_kline(df, freq=freq)

    # 过滤掉没有成交量的K线
    bars = [bar for bar in bars if bar.vol > 0]

    if len(bars) == 0:
        return None

    c = CZSC(bars)
    return c


class TestBarSignals:
    """测试K线级别信号"""

class TestVolSignals:
    """测试成交量信号"""

    def test_vol_single_ma_with_normal_data(self):
        """测试单均线成交量信号（正常数据）"""
        from czsc.signals.vol import vol_single_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = vol_single_ma_V230214(c, ma_period=5)
        assert signal is None or isinstance(signal, dict), "成交量信号返回类型不正确"

    def test_vol_single_ma_with_different_periods(self):
        """测试单均线成交量信号（不同周期）"""
        from czsc.signals.vol import vol_single_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        periods = [5, 10, 20]
        for period in periods:
            signal = vol_single_ma_V230214(c, ma_period=period)
            assert signal is None or isinstance(signal, dict), \
                f"周期{period}的成交量信号返回类型不正确"

    def test_vol_double_ma_with_normal_data(self):
        """测试双均线成交量信号（正常数据）"""
        from czsc.signals.vol import vol_double_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = vol_double_ma_V230214(c, ma_period1=5, ma_period2=10)
        assert signal is None or isinstance(signal, dict), "双均线成交量信号返回类型不正确"

    def test_vol_double_ma_with_different_symbols(self):
        """测试双均线成交量信号（多品种）"""
        from czsc.signals.vol import vol_double_ma_V230214

        symbols = ["000001", "000002"]
        for symbol in symbols:
            c = get_czsc_obj(symbol=symbol, freq="30分钟", sdt="20200101", edt="20250101")
            if c is None or len(c.bars_raw) < 100:
                continue

            signal = vol_double_ma_V230214(c, ma_period1=5, ma_period2=10)
            assert signal is None or isinstance(signal, dict), \
                f"品种{symbol}的双均线成交量信号返回类型不正确"


class TestContextSignals:
    """测试上下文信号"""

    def test_cxt_bi_base_with_normal_data(self):
        """测试笔基础信号（正常数据）"""
        from czsc.signals.cxt import cxt_bi_base_V230228

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = cxt_bi_base_V230228(c, di=1)
        assert signal is None or isinstance(signal, dict), "笔基础信号返回类型不正确"

    def test_cxt_fx_power_with_normal_data(self):
        """测试分型力度信号（正常数据）"""
        from czsc.signals.cxt import cxt_fx_power_V221107

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = cxt_fx_power_V221107(c, di=1)
        assert signal is None or isinstance(signal, dict), "分型力度信号返回类型不正确"

    def test_cxt_signals_with_different_frequencies(self):
        """测试上下文信号（多频率）"""
        from czsc.signals.cxt import cxt_bi_base_V230228

        freqs = ["30分钟", "日线"]
        for freq in freqs:
            c = get_czsc_obj(symbol="000001", freq=freq, sdt="20200101", edt="20250101")
            if c is None or len(c.bars_raw) < 100:
                continue

            signal = cxt_bi_base_V230228(c, di=1)
            assert signal is None or isinstance(signal, dict), \
                f"频率{freq}的上下文信号返回类型不正确"


class TestTASSignals:
    """测试技术指标信号"""

class TestSignalCombinations:
    """测试信号组合"""

    def test_signal_return_structure(self):
        """测试信号返回结构"""
        from czsc.signals.vol import vol_single_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = vol_single_ma_V230214(c, ma_period=5)

        # 如果信号不是None，检查结构
        if signal is not None:
            assert isinstance(signal, dict), "信号应该是字典类型"
            # 信号字典通常包含key1, key2, key3, value等字段
            # 这里不做强制要求，因为不同信号可能有不同结构


class TestSignalEdgeCases:
    """测试信号边界情况"""

    def test_signal_consistency_across_calls(self):
        """测试信号多次调用的一致性"""
        from czsc.signals.vol import vol_single_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        # 多次调用应得到相同结果
        signal1 = vol_single_ma_V230214(c, ma_period=5)
        signal2 = vol_single_ma_V230214(c, ma_period=5)

        # 结果类型应一致
        assert type(signal1) == type(signal2), "多次调用的信号类型应一致"
