# -*- coding: utf-8 -*-
"""
持仓权重转换工具

将分钟线上的标准持仓权重数据转换为符合 A 股 T+1 交易规则的持仓权重数据。

T+1 规则：
- T：交易日（Trading Day）
- T+1：T 日的下一个交易日
- 核心规则：T 日买入的股票，T+1 日起方可卖出
  即：T 日新增的持仓部分，只能在 T+1 日及以后才能卖出
  T 日可以卖出 T 日之前已有的持仓（不受限制）
"""
from typing import List

import numpy as np
import pandas as pd


def weights_convert(weights_df: pd.DataFrame, rule: str = "t+1") -> pd.DataFrame:
    """权重数据转换工具

    Args:
        weights_df: 标准持仓权重DataFrame，包含列：
            - dt: 时间戳（datetime）
            - symbol: 品种代码（str）
            - weight: 持仓权重（float，范围-1到1）
        rule: 转换规则，支持：
            - 't+1': 转换为符合T+1交易规则的权重
            - 'none': 不转换，直接返回原数据

    Returns:
        转换后的DataFrame，格式与输入相同

    Raises:
        ValueError: 当 rule 参数不支持时，或输入数据格式不正确时

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'dt': pd.to_datetime(['2024-01-01 09:30:00', '2024-01-01 10:00:00']),
        ...     'symbol': ['AAPL', 'AAPL'],
        ...     'weight': [0.0, 0.5]
        ... })
        >>> result = weights_convert(df, rule='t+1')
    """
    _validate_input(weights_df)

    if rule == "t+1":
        return _apply_t_plus_1_rule(weights_df)
    if rule == "none":
        return weights_df.copy()

    raise ValueError(f"不支持的转换规则: {rule}。支持的规则: 't+1', 'none'")


def _validate_input(weights_df: pd.DataFrame) -> None:
    """验证输入数据的格式和完整性

    Args:
        weights_df: 待验证的DataFrame

    Raises:
        ValueError: 当数据格式不正确时
    """
    required_columns = ["dt", "symbol", "weight"]
    missing_columns = [col for col in required_columns if col not in weights_df.columns]

    if missing_columns:
        raise ValueError(f"输入数据缺少必需的列: {missing_columns}")

    # 空DataFrame跳过类型检查
    if len(weights_df) == 0:
        return

    if not pd.api.types.is_datetime64_any_dtype(weights_df["dt"]):
        raise ValueError("'dt' 列必须是 datetime 类型")

    if not pd.api.types.is_numeric_dtype(weights_df["weight"]):
        raise ValueError("'weight' 列必须是数值类型")


def _apply_t_plus_1_rule(weights_df: pd.DataFrame) -> pd.DataFrame:
    """应用T+1交易规则转换权重数据

    T+1 规则：T 日买入的股票，T+1 日起方可卖出
    即：T 日新增的持仓部分，只能在 T+1 日及以后才能卖出

    Args:
        weights_df: 标准持仓权重DataFrame

    Returns:
        符合T+1规则的权重数据
    """
    if len(weights_df) == 0:
        return weights_df.copy()

    # 使用 groupby 处理每个品种
    results = []
    for symbol, group_df in weights_df.groupby("symbol"):
        converted = _convert_single_symbol_plus_1_rule(group_df.copy())
        results.append(converted)

    return pd.concat(results, ignore_index=True)


def _convert_single_symbol_plus_1_rule(df: pd.DataFrame) -> pd.DataFrame:
    """处理单个品种的T+1转换

    T+1 规则：T 日买入的股票，T+1 日起方可卖出
    即：T 日新增的持仓部分，只能在 T+1 日及以后才能卖出

    关键点：
    - 日内新买入的部分也不能在当天卖出
    - 需要追踪日内累计锁定的仓位

    场景：同一天内 0 → 0.5 → 0.2
    09:30 买入到 0.5，新买入了 0.5
    10:00 想减仓到 0.2，但 当天新买入的 0.5 不能在当天卖出
    因此 10:00 最小持仓应该是 0.5，而不是 0.2

    Args:
        df: 单个品种的权重数据

    Returns:
        转换后的权重数据
    """
    df = df.sort_values("dt").reset_index(drop=True)

    # 提取日期列
    dates: pd.Series = df["dt"].dt.date
    weights: np.ndarray = df["weight"].values.copy()

    # 获取唯一日期列表（按时间顺序）
    unique_dates: np.ndarray = dates.unique()

    # 初始状态
    previous_close: float = 0.0  # 前一日收盘权重

    # 按日期处理
    for current_date in unique_dates:
        # 获取当日数据的索引
        day_mask: np.ndarray = (dates == current_date).to_numpy()
        day_indices: np.ndarray = np.where(day_mask)[0]

        # 当日初始持仓 = 前一日收盘持仓
        current_position: float = previous_close
        # 当日锁定仓位（当天新买入的部分，不能卖）
        locked_position: float = 0.0

        # 逐个时刻处理当日数据
        for idx in day_indices:
            target_weight: float = weights[idx]

            if target_weight > current_position:
                # 加仓：新买入的部分加入锁定
                buy_amount: float = target_weight - current_position
                locked_position += buy_amount
                current_position = target_weight
            elif target_weight < current_position:
                # 减仓：不能低于锁定仓位
                actual_weight: float = max(target_weight, locked_position)
                current_position = actual_weight
            # else: 持仓不变，无需操作

            weights[idx] = current_position

        # 更新前一日收盘
        previous_close = current_position

    df["weight"] = weights
    return df
