# -*- coding: utf-8 -*-
"""
测试持仓权重转换工具

测试 A 股 T+1 交易规则：T 日买入的股票，T+1 日起方可卖出
"""
import numpy as np
import pandas as pd
import pytest

from czsc.utils.weights_convert import weights_convert


def generate_mock_weights(
    symbols: list,
    freq: str,
    sdt: str = "20240101",
    edt: str = "20240110",
    seed: int = 42,
) -> pd.DataFrame:
    """生成模拟持仓权重数据（仅用于测试）"""
    np.random.seed(seed)
    start_date = pd.to_datetime(sdt, format="%Y%m%d")
    end_date = pd.to_datetime(edt, format="%Y%m%d")
    dates = _generate_time_series(start_date, end_date, freq)

    data = []
    for symbol_idx, symbol in enumerate(symbols):
        symbol_seed = seed + symbol_idx * 100
        np.random.seed(symbol_seed)

        for dt in dates:
            weight = np.random.uniform(-0.5, 0.8)
            if np.random.random() < 0.2:
                weight = 0
            data.append({"dt": dt, "symbol": symbol, "weight": weight})

    return pd.DataFrame(data)


def _generate_time_series(start_date: pd.Timestamp, end_date: pd.Timestamp, freq: str) -> pd.DatetimeIndex:
    supported_freqs = ["1分钟", "5分钟", "15分钟", "30分钟"]
    if freq not in supported_freqs:
        raise ValueError(f"不支持的频率: {freq}。支持的频率: {', '.join(supported_freqs)}")

    trading_days = pd.date_range(start=start_date, end=end_date, freq="D")
    freq_minutes = int(freq.replace("分钟", ""))
    dates = []

    for day in trading_days:
        day_str = day.strftime("%Y-%m-%d")
        morning_times = pd.date_range(start=f"{day_str} 09:30", end=f"{day_str} 11:30", freq=f"{freq_minutes}min")
        afternoon_times = pd.date_range(start=f"{day_str} 13:00", end=f"{day_str} 15:00", freq=f"{freq_minutes}min")
        dates.extend(morning_times.tolist())
        dates.extend(afternoon_times.tolist())

    return pd.DatetimeIndex(dates)


# ==================== 核心 T+1 规则测试用例 ====================


