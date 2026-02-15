# -*- coding: utf-8 -*-
"""
describe: czsc.signals 单元测试 - 信号生成函数
author: Claude Code
create_dt: 2026/2/15

Mock数据格式说明：
- 使用 czsc.mock.generate_symbol_kines 生成
- 日期范围：20200101-20250101（5年数据，满足3年+要求）
- K线格式：OHLCVA（开高低收成交量成交额）
- 频率：支持 1分钟、5分钟、15分钟、30分钟、日线

测试覆盖范围：
- bar.py: K线级别信号
- vol.py: 成交量信号
- cxt.py: 上下文信号
- tas.py: 技术指标信号
- pos.py: 持仓相关信号
"""
import pytest
from collections import OrderedDict
from czsc import mock
from czsc.core import CZSC, format_standard_kline, Freq


def get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101"):
    """获取CZSC分析对象（5年数据，满足3年+要求）

    Args:
        symbol: 品种代码
        freq: K线频率
        sdt: 开始日期，格式 YYYYMMDD
        edt: 结束日期，格式 YYYYMMDD

    Returns:
        CZSC: 缠论分析对象
    """
    df = mock.generate_symbol_kines(symbol, freq, sdt=sdt, edt=edt, seed=42)
    bars = format_standard_kline(df, freq=freq)
    return CZSC(bars)


def test_signals_module_import():
    """测试信号模块导入"""
    from czsc.signals import bar
    from czsc.signals import vol
    from czsc.signals import cxt
    from czsc.signals import tas
    from czsc.signals import pos

    assert hasattr(bar, 'is_third_buy'), "bar模块应该有 is_third_buy 函数"
    assert hasattr(vol, 'update_vol_ma_cache'), "vol模块应该有 update_vol_ma_cache 函数"
    assert hasattr(cxt, 'cxt_bi_base_V230228'), "cxt模块应该有 cxt_bi_base_V230228 函数"


def test_bar_signals():
    """测试K线级别信号"""
    from czsc.signals.bar import is_third_buy, is_third_sell, is_first_buy

    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101")

    # 测试三买信号
    result = is_third_buy(c)
    assert isinstance(result, bool), f"is_third_buy应该返回bool，实际为{type(result)}"

    # 测试三卖信号
    result = is_third_sell(c)
    assert isinstance(result, bool), f"is_third_sell应该返回bool，实际为{type(result)}"

    # 测试一买信号
    result = is_first_buy(c)
    assert isinstance(result, bool), f"is_first_buy应该返回bool，实际为{type(result)}"


def test_vol_signals():
    """测试成交量信号"""
    from czsc.signals.vol import vol_single_ma_V230214, vol_double_ma_V230214

    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101")

    # 测试单均线成交量信号
    result = vol_single_ma_V230214(c)
    assert isinstance(result, OrderedDict), f"vol_single_ma_V230214应该返回OrderedDict，实际为{type(result)}"
    assert 'key' in result, "信号结果应该包含key字段"
    assert 'value' in result, "信号结果应该包含value字段"

    # 测试双均线成交量信号
    result = vol_double_ma_V230214(c, ma_period=(5, 10))
    assert isinstance(result, OrderedDict), f"vol_double_ma_V230214应该返回OrderedDict，实际为{type(result)}"


def test_cxt_signals():
    """测试上下文信号"""
    from czsc.signals.cxt import cxt_bi_base_V230228, cxt_fx_power_V221107

    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101")

    # 测试笔基础信号
    result = cxt_bi_base_V230228(c)
    assert isinstance(result, OrderedDict), f"cxt_bi_base_V230228应该返回OrderedDict，实际为{type(result)}"
    assert 'key' in result, "信号结果应该包含key字段"
    assert 'value' in result, "信号结果应该包含value字段"

    # 测试分型力度信号
    result = cxt_fx_power_V221107(c)
    assert isinstance(result, OrderedDict), f"cxt_fx_power_V221107应该返回OrderedDict，实际为{type(result)}"


def test_tas_signals():
    """测试技术指标信号"""
    from czsc.signals.tas import tas_ma_base_V230224

    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101")

    # 测试均线基础信号
    result = tas_ma_base_V230224(c)
    assert isinstance(result, OrderedDict), f"tas_ma_base_V230224应该返回OrderedDict，实际为{type(result)}"


def test_signals_with_different_frequencies():
    """测试不同频率的信号生成"""
    from czsc.signals.bar import is_third_buy

    for freq_config in [("30分钟", Freq.F30), ("60分钟", Freq.F60), ("日线", Freq.D)]:
        freq_str, freq_enum = freq_config

        # 生成3年+的数据
        c = get_czsc_obj(symbol="000001", freq=freq_str, sdt="20200101", edt="20250101")

        # 测试信号生成
        result = is_third_buy(c)
        assert isinstance(result, bool), f"{freq_str}频率的is_third_buy应该返回bool"


def test_signals_edge_cases():
    """测试信号生成的边界情况"""
    from czsc.signals.bar import is_third_buy

    # 测试少量数据的情况（但仍满足3年要求）
    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20220101", edt="20250101")

    # 应该能够正常生成信号
    result = is_third_buy(c)
    assert isinstance(result, bool), "即使数据较少，也应该能正常处理"


def test_multiple_signals_combination():
    """测试多个信号组合使用"""
    from czsc.signals.bar import is_third_buy, is_third_sell
    from czsc.signals.vol import vol_single_ma_V230214

    c = get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101")

    # 获取多个信号
    third_buy = is_third_buy(c)
    third_sell = is_third_sell(c)
    vol_signal = vol_single_ma_V230214(c)

    # 验证信号类型
    assert isinstance(third_buy, bool)
    assert isinstance(third_sell, bool)
    assert isinstance(vol_signal, OrderedDict)

    # 验证信号逻辑（不应该同时出现三买和三卖）
    if third_buy and third_sell:
        pytest.fail("不应该同时出现三买和三卖信号")


def test_signals_with_different_symbols():
    """测试不同品种的信号生成"""
    from czsc.signals.bar import is_third_buy

    for symbol in ["000001", "000002", "600000"]:
        c = get_czsc_obj(symbol=symbol, freq="日线", sdt="20200101", edt="20250101")
        result = is_third_buy(c)
        assert isinstance(result, bool), f"{symbol}的信号生成应该正常"


def test_signal_result_consistency():
    """测试信号结果的一致性（同一数据多次生成应得到相同结果）"""
    from czsc.signals.bar import is_third_buy

    symbol = "000001"
    sdt = "20200101"
    edt = "20250101"

    # 第一次生成
    c1 = get_czsc_obj(symbol=symbol, freq="日线", sdt=sdt, edt=edt)
    result1 = is_third_buy(c1)

    # 第二次生成（使用相同seed）
    c2 = get_czsc_obj(symbol=symbol, freq="日线", sdt=sdt=sdt, edt=edt)
    result2 = is_third_buy(c2)

    # 结果应该一致
    assert result1 == result2, "相同数据应该生成一致的信号结果"
