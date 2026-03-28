"""
持仓权重转换工具（Polars 优化版本）

使用 Polars 重写 weights_convert.py 中的核心功能，在保持输入输出不变的前提下，
利用 Polars 更高效的分组、排序和内存布局来提升性能。

T+1 规则：
- T：交易日（Trading Day）
- T+1：T 日的下一个交易日
- 核心规则：T 日买入的股票，T+1 日起方可卖出
  即：T 日新增的持仓部分，只能在 T+1 日及以后才能卖出
  T 日可以卖出 T 日之前已有的持仓（不受限制）
"""

import numpy as np
import pandas as pd
import polars as pl


def weights_convert(weights_df: pd.DataFrame, rule: str = "t+1") -> pd.DataFrame:
    """权重数据转换工具（Polars 优化版本）

    Args:
        weights_df: 标准持仓权重DataFrame，包含列：
            - dt: 时间戳（datetime）
            - symbol: 品种代码（str）
            - weight: 持仓权重（float，范围-1到1）
        rule: 转换规则，支持：
            - 't+1': 转换为符合T+1交易规则的权重
            - 'none': 不转换，直接返回原数据

    Returns:
        转换后的DataFrame（pandas），格式与输入相同

    Raises:
        ValueError: 当 rule 参数不支持时，或输入数据格式不正确时
    """
    _validate_input(weights_df)

    if rule == "t+1":
        return _apply_t_plus_1_rule(weights_df)
    if rule == "none":
        return weights_df.copy()

    raise ValueError(f"不支持的转换规则: {rule}。支持的规则: 't+1', 'none'")


def _validate_input(weights_df: pd.DataFrame) -> None:
    """验证输入数据的格式和完整性"""
    required_columns = ["dt", "symbol", "weight"]
    missing_columns = [col for col in required_columns if col not in weights_df.columns]

    if missing_columns:
        raise ValueError(f"输入数据缺少必需的列: {missing_columns}")

    if len(weights_df) == 0:
        return

    if not pd.api.types.is_datetime64_any_dtype(weights_df["dt"]):
        raise ValueError("'dt' 列必须是 datetime 类型")

    if not pd.api.types.is_numeric_dtype(weights_df["weight"]):
        raise ValueError("'weight' 列必须是数值类型")


def _apply_t_plus_1_rule(weights_df: pd.DataFrame) -> pd.DataFrame:
    """应用T+1交易规则转换权重数据（Polars 优化版本）"""
    if len(weights_df) == 0:
        return weights_df.copy()

    # 保留额外列信息
    extra_cols = [c for c in weights_df.columns if c not in ("dt", "symbol", "weight")]

    # 转换为 Polars DataFrame（仅核心列）
    pldf = pl.from_pandas(weights_df[["dt", "symbol", "weight"]])

    # 添加原始索引和日期列
    pldf = pldf.with_row_index("__orig_idx__").with_columns(pl.col("dt").dt.date().alias("__date__"))

    # 按 symbol 分组，对每组应用 T+1 转换（使用 eager API）
    result = pldf.sort("dt").group_by("symbol", maintain_order=True).map_groups(_process_symbol_group)

    # 按原始顺序排序
    result = result.sort("__orig_idx__")

    # 转换回 pandas
    out = result.select(["dt", "symbol", "weight"]).to_pandas()

    # 恢复额外列
    if extra_cols:
        for col in extra_cols:
            out[col] = weights_df[col].values

    return out


def _process_symbol_group(group_df: pl.DataFrame) -> pl.DataFrame:
    """处理单个品种的 T+1 转换（向量化日期边界 + numpy 循环）"""
    dates = group_df["__date__"].to_numpy()
    weights = group_df["weight"].to_numpy().copy()

    n = len(weights)
    if n == 0:
        return group_df

    # 预计算日期变化位置
    date_changes = np.empty(n, dtype=np.bool_)
    date_changes[0] = True
    date_changes[1:] = dates[1:] != dates[:-1]

    # 核心 T+1 转换逻辑
    previous_close = 0.0
    locked_position = 0.0
    current_position = 0.0

    for i in range(n):
        if date_changes[i]:
            # 新的交易日开始
            previous_close = current_position if i > 0 else 0.0
            current_position = previous_close
            locked_position = 0.0

        target_weight = weights[i]

        if target_weight > current_position:
            buy_amount = target_weight - current_position
            locked_position += buy_amount
            current_position = target_weight
        elif target_weight < current_position:
            current_position = max(target_weight, locked_position)

        weights[i] = current_position

    return group_df.with_columns(pl.Series("weight", weights))
