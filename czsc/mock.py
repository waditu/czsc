# -*- coding: utf-8 -*-
"""
模拟数据生成模块
"""
import numpy as np
import pandas as pd
from czsc.utils.cache import disk_cache


def generate_symbol_kines(symbol, freq, sdt="20100101", edt="20250101", seed=42):
    """生成单个品种指定频率的K线数据

    Args:
        symbol: 品种代码，如 'AAPL', '000001.SH' 等
        freq: K线频率，支持 '1分钟', '5分钟', '15分钟', '30分钟', '日线'
        sdt: 开始日期，格式为 'YYYYMMDD'，默认 "20100101"
        edt: 结束日期，格式为 'YYYYMMDD'，默认 "20250101"
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含K线数据的DataFrame，列包括dt、symbol、open、close、high、low、vol、amount
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed + hash(symbol) % 1000)

    # 转换日期格式
    start_date = pd.to_datetime(sdt, format="%Y%m%d")
    end_date = pd.to_datetime(edt, format="%Y%m%d")

    # 根据频率生成时间序列
    if freq == "日线":
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
    elif freq in ["1分钟", "5分钟", "15分钟", "30分钟"]:
        # 先生成日期范围
        trading_days = pd.date_range(start=start_date, end=end_date, freq="D")
        dates = []

        # 获取分钟数
        freq_minutes = int(freq.replace("分钟", ""))

        # A股交易时间段
        morning_start = "09:30"
        morning_end = "11:30"
        afternoon_start = "13:00"
        afternoon_end = "15:00"

        for day in trading_days:
            # 上午交易时间
            morning_times = pd.date_range(
                start=f"{day.strftime('%Y-%m-%d')} {morning_start}",
                end=f"{day.strftime('%Y-%m-%d')} {morning_end}",
                freq=f"{freq_minutes}T",
            )

            # 下午交易时间
            afternoon_times = pd.date_range(
                start=f"{day.strftime('%Y-%m-%d')} {afternoon_start}",
                end=f"{day.strftime('%Y-%m-%d')} {afternoon_end}",
                freq=f"{freq_minutes}T",
            )

            dates.extend(morning_times.tolist())
            dates.extend(afternoon_times.tolist())

        dates = pd.DatetimeIndex(dates)
    else:
        raise ValueError(f"不支持的频率: {freq}。支持的频率: 1分钟, 5分钟, 15分钟, 30分钟, 日线")

    # 定义不同的市场阶段，模拟真实市场的周期性变化
    phases = [
        {"name": "熊市", "trend": -0.0008, "volatility": 0.025, "length": 0.3},
        {"name": "震荡", "trend": 0.0002, "volatility": 0.015, "length": 0.2},
        {"name": "牛市", "trend": 0.0012, "volatility": 0.02, "length": 0.3},
        {"name": "调整", "trend": -0.0005, "volatility": 0.02, "length": 0.2},
    ]

    # 初始价格
    base_price = 100.0

    # 市场阶段控制变量
    total_periods = len(dates)
    phase_idx = 0
    phase_periods = 0
    current_phase = phases[phase_idx]

    data = []

    for i, dt in enumerate(dates):
        # 切换市场阶段
        if phase_periods >= total_periods * current_phase["length"]:
            phase_idx = (phase_idx + 1) % len(phases)
            current_phase = phases[phase_idx]
            phase_periods = 0

        # 当前阶段的趋势和波动
        trend = current_phase["trend"]
        volatility = current_phase["volatility"]

        # 对于分钟级数据，调整趋势和波动率
        if freq != "日线":
            freq_minutes = int(freq.replace("分钟", ""))
            # 按分钟级别调整趋势和波动，使日内波动更合理
            trend = trend / (240 / freq_minutes)  # 240是一天的交易分钟数
            volatility = volatility / (240 / freq_minutes) ** 0.5

        # 添加周期性波动，模拟季节性等因素
        if freq == "日线":
            cycle_factor = np.sin(i / 30) * 0.001  # 30天周期
            annual_cycle = np.sin(i / 365) * 0.0005  # 年度周期
        else:
            # 分钟级别的周期性波动
            cycle_factor = np.sin(i / 120) * 0.0005  # 120分钟周期
            annual_cycle = np.sin(i / (365 * 240)) * 0.0002  # 年度周期

        # 随机噪音
        noise = np.random.normal(0, volatility)

        # 计算开盘价和收盘价
        open_price = base_price
        close_price = base_price * (1 + trend + cycle_factor + annual_cycle + noise)

        # 确保价格不会变为负数
        if close_price <= 0:
            close_price = base_price * 0.95

        # 计算日内波动范围，考虑市场波动的合理性
        price_change_ratio = abs(close_price - open_price) / open_price
        if freq == "日线":
            daily_range = base_price * (price_change_ratio + np.random.uniform(0.01, 0.04))
        else:
            # 分钟级别的波动范围更小
            daily_range = base_price * (price_change_ratio + np.random.uniform(0.001, 0.01))

        if close_price > open_price:  # 阳线
            high_price = close_price + daily_range * np.random.uniform(0.1, 0.5)
            low_price = open_price - daily_range * np.random.uniform(0.1, 0.3)
        else:  # 阴线
            high_price = open_price + daily_range * np.random.uniform(0.1, 0.3)
            low_price = close_price - daily_range * np.random.uniform(0.1, 0.5)

        # 确保价格关系正确：high >= max(open, close), low <= min(open, close)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        # 模拟成交量 - 价格波动大的时候成交量通常也大
        if freq == "日线":
            base_volume = np.random.uniform(100000, 300000)
        else:
            # 分钟级别的成交量更小
            freq_minutes = int(freq.replace("分钟", ""))
            base_volume = np.random.uniform(10000, 50000) * (freq_minutes / 5)  # 基于5分钟调整

        volatility_factor = price_change_ratio * 5  # 波动率影响成交量
        volume_multiplier = 1 + volatility_factor + np.random.uniform(-0.2, 0.2)
        volume = int(base_volume * max(volume_multiplier, 0.3))  # 确保成交量不会过小

        # 计算成交金额（使用平均价格）
        avg_price = (high_price + low_price + open_price + close_price) / 4
        amount = volume * avg_price

        data.append(
            {
                "dt": dt,
                "symbol": symbol,
                "open": round(open_price, 2),
                "close": round(close_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "vol": volume,
                "amount": round(amount, 2),
            }
        )

        # 更新基准价格为收盘价
        base_price = close_price
        phase_periods += 1

    return pd.DataFrame(data)


@disk_cache(ttl=3600 * 24)
def generate_klines(seed=42):
    """生成K线数据，包含完整的OHLCVA信息（开高低收量额）

    Args:
        seed: 随机数种子，确保结果可重现，默认42

    Returns:
        pd.DataFrame: 包含K线数据的DataFrame，列包括dt、symbol、open、close、high、low、vol、amount
    """
    # 设置随机数种子确保结果可重现
    np.random.seed(seed)

    dates = pd.date_range(start="2010-01-01", end="2025-06-08", freq="D")
    symbols = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "NFLX",
        "PYPL",
        "INTC",
        "CSCO",
        "IBM",
        "ORCL",
        "SAP",
        "BTC",
        "ETH",
        "000001",
    ]

    # 定义不同的市场阶段，模拟真实市场的周期性变化
    phases = [
        {"name": "熊市", "trend": -0.0008, "volatility": 0.025, "length": 0.3},
        {"name": "震荡", "trend": 0.0002, "volatility": 0.015, "length": 0.2},
        {"name": "牛市", "trend": 0.0012, "volatility": 0.02, "length": 0.3},
        {"name": "调整", "trend": -0.0005, "volatility": 0.02, "length": 0.2},
    ]

    data = []
    for symbol in symbols:
        # 初始价格
        base_price = 100.0

        # 为每个标的设置不同的种子偏移，确保不同标的有不同的走势
        symbol_seed = seed + hash(symbol) % 1000
        np.random.seed(symbol_seed)

        # 市场阶段控制变量
        total_days = len(dates)
        phase_idx = 0
        phase_days = 0
        current_phase = phases[phase_idx]

        for i, dt in enumerate(dates):
            # 切换市场阶段
            if phase_days >= total_days * current_phase["length"]:
                phase_idx = (phase_idx + 1) % len(phases)
                current_phase = phases[phase_idx]
                phase_days = 0

            # 当前阶段的趋势和波动
            trend = current_phase["trend"]
            volatility = current_phase["volatility"]

            # 添加周期性波动，模拟季节性等因素
            cycle_factor = np.sin(i / 30) * 0.001  # 30天周期

            # 添加长期周期，模拟年度周期
            annual_cycle = np.sin(i / 365) * 0.0005  # 年度周期

            # 随机噪音
            noise = np.random.normal(0, volatility)

            # 计算开盘价和收盘价
            open_price = base_price
            close_price = base_price * (1 + trend + cycle_factor + annual_cycle + noise)

            # 确保价格不会变为负数
            if close_price <= 0:
                close_price = base_price * 0.95

            # 计算日内波动范围，考虑市场波动的合理性
            price_change_ratio = abs(close_price - open_price) / open_price
            daily_range = base_price * (price_change_ratio + np.random.uniform(0.01, 0.04))

            if close_price > open_price:  # 阳线
                high_price = close_price + daily_range * np.random.uniform(0.1, 0.5)
                low_price = open_price - daily_range * np.random.uniform(0.1, 0.3)
            else:  # 阴线
                high_price = open_price + daily_range * np.random.uniform(0.1, 0.3)
                low_price = close_price - daily_range * np.random.uniform(0.1, 0.5)

            # 确保价格关系正确：high >= max(open, close), low <= min(open, close)
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            # 模拟成交量 - 价格波动大的时候成交量通常也大
            base_volume = np.random.uniform(100000, 300000)
            volatility_factor = price_change_ratio * 5  # 波动率影响成交量
            volume_multiplier = 1 + volatility_factor + np.random.uniform(-0.2, 0.2)
            volume = int(base_volume * max(volume_multiplier, 0.3))  # 确保成交量不会过小

            # 计算成交金额（使用平均价格）
            avg_price = (high_price + low_price + open_price + close_price) / 4
            amount = volume * avg_price

            data.append(
                {
                    "dt": dt,
                    "symbol": symbol,
                    "open": round(open_price, 2),
                    "close": round(close_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "vol": volume,
                    "amount": round(amount, 2),
                }
            )

            # 更新基准价格为收盘价
            base_price = close_price
            phase_days += 1

    return pd.DataFrame(data)


def generate_klines_with_weights(seed=42):
    """生成K线数据，包含权重信息"""
    df = generate_klines(seed)
    df["weight"] = np.random.normal(-1, 1, len(df))
    df["weight"] = df["weight"].clip(-1, 1)
    df["price"] = df["close"]
    return df


def generate_ts_factor(seed=42):
    """生成K线数据，包含权重信息"""
    df = generate_klines(seed)
    df["F#SMA#20"] = df.groupby("symbol")["close"].rolling(20).mean().reset_index(drop=True).fillna(0)
    return df


def generate_cs_factor(seed=42):
    """生成截面因子数据"""
    df = generate_klines(seed)
    df["ret20"] = df.groupby("symbol")["close"].pct_change(20).reset_index(drop=True).fillna(0)
    df["F#RPS#20"] = df.groupby("dt")["ret20"].rank(pct=True).reset_index(drop=True).fillna(0)
    df.drop(columns=["ret20"], inplace=True)
    return df


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
