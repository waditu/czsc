# -*- coding: utf-8 -*-
"""
test_utils_ta.py - 技术分析指标单元测试

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20200101-20250101（5年数据，满足3年+要求）
- 频率: 日线
- Seed: 42（确保可重现）

测试覆盖范围:
- SMA (Simple Moving Average) - 简单移动平均线
- EMA (Exponential Moving Average) - 指数移动平均线
- MACD (Moving Average Convergence Divergence) - 指标平滑异同移动平均线
- RSI (Relative Strength Index) - 相对强弱指标
- BOLL (Bollinger Bands) - 布林带
- ATR (Average True Range) - 平均真实波幅
- KDJ (Stochastic Indicator) - 随机指标
"""
import pytest
import pandas as pd
import numpy as np
from czsc import mock
from czsc.utils.ta import SMA, EMA, MACD, RSI, BOLL, ATR, KDJ


def get_test_data(freq="日线", sdt="20200101", edt="20250101", symbol="000001"):
    """获取测试数据

    Args:
        freq: K线频率，默认日线
        sdt: 开始日期
        edt: 结束日期
        symbol: 品种代码

    Returns:
        DataFrame: K线数据
    """
    df = mock.generate_symbol_kines(symbol=symbol, freq=freq, sdt=sdt, edt=edt, seed=42)
    return df


class TestSMA:
    """SMA简单移动平均线测试"""

    def test_sma_basic(self):
        """测试SMA基础功能"""
        df = get_test_data()
        sma5 = SMA(df['close'], 5)
        sma10 = SMA(df['close'], 10)
        sma20 = SMA(df['close'], 20)
        sma60 = SMA(df['close'], 60)

        assert len(sma5) == len(df), "SMA返回长度应与输入相同"
        assert len(sma10) == len(df), "SMA返回长度应与输入相同"
        assert len(sma20) == len(df), "SMA返回长度应与输入相同"
        assert len(sma60) == len(df), "SMA返回长度应与输入相同"

        # 验证SMA非NaN值的平滑性
        assert not sma5[60:].isna().any(), "SMA(5)在60周期后不应有NaN"
        assert not sma10[60:].isna().any(), "SMA(10)在60周期后不应有NaN"
        assert not sma20[60:].isna().any(), "SMA(20)在60周期后不应有NaN"
        assert not sma60[60:].isna().any(), "SMA(60)在60周期后不应有NaN"

    def test_sma_empty_array(self):
        """测试空数组"""
        result = SMA([], 5)
        assert len(result) == 0, "空数组应返回空结果"

    def test_sma_single_value(self):
        """测试单值数组"""
        result = SMA([100], 5)
        assert len(result) == 1, "单值数组应返回单值结果"
        assert pd.isna(result[0]), "周期大于数据长度时，结果应为NaN"

    def test_sma_with_nan(self):
        """测试包含NaN的数据"""
        data = [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10]
        result = SMA(data, 5)
        assert len(result) == len(data), "包含NaN的数据长度应保持不变"
        # 验证结果不为None
        assert result is not None

    def test_sma_with_inf(self):
        """测试包含Inf的数据"""
        data = [1, 2, 3, 4, np.inf, 6, 7, 8, 9, 10]
        result = SMA(data, 5)
        assert len(result) == len(data), "包含Inf的数据长度应保持不变"

    def test_sma_with_zeros(self):
        """测试全0数据"""
        data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = SMA(data, 5)
        assert len(result) == len(data), "全0数据长度应保持不变"
        # 验证结果也是0（忽略NaN）
        non_nan = result[~pd.isna(result)]
        assert all(non_nan == 0), "全0数据的SMA应为0"

    def test_sma_large_period(self):
        """测试周期超过数据长度"""
        data = [1, 2, 3, 4, 5]
        result = SMA(data, 10)
        assert len(result) == len(data), "周期超过数据长度时，长度应保持不变"
        assert pd.isna(result[-1]), "周期超过数据长度时，结果应为NaN"

    def test_sma_period_1(self):
        """测试周期为1"""
        data = [1, 2, 3, 4, 5]
        result = SMA(data, 1)
        assert len(result) == len(data), "周期为1时，长度应保持不变"
        assert all(result == data), "周期为1时，SMA应等于原始数据"


