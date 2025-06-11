# -*- coding: utf-8 -*-
"""
模拟数据生成模块
"""
import numpy as np
import pandas as pd
from czsc.utils.cache import disk_cache


@disk_cache(ttl=3600 * 24)
def generate_strategy_returns(n_strategies=10, n_days=None, seed=42):
    """生成多策略收益数据

    Args:
        n_strategies: 策略数量，默认10个
        n_days: 生成天数，None表示使用全部时间范围
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含策略收益数据的DataFrame，列包括dt、strategy、returns
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    if n_days and len(dates) > n_days:
        dates = dates[-n_days:]  # 取最近的n_days天
    data = []

    for i in range(n_strategies):
        strategy_name = f"策略_{i+1:02d}"
        # 生成具有不同特征的收益率
        base_return = np.random.normal(0.0005, 0.015, len(dates))
        if i % 3 == 0:  # 每3个策略中有一个表现更好
            base_return += np.random.normal(0.0002, 0.005, len(dates))

        for j, dt in enumerate(dates):
            data.append({"dt": dt, "strategy": strategy_name, "returns": base_return[j]})

    return pd.DataFrame(data)


@disk_cache(ttl=3600 * 24)
def generate_portfolio(seed=42):
    """生成组合数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含组合和基准收益数据的DataFrame，列包括dt、portfolio、benchmark
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    portfolio_returns = np.random.normal(0.0008, 0.012, len(dates))
    benchmark_returns = np.random.normal(0.0003, 0.010, len(dates))

    return pd.DataFrame({"dt": dates, "portfolio": portfolio_returns, "benchmark": benchmark_returns})


@disk_cache(ttl=3600 * 24)
def generate_weights(seed=42):
    """生成权重数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含权重数据的DataFrame，列包括dt、symbol、weight
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    data = []
    for dt in dates:
        # 生成随机权重，每日权重和为1
        weights = np.random.random(len(symbols))
        weights = weights / weights.sum()

        for i, symbol in enumerate(symbols):
            data.append({"dt": dt, "symbol": symbol, "weight": weights[i]})

    return pd.DataFrame(data)


@disk_cache(ttl=3600 * 24)
def generate_price_data(seed=42):
    """生成价格数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含价格数据的DataFrame，列包括symbol、dt、price
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    data = []
    for symbol in symbols:
        price = 100.0
        for dt in dates:
            price *= 1 + np.random.normal(0.0005, 0.02)
            data.append({"symbol": symbol, "dt": dt, "price": price})

    return pd.DataFrame(data)


@disk_cache(ttl=3600 * 24)
def generate_klines(seed=42):
    """生成K线数据，包含完整的OHLCVA信息（开高低收量额）

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含K线数据的DataFrame，列包括dt、symbol、open、close、high、low、vol、amount、weight、price
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    data = []
    for symbol in symbols:
        # 初始价格
        price = 100.0

        for i, dt in enumerate(dates):
            # 生成开盘价
            open_price = price * (1 + np.random.normal(0, 0.01))

            # 生成日内波动
            daily_return = np.random.normal(0.0005, 0.02)
            high_mult = 1 + abs(np.random.normal(0, 0.015))
            low_mult = 1 - abs(np.random.normal(0, 0.015))

            # 计算OHLC
            close_price = open_price * (1 + daily_return)
            high_price = max(open_price, close_price) * high_mult
            low_price = min(open_price, close_price) * low_mult

            # 成交量（随机生成）
            volume = np.random.randint(1000000, 10000000)

            # 成交金额（价格 * 成交量）
            amount = close_price * volume

            # 权重（简单均权或随机权重）
            weight = 1.0 / len(symbols) + np.random.normal(0, 0.02)
            weight = max(0.01, min(0.5, weight))  # 限制权重范围

            data.append(
                {
                    "dt": dt,
                    "symbol": symbol,
                    "open": round(open_price, 2),
                    "close": round(close_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "vol": volume,
                    "amount": round(amount, 2),  # 成交金额
                    "weight": round(weight, 4),
                    "price": round(close_price, 2),  # 用收盘价作为价格
                }
            )

            # 更新基准价格
            price = close_price

    return pd.DataFrame(data)


def set_global_seed(seed=42):
    """设置全局随机数种子

    Args:
        seed: 随机数种子，默认42

    Note:
        调用此函数后，所有使用numpy随机数的函数都会基于这个种子生成数据
        适用于需要统一设置种子的场景
    """
    np.random.seed(seed)


@disk_cache(ttl=3600 * 24)
def generate_factor_data(seed=42):
    """生成因子分析数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含因子和目标变量的DataFrame
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    data = []
    for symbol in symbols:
        for dt in dates:
            data.append(
                {
                    "dt": dt,
                    "symbol": symbol,
                    "factor1": np.random.normal(0, 1),
                    "factor2": np.random.normal(0, 1.5),
                    "factor3": np.random.normal(0, 0.8),
                    "target": np.random.normal(0.001, 0.02),
                    "price": 100 * (1 + np.random.normal(0.0005, 0.015)),
                    "volume": np.random.randint(1000000, 10000000),
                }
            )

    return pd.DataFrame(data)