def test_t_plus_1_basic_buy_next_day_sell():
    """测试基本的 T+1 规则：T 日买入，T+1 日可卖出"""
    data = {
        "dt": pd.to_datetime(
            [
                "2024-01-01 09:30:00",  # Day1 开仓
                "2024-01-01 15:00:00",  # Day1 收盘 0.5 (T日买入)
                "2024-01-02 09:30:00",  # Day2 尝试平仓到 0.0
                "2024-01-02 15:00:00",  # Day2 收盘
            ]
        ),
        "symbol": ["AAPL"] * 4,
        "weight": [0.0, 0.5, 0.0, 0.2],
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")

    # Day2 应该可以完全平仓到 0.0（Day1 新增的 0.5 在 Day2 可卖出）
    # 0.0 (old) -> 0.5 (new, locked today). Close 0.5.
    # Day2 Start: 0.5 (old).
    # 0.5 -> 0.0. Sell 0.5. OK.
    pd.testing.assert_series_equal(result["weight"], pd.Series([0.0, 0.5, 0.0, 0.2], name="weight"))


def test_t_plus_1_consecutive_days_buy_and_sell():
    """测试连续多日增仓后卖出

    场景：
    - Day1：0 → 0.3
    - Day2：0.3 → 0.6 (新增 0.3)
    - Day3：0.6 → 0.0

    分析：
    - Day 2 可以卖出 Day 1 的 0.3。但这里是增仓，所以没问题。
    - Day 3 可以卖出 Day 2 持有的 0.6 (Day 1 的 0.3 + Day 2 的 0.3)。
    - 因为 Day 2 的 0.3 是 T 日买入，Day 3 是 T+1 日，所以可卖。
    """
    data = {
        "dt": pd.to_datetime(
            [
                "2024-01-01 15:00:00",  # Day1 收盘 0.3
                "2024-01-02 15:00:00",  # Day2 收盘 0.6
                "2024-01-03 09:30:00",  # Day3 尝试降到 0.0
                "2024-01-03 15:00:00",
            ]
        ),
        "symbol": ["AAPL"] * 4,
        "weight": [0.3, 0.6, 0.0, 0.0],
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")

    # Day 3 应该可以完全卖出
    pd.testing.assert_series_equal(result["weight"], pd.Series([0.3, 0.6, 0.0, 0.0], name="weight"))


def test_t_plus_1_intraday_restriction():
    """测试日内 T+1 限制：当日买入当日不可卖

    场景：
    - 09:30: 0.0
    - 10:00: 0.5 (买入 0.5)
    - 11:00: 0.2 (尝试卖出 0.3)

    期望结果：
    - 11:00 时只能持有 0.5。因为 0.5 是当日新买入的，锁定了。
    """
    data = {
        "dt": pd.to_datetime(
            ["2024-01-01 09:30:00", "2024-01-01 10:00:00", "2024-01-01 11:00:00"]
        ),
        "symbol": ["AAPL"] * 3,
        "weight": [0.0, 0.5, 0.2],
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")

    # 11:00 应被强制维持在 0.5
    pd.testing.assert_series_equal(result["weight"], pd.Series([0.0, 0.5, 0.5], name="weight"))


def test_t_plus_0_rolling_buy_then_sell():
    """测试底仓做 T：先买后卖（T+0 滚动）

    场景：
    - Day 1: 0.5 (底仓)
    - Day 2 09:30: 0.5 (昨收)
    - Day 2 10:00: 0.8 (买入 0.3) -> 此时持仓 0.8 (0.5 老仓 + 0.3 新仓)
    - Day 2 11:00: 0.5 (卖出 0.3) -> 此时持仓 0.5 (0.2 老仓 + 0.3 新仓)
      - 这里的卖出是允许的，因为我们有 0.5 的老仓。
      - 卖出 0.3 后，还剩下 0.2 的老仓可用。
    - Day 2 14:00: 0.2 (再卖 0.3) -> 目标 0.2
      - 持仓 0.5 (0.2老 + 0.3新) -> 目标 0.2。需卖出 0.3。
      - 可用老仓只有 0.2。还缺 0.1。这 0.1 必须卖新仓，不允许。
      - 所以只能卖出 0.2 的老仓。
      - 最终持仓应该是 0.3 (即新仓的部分，完全不能动)。
    """
    data = {
        "dt": pd.to_datetime([
            "2024-01-01 15:00:00",
            "2024-01-02 09:30:00",
            "2024-01-02 10:00:00",  # 买入 0.3
            "2024-01-02 11:00:00",  # 卖出 0.3 (OK)
            "2024-01-02 14:00:00",  # 再卖 0.3 (Fail, limit to 0.3)
        ]),
        "symbol": ["AAPL"] * 5,
        "weight": [0.5, 0.5, 0.8, 0.5, 0.2]
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")

    # 注意：这里的预期值是 [0.5, 0.5, 0.8, 0.5, 0.3]
    # Day 2 开始 0.5 (老)。
    # 10:00 0.8 (新 0.3 locked). Current: 0.8. Locked: 0.3.
    # 11:00 0.5. Target 0.5. Max(0.5, 0.3) = 0.5. OK. Current: 0.5.
    # 14:00 0.2. Target 0.2. Max(0.2, 0.3) = 0.3. Converted to 0.3.
    expected = [0.5, 0.5, 0.8, 0.5, 0.3]
    pd.testing.assert_series_equal(result["weight"], pd.Series(expected, name="weight"))


def test_t_plus_0_rolling_sell_then_buy():
    """测试底仓做 T：先卖后买

    场景：
    - Day 1: 0.5
    - Day 2 09:30: 0.5
    - Day 2 10:00: 0.2 (卖出 0.3) -> 剩 0.2。允许 (卖老仓)。
    - Day 2 11:00: 0.5 (买回 0.3) -> 持 0.5 (0.2 老 + 0.3 新)。
    - Day 2 14:00: 0.2 (再卖 0.3) -> 目标 0.2。
      - 需卖 0.3。老仓只有 0.2。
      - 只能卖 0.2。保留 0.3 (新仓)。
    """
    data = {
        "dt": pd.to_datetime([
            "2024-01-01 15:00:00",
            "2024-01-02 09:30:00", # 0.5
            "2024-01-02 10:00:00", # 卖 0.3 -> 0.2
            "2024-01-02 11:00:00", # 买 0.3 -> 0.5
            "2024-01-02 14:00:00", # 卖 0.3 -> 0.2 (Limit to 0.3)
        ]),
        "symbol": ["AAPL"] * 5,
        "weight": [0.5, 0.5, 0.2, 0.5, 0.2]
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")

    # Day 2 Start 0.5. Locked 0.0.
    # 10:00 0.2. Sell. Max(0.2, 0) = 0.2. OK. Locked 0.
    # 11:00 0.5. Buy 0.3. Locked += 0.3 -> 0.3. Current 0.5.
    # 14:00 0.2. Sell. Max(0.2, 0.3) -> 0.3.
    expected = [0.5, 0.5, 0.2, 0.5, 0.3]
    pd.testing.assert_series_equal(result["weight"], pd.Series(expected, name="weight"))


def test_multi_day_complex_scenario():
    """复杂多日场景测试"""
    # Day 1: 买 0.5
    # Day 2: 卖 0.2 -> 0.3, 买 0.2 -> 0.5. (剩 0.3 老, 0.2 新)
    # Day 3: 全卖 -> 0.0. (OK)
    data = {
        "dt": pd.to_datetime([
            "2024-01-01 15:00:00", # Day 1 End: 0.5
            "2024-01-02 10:00:00", # Day 2 Sell: 0.3 (OK)
            "2024-01-02 14:00:00", # Day 2 Buy: 0.5 (Buy 0.2)
            "2024-01-03 10:00:00", # Day 3 Sell: 0.0 (OK)
        ]),
        "symbol": ["AAPL"] * 4,
        "weight": [0.5, 0.3, 0.5, 0.0]
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="t+1")
    
    pd.testing.assert_series_equal(result["weight"], df["weight"])


# ==================== 基础功能测试 ====================


def test_multiple_symbols():
    """测试多品种独立处理"""
    symbols_data = []
    # AAPL: 0 -> 0.5 -> 0.2 => 0.0, 0.5, 0.5
    # MSFT: 0 -> 0.5 -> 0.5 => 0.0, 0.5, 0.5
    for symbol in ["AAPL", "MSFT"]:
        data = {
            "dt": pd.to_datetime(
                ["2024-01-01 09:30:00", "2024-01-01 10:00:00", "2024-01-01 11:00:00"]
            ),
            "symbol": [symbol] * 3,
            "weight": [0.0, 0.5, 0.2],
        }
        symbols_data.append(pd.DataFrame(data))

    df = pd.concat(symbols_data, ignore_index=True)
    result = weights_convert(df, rule="t+1")

    for symbol in ["AAPL", "MSFT"]:
        symbol_df = result[result["symbol"] == symbol]
        # 0.2 -> 0.5 (constrained)
        assert symbol_df.iloc[2]["weight"] == 0.5


def test_empty_dataframe():
    """测试空 DataFrame"""
    df = pd.DataFrame(columns=["dt", "symbol", "weight"])
    df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    df["weight"] = df["weight"].astype(float)
    result = weights_convert(df, rule="t+1")
    assert len(result) == 0


def test_rule_none():
    """测试 rule='none'"""
    data = {
        "dt": pd.to_datetime(["2024-01-01 09:30:00", "2024-01-01 10:00:00"]),
        "symbol": ["AAPL"] * 2,
        "weight": [0.0, 0.5],
    }
    df = pd.DataFrame(data)
    result = weights_convert(df, rule="none")
    pd.testing.assert_frame_equal(result, df)


def test_invalid_input():
    df = pd.DataFrame(columns=["dt", "symbol", "weight"])
    with pytest.raises(ValueError, match="不支持的转换规则"):
        weights_convert(df, rule="invalid")