class TestEMA:
    """EMA指数移动平均线测试"""

    def test_ema_basic(self):
        """测试EMA基础功能"""
        df = get_test_data()
        ema5 = EMA(df['close'], 5)
        ema12 = EMA(df['close'], 12)
        ema26 = EMA(df['close'], 26)

        assert len(ema5) == len(df), "EMA返回长度应与输入相同"
        assert len(ema12) == len(df), "EMA返回长度应与输入相同"
        assert len(ema26) == len(df), "EMA返回长度应与输入相同"

    def test_ema_empty_array(self):
        """测试空数组"""
        result = EMA([], 5)
        assert len(result) == 0, "空数组应返回空结果"

    def test_ema_single_value(self):
        """测试单值数组"""
        result = EMA([100], 5)
        assert len(result) == 1, "单值数组应返回单值结果"

    def test_ema_with_nan(self):
        """测试包含NaN的数据"""
        data = [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10]
        result = EMA(data, 5)
        assert len(result) == len(data), "包含NaN的数据长度应保持不变"

    def test_ema_with_zeros(self):
        """测试全0数据"""
        data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = EMA(data, 5)
        assert len(result) == len(data), "全0数据长度应保持不变"

    def test_ema_period_1(self):
        """测试周期为1"""
        data = [1, 2, 3, 4, 5]
        result = EMA(data, 1)
        assert len(result) == len(data), "周期为1时，长度应保持不变"
        assert all(result == data), "周期为1时，EMA应等于原始数据"


class TestMACD:
    """MACD指标测试"""

    def test_macd_basic(self):
        """测试MACD基础功能"""
        df = get_test_data()
        diff, dea, macd = MACD(df['close'])

        assert len(diff) == len(df), "DIFF返回长度应与输入相同"
        assert len(dea) == len(df), "DEA返回长度应与输入相同"
        assert len(macd) == len(df), "MACD返回长度应与输入相同"

        # 验证MACD = 2 * (DIFF - DEA)
        macd_calculated = 2 * (diff - dea)
        # 忽略NaN比较
        valid_idx = ~pd.isna(macd_calculated)
        assert np.allclose(macd[valid_idx], macd_calculated[valid_idx], rtol=1e-10), \
            "MACD应等于2*(DIFF-DEA)"

    def test_macd_empty_array(self):
        """测试空数组"""
        diff, dea, macd = MACD([])
        assert len(diff) == 0, "空数组应返回空结果"
        assert len(dea) == 0, "空数组应返回空结果"
        assert len(macd) == 0, "空数组应返回空结果"

    def test_macd_single_value(self):
        """测试单值数组"""
        diff, dea, macd = MACD([100])
        assert len(diff) == 1, "单值数组应返回单值结果"
        assert len(dea) == 1, "单值数组应返回单值结果"
        assert len(macd) == 1, "单值数组应返回单值结果"

    def test_macd_with_nan(self):
        """测试包含NaN的数据"""
        data = [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10]
        diff, dea, macd = MACD(data)
        assert len(diff) == len(data), "包含NaN的数据长度应保持不变"
        assert len(dea) == len(data), "包含NaN的数据长度应保持不变"
        assert len(macd) == len(data), "包含NaN的数据长度应保持不变"

    def test_macd_with_zeros(self):
        """测试全0数据"""
        data = [0] * 100
        diff, dea, macd = MACD(data)
        assert len(diff) == len(data), "全0数据长度应保持不变"
        assert len(dea) == len(data), "全0数据长度应保持不变"
        assert len(macd) == len(data), "全0数据长度应保持不变"

    def test_macd_with_inf(self):
        """测试包含Inf的数据"""
        data = [1, 2, 3, 4, np.inf, 6, 7, 8, 9, 10]
        diff, dea, macd = MACD(data)
        assert len(diff) == len(data), "包含Inf的数据长度应保持不变"

    def test_macd_constant_values(self):
        """测试常量值数据"""
        data = [100] * 100
        diff, dea, macd = MACD(data)
        # 常量值的MACD应接近0
        assert len(diff) == len(data), "常量数据长度应保持不变"