@disk_cache(ttl=3600 * 24)
def generate_correlation_data(seed=42):
    """生成相关性分析数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含多个具有不同相关性的时间序列
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")

    # 创建具有不同相关性的序列
    base_series = np.random.normal(0, 1, len(dates))

    data = pd.DataFrame(
        {
            "dt": dates,
            "series_A": base_series,
            "series_B": 0.7 * base_series + 0.3 * np.random.normal(0, 1, len(dates)),
            "series_C": -0.5 * base_series + 0.5 * np.random.normal(0, 1, len(dates)),
            "series_D": np.random.normal(0, 1, len(dates)),
            "returns_A": np.random.normal(0.0008, 0.015, len(dates)),
            "returns_B": np.random.normal(0.0005, 0.012, len(dates)),
            "returns_C": np.random.normal(0.0003, 0.020, len(dates)),
        }
    )

    return data


@disk_cache(ttl=3600 * 24)
def generate_backtest_data(seed=42):
    """生成回测分析数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含交易记录的DataFrame
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    # 生成持仓数据
    holds_data = []
    for i in range(100):  # 生成100笔交易
        symbol = np.random.choice(symbols)
        entry_date = np.random.choice(dates)
        exit_date = entry_date + pd.Timedelta(days=np.random.randint(1, 30))

        entry_price = 100 + np.random.normal(0, 20)
        exit_price = entry_price * (1 + np.random.normal(0.02, 0.1))

        holds_data.append(
            {
                "symbol": symbol,
                "dt": entry_date,
                "price": entry_price,
                "exit_dt": exit_date,
                "exit_price": exit_price,
                "returns": (exit_price - entry_price) / entry_price,
                "hold_days": (exit_date - entry_date).days,
                "direction": np.random.choice(["多头", "空头"]),
                "max_drawdown": -abs(np.random.normal(0.05, 0.03)),
            }
        )

    return pd.DataFrame(holds_data)


@disk_cache(ttl=3600 * 24)
def generate_daily_returns(n_strategies=3, seed=42):
    """生成日收益数据用于收益分析

    Args:
        n_strategies: 策略数量，默认3个
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含多策略日收益的DataFrame，index为日期
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")

    data = {}
    for i in range(n_strategies):
        strategy_name = f"strategy_{chr(65+i)}"  # strategy_A, strategy_B, strategy_C
        # 生成具有不同风险收益特征的收益率
        if i == 0:  # 高收益高波动
            returns = np.random.normal(0.0008, 0.015, len(dates))
        elif i == 1:  # 中等收益中等波动
            returns = np.random.normal(0.0005, 0.012, len(dates))
        else:  # 低收益低波动
            returns = np.random.normal(0.0003, 0.010, len(dates))

        data[strategy_name] = returns

    # 添加基准
    data["benchmark"] = np.random.normal(0.0003, 0.010, len(dates))

    return pd.DataFrame(data, index=dates)


@disk_cache(ttl=3600 * 24)
def generate_statistics_data(seed=42):
    """生成统计分析数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含统计分析所需的多种数据
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")

    data = pd.DataFrame(
        {
            "dt": dates,
            "returns": np.random.normal(0.0008, 0.015, len(dates)),
            "factor1": np.random.normal(0, 1, len(dates)),
            "factor2": np.random.normal(0, 1.2, len(dates)),
            "category": np.random.choice(["A", "B", "C"], len(dates)),
            "volume": np.random.randint(1000000, 10000000, len(dates)),
            "price": np.cumsum(np.random.normal(0.1, 2, len(dates))) + 100,
        }
    )

    return data


@disk_cache(ttl=3600 * 24)
def generate_event_data(seed=42):
    """生成事件分析数据

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含事件和特征的DataFrame
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    data = []
    for symbol in symbols:
        for dt in dates:
            # 事件发生概率为20%
            event_occur = np.random.choice([0, 1], p=[0.8, 0.2])

            data.append(
                {
                    "dt": dt,
                    "symbol": symbol,
                    "event": event_occur,
                    "target": np.random.normal(0.001, 0.02),
                    "feature1": np.random.normal(0, 1),
                    "feature2": np.random.normal(0, 1.5),
                    "feature3": np.random.normal(0, 0.8),
                    "price_change": np.random.normal(0.0005, 0.015),
                }
            )

    return pd.DataFrame(data)
