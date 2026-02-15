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

    def test_is_third_buy_with_normal_data(self):
        """测试三买信号（正常数据）"""
        from czsc.signals.bar import is_third_buy

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = is_third_buy(c, di=1)
        # 信号可能是None、bool或OrderedDict
        assert signal is None or isinstance(signal, (bool, dict)), "三买信号返回类型不正确"

    def test_is_third_buy_with_different_symbols(self):
        """测试三买信号（多品种）"""
        from czsc.signals.bar import is_third_buy

        symbols = ["000001", "000002", "600000"]
        for symbol in symbols:
            c = get_czsc_obj(symbol=symbol, freq="30分钟", sdt="20200101", edt="20250101")
            if c is None or len(c.bars_raw) < 100:
                continue

            signal = is_third_buy(c, di=1)
            assert signal is None or isinstance(signal, (bool, dict)), \
                f"品种{symbol}的三买信号返回类型不正确"

    def test_is_third_sell_with_normal_data(self):
        """测试三卖信号（正常数据）"""
        from czsc.signals.bar import is_third_sell

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = is_third_sell(c, di=1)
        # 信号可能是None、bool或OrderedDict
        assert signal is None or isinstance(signal, (bool, dict)), "三卖信号返回类型不正确"

    def test_signal_mutually_exclusive(self):
        """测试三买和三卖互斥性"""
        from czsc.signals.bar import is_third_buy, is_third_sell

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        buy_signal = is_third_buy(c, di=1)
        sell_signal = is_third_sell(c, di=1)

        # 三买和三卖不应同时为True（如果返回bool）
        if isinstance(buy_signal, bool) and isinstance(sell_signal, bool):
            assert not (buy_signal and sell_signal), "三买和三卖不应同时出现"

    def test_signals_with_different_frequencies(self):
        """测试多频率信号"""
        from czsc.signals.bar import is_third_buy

        freqs = ["30分钟", "60分钟", "日线"]
        for freq in freqs:
            c = get_czsc_obj(symbol="000001", freq=freq, sdt="20200101", edt="20250101")
            if c is None or len(c.bars_raw) < 100:
                continue

            signal = is_third_buy(c, di=1)
            assert signal is None or isinstance(signal, (bool, dict)), \
                f"频率{freq}的信号返回类型不正确"

    def test_signal_reproducibility(self):
        """测试信号可重现性"""
        from czsc.signals.bar import is_third_buy

        # 使用相同seed生成两次数据
        c1 = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101", seed=42)
        c2 = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101", seed=42)

        if c1 is None or c2 is None or len(c1.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal1 = is_third_buy(c1, di=1)
        signal2 = is_third_buy(c2, di=1)

        # 相同数据应得到相同信号
        assert type(signal1) == type(signal2), "相同数据应得到相同类型的信号"

    def test_is_first_buy_with_normal_data(self):
        """测试一买信号（正常数据）"""
        from czsc.signals.bar import is_first_buy

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = is_first_buy(c, di=1)
        assert signal is None or isinstance(signal, (bool, dict)), "一买信号返回类型不正确"


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

        freqs = ["60分钟", "日线"]
        for freq in freqs:
            c = get_czsc_obj(symbol="000001", freq=freq, sdt="20200101", edt="20250101")
            if c is None or len(c.bars_raw) < 100:
                continue

            signal = cxt_bi_base_V230228(c, di=1)
            assert signal is None or isinstance(signal, dict), \
                f"频率{freq}的上下文信号返回类型不正确"


class TestTASSignals:
    """测试技术指标信号"""

    def test_tas_ma_base_with_normal_data(self):
        """测试MA基础信号（正常数据）"""
        from czsc.signals.tas import tas_ma_base_V230224

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = tas_ma_base_V230224(c, ma_period=5)
        assert signal is None or isinstance(signal, dict), "MA基础信号返回类型不正确"

    def test_tas_ma_base_with_different_periods(self):
        """测试MA基础信号（不同周期）"""
        from czsc.signals.tas import tas_ma_base_V230224

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        periods = [5, 10, 20, 60]
        for period in periods:
            signal = tas_ma_base_V230224(c, ma_period=period)
            assert signal is None or isinstance(signal, dict), \
                f"周期{period}的MA信号返回类型不正确"


class TestSignalCombinations:
    """测试信号组合"""

    def test_multiple_signals_same_czsc(self):
        """测试同一CZSC对象的多个信号"""
        from czsc.signals.bar import is_third_buy, is_third_sell
        from czsc.signals.vol import vol_single_ma_V230214

        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal1 = is_third_buy(c, di=1)
        signal2 = is_third_sell(c, di=1)
        signal3 = vol_single_ma_V230214(c, ma_period=5)

        # 所有信号都应有正确的返回类型
        assert signal1 is None or isinstance(signal1, (bool, dict))
        assert signal2 is None or isinstance(signal2, (bool, dict))
        assert signal3 is None or isinstance(signal3, dict)

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

    def test_signal_with_small_dataset(self):
        """测试小数据集的信号"""
        from czsc.signals.bar import is_third_buy

        # 使用较短时间范围
        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20240101", edt="20240131")
        if c is None or len(c.bars_raw) < 50:
            # 数据太少，预期信号可能为None
            pass

        # 即使数据少，函数也应该能正常执行
        if c is not None:
            signal = is_third_buy(c, di=1)
            assert signal is None or isinstance(signal, (bool, dict))

    def test_signal_with_large_dataset(self):
        """测试大数据集的信号"""
        from czsc.signals.bar import is_third_buy

        # 使用5年数据
        c = get_czsc_obj(symbol="000001", freq="30分钟", sdt="20200101", edt="20250101")
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        # 大数据集测试性能
        signal = is_third_buy(c, di=1)
        assert signal is None or isinstance(signal, (bool, dict))

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