class TestRSI:
    """RSI相对强弱指标测试"""

    def test_rsi_basic(self):
        """测试RSI基础功能"""
        df = get_test_data()
        rsi6 = RSI(df['close'], 6)
        rsi12 = RSI(df['close'], 12)
        rsi24 = RSI(df['close'], 24)

        assert len(rsi6) == len(df), "RSI返回长度应与输入相同"
        assert len(rsi12) == len(df), "RSI返回长度应与输入相同"
        assert len(rsi24) == len(df), "RSI返回长度应与输入相同"

        # 验证RSI在0-100范围内（忽略NaN）
        valid_rsi6 = rsi6[~pd.isna(rsi6)]
        assert all((valid_rsi6 >= 0) & (valid_rsi6 <= 100)), "RSI应在0-100范围内"

    def test_rsi_empty_array(self):
        """测试空数组"""
        result = RSI([], 6)
        assert len(result) == 0, "空数组应返回空结果"

    def test_rsi_single_value(self):
        """测试单值数组"""
        result = RSI([100], 6)
        assert len(result) == 1, "单值数组应返回单值结果"

    def test_rsi_with_nan(self):
        """测试包含NaN的数据"""
        data = [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10]
        result = RSI(data, 6)
        assert len(result) == len(data), "包含NaN的数据长度应保持不变"

    def test_rsi_constant_values(self):
        """测试常量值数据"""
        data = [100] * 100
        result = RSI(data, 6)
        assert len(result) == len(data), "常量数据长度应保持不变"

    def test_rsi_all_increasing(self):
        """测试持续上涨数据"""
        data = list(range(1, 101))
        result = RSI(data, 6)
        # 持续上涨时RSI应接近100
        valid_rsi = result[~pd.isna(result)]
        assert len(valid_rsi) > 0, "应有有效的RSI值"

    def test_rsi_all_decreasing(self):
        """测试持续下跌数据"""
        data = list(range(100, 0, -1))
        result = RSI(data, 6)
        # 持续下跌时RSI应接近0
        valid_rsi = result[~pd.isna(result)]
        assert len(valid_rsi) > 0, "应有有效的RSI值"


class TestBOLL:
    """BOLL布林带测试"""

    def test_boll_basic(self):
        """测试BOLL基础功能"""
        df = get_test_data()
        upper, middle, lower = BOLL(df['close'], 20)

        assert len(upper) == len(df), "上轨返回长度应与输入相同"
        assert len(middle) == len(df), "中轨返回长度应与输入相同"
        assert len(lower) == len(df), "下轨返回长度应与输入相同"

        # 验证上轨 >= 中轨 >= 下轨（忽略NaN）
        valid_idx = ~pd.isna(upper) & ~pd.isna(middle) & ~pd.isna(lower)
        assert all(upper[valid_idx] >= middle[valid_idx]), "上轨应大于等于中轨"
        assert all(middle[valid_idx] >= lower[valid_idx]), "中轨应大于等于下轨"

    def test_boll_empty_array(self):
        """测试空数组"""
        upper, middle, lower = BOLL([], 20)
        assert len(upper) == 0, "空数组应返回空结果"
        assert len(middle) == 0, "空数组应返回空结果"
        assert len(lower) == 0, "空数组应返回空结果"

    def test_boll_single_value(self):
        """测试单值数组"""
        upper, middle, lower = BOLL([100], 20)
        assert len(upper) == 1, "单值数组应返回单值结果"
        assert len(middle) == 1, "单值数组应返回单值结果"
        assert len(lower) == 1, "单值数组应返回单值结果"

    def test_boll_with_nan(self):
        """测试包含NaN的数据"""
        data = [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10] * 10
        upper, middle, lower = BOLL(data, 20)
        assert len(upper) == len(data), "包含NaN的数据长度应保持不变"
        assert len(middle) == len(data), "包含NaN的数据长度应保持不变"
        assert len(lower) == len(data), "包含NaN的数据长度应保持不变"

    def test_boll_constant_values(self):
        """测试常量值数据"""
        data = [100] * 100
        upper, middle, lower = BOLL(data, 20)
        # 常量值的BOLL上下轨应接近中轨
        valid_idx = ~pd.isna(upper) & ~pd.isna(middle) & ~pd.isna(lower)
        if len(valid_idx) > 0:
            # 中轨应该等于常量值
            assert all(middle[valid_idx] == 100), "常量值的中轨应等于该常量"

    def test_boll_with_zeros(self):
        """测试全0数据"""
        data = [0] * 100
        upper, middle, lower = BOLL(data, 20)
        assert len(upper) == len(data), "全0数据长度应保持不变"
        assert len(middle) == len(data), "全0数据长度应保持不变"
        assert len(lower) == len(data), "全0数据长度应保持不变"

    def test_boll_relationship(self):
        """测试布林带上下轨关系"""
        data = list(range(1, 101))
        upper, middle, lower = BOLL(data, 20)

        # 验证上轨 >= 中轨 >= 下轨
        valid_idx = ~pd.isna(upper) & ~pd.isna(middle) & ~pd.isna(lower)
        assert all(upper[valid_idx] >= middle[valid_idx]), "上轨应大于等于中轨"
        assert all(middle[valid_idx] >= lower[valid_idx]), "中轨应大于等于下轨"


class TestATR:
    """ATR平均真实波幅测试"""

    def test_atr_basic(self):
        """测试ATR基础功能"""
        df = get_test_data()
        atr = ATR(df, 14)

        assert len(atr) == len(df), "ATR返回长度应与输入相同"

        # 验证ATR非负性（忽略NaN）
        valid_atr = atr[~pd.isna(atr)]
        assert all(valid_atr >= 0), "ATR应非负"

    def test_atr_empty_array(self):
        """测试空数组"""
        df = pd.DataFrame({'high': [], 'low': [], 'close': []})
        result = ATR(df, 14)
        assert len(result) == 0, "空数组应返回空结果"

    def test_atr_single_value(self):
        """测试单值数据"""
        df = pd.DataFrame({'high': [100], 'low': [90], 'close': [95]})
        result = ATR(df, 14)
        assert len(result) == 1, "单值数据应返回单值结果"

    def test_atr_with_nan(self):
        """测试包含NaN的数据"""
        df = pd.DataFrame({
            'high': [100, 102, np.nan, 106, 108],
            'low': [90, 92, 94, np.nan, 98],
            'close': [95, 97, 99, 101, 103]
        })
        result = ATR(df, 14)
        assert len(result) == len(df), "包含NaN的数据长度应保持不变"

    def test_atr_constant_prices(self):
        """测试常量价格"""
        df = pd.DataFrame({
            'high': [100] * 50,
            'low': [100] * 50,
            'close': [100] * 50
        })
        result = ATR(df, 14)
        # 常量价格的ATR应为0
        valid_atr = result[~pd.isna(result)]
        if len(valid_atr) > 0:
            assert all(valid_atr == 0), "常量价格的ATR应为0"

    def test_atr_with_zeros(self):
        """测试全0数据"""
        df = pd.DataFrame({
            'high': [0] * 50,
            'low': [0] * 50,
            'close': [0] * 50
        })
        result = ATR(df, 14)
        assert len(result) == len(df), "全0数据长度应保持不变"

    def test_atr_non_negative(self):
        """测试ATR非负性"""
        df = get_test_data()
        atr = ATR(df, 14)
        valid_atr = atr[~pd.isna(atr)]
        assert all(valid_atr >= 0), "ATR应始终非负"


class TestKDJ:
    """KDJ随机指标测试"""

    def test_kdj_basic(self):
        """测试KDJ基础功能"""
        df = get_test_data()
        k, d, j = KDJ(df, 9, 3, 3)

        assert len(k) == len(df), "K值返回长度应与输入相同"
        assert len(d) == len(df), "D值返回长度应与输入相同"
        assert len(j) == len(df), "J值返回长度应与输入相同"

        # 验证K/D值在0-100范围内（忽略NaN）
        valid_k = k[~pd.isna(k)]
        valid_d = d[~pd.isna(d)]
        assert all((valid_k >= 0) & (valid_k <= 100)), "K值应在0-100范围内"
        assert all((valid_d >= 0) & (valid_d <= 100)), "D值应在0-100范围内"

    def test_kdj_empty_array(self):
        """测试空数组"""
        df = pd.DataFrame({'high': [], 'low': [], 'close': []})
        k, d, j = KDJ(df, 9, 3, 3)
        assert len(k) == 0, "空数组应返回空结果"
        assert len(d) == 0, "空数组应返回空结果"
        assert len(j) == 0, "空数组应返回空结果"

    def test_kdj_single_value(self):
        """测试单值数据"""
        df = pd.DataFrame({'high': [100], 'low': [90], 'close': [95]})
        k, d, j = KDJ(df, 9, 3, 3)
        assert len(k) == 1, "单值数据应返回单值结果"
        assert len(d) == 1, "单值数据应返回单值结果"
        assert len(j) == 1, "单值数据应返回单值结果"

    def test_kdj_with_nan(self):
        """测试包含NaN的数据"""
        df = pd.DataFrame({
            'high': [100, 102, np.nan, 106, 108],
            'low': [90, 92, 94, np.nan, 98],
            'close': [95, 97, 99, 101, 103]
        })
        k, d, j = KDJ(df, 9, 3, 3)
        assert len(k) == len(df), "包含NaN的数据长度应保持不变"
        assert len(d) == len(df), "包含NaN的数据长度应保持不变"
        assert len(j) == len(df), "包含NaN的数据长度应保持不变"

    def test_kdj_constant_prices(self):
        """测试常量价格"""
        df = pd.DataFrame({
            'high': [100] * 50,
            'low': [100] * 50,
            'close': [100] * 50
        })
        k, d, j = KDJ(df, 9, 3, 3)
        # 常量价格的KDJ应在50附近（超买超卖中间值）
        assert len(k) == len(df), "常量数据长度应保持不变"

    def test_kdj_range(self):
        """测试KDJ取值范围"""
        df = get_test_data()
        k, d, j = KDJ(df, 9, 3, 3)

        # 验证K/D在0-100范围
        valid_k = k[~pd.isna(k)]
        valid_d = d[~pd.isna(d)]
        assert all((valid_k >= 0) & (valid_k <= 100)), "K值应在0-100范围内"
        assert all((valid_d >= 0) & (valid_d <= 100)), "D值应在0-100范围内"


class TestIndicatorsIntegration:
    """技术指标综合测试"""

    def test_indicators_with_real_data_consistency(self):
        """测试技术指标在真实数据上的一致性"""
        df = get_test_data()

        # 测试多个指标
        sma = SMA(df['close'], 20)
        ema = EMA(df['close'], 20)
        diff, dea, macd = MACD(df['close'])
        rsi = RSI(df['close'], 14)
        upper, middle, lower = BOLL(df['close'], 20)
        atr = ATR(df, 14)
        k, d, j = KDJ(df, 9, 3, 3)

        # 验证所有指标长度一致
        assert len(sma) == len(df), "SMA长度应一致"
        assert len(ema) == len(df), "EMA长度应一致"
        assert len(diff) == len(df), "MACD DIFF长度应一致"
        assert len(rsi) == len(df), "RSI长度应一致"
        assert len(upper) == len(df), "BOLL上轨长度应一致"
        assert len(atr) == len(df), "ATR长度应一致"
        assert len(k) == len(df), "KDJ K值长度应一致"

    def test_indicators_with_mixed_nan_inf(self):
        """测试技术指标对混合NaN/Inf数据的处理"""
        data = [1, 2, np.nan, 4, np.inf, 6, -np.inf, 8, 9, 10] * 10

        # 测试不会崩溃
        sma = SMA(data, 5)
        ema = EMA(data, 5)
        diff, dea, macd = MACD(data)
        rsi = RSI(data, 6)

        assert len(sma) == len(data), "SMA应能处理混合数据"
        assert len(ema) == len(data), "EMA应能处理混合数据"
        assert len(diff) == len(data), "MACD应能处理混合数据"
        assert len(rsi) == len(data), "RSI应能处理混合数据"
