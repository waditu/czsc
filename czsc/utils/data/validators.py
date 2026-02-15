"""
数据验证工具

提取的通用数据验证逻辑
"""

import pandas as pd
from typing import List, Optional
from loguru import logger


def validate_dataframe_columns(
    df: pd.DataFrame,
    required_columns: List[str],
    name: str = "DataFrame"
) -> None:
    """验证DataFrame包含所有必需的列

    :param df: 要验证的DataFrame
    :param required_columns: 必需的列名列表
    :param name: DataFrame的名称，用于错误消息
    :raises ValueError: 如果缺少必需的列
    """
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{name} 缺少必需的列: {missing_columns}. "
            f"当前列: {list(df.columns)}"
        )


def validate_datetime_index(
    df: pd.DataFrame,
    name: str = "DataFrame"
) -> None:
    """验证DataFrame的索引是DatetimeIndex

    :param df: 要验证的DataFrame
    :param name: DataFrame的名称，用于错误消息
    :raises ValueError: 如果索引不是DatetimeIndex
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            f"{name} 的索引必须是 DatetimeIndex, "
            f"当前类型: {type(df.index)}"
        )


def validate_numeric_column(
    df: pd.DataFrame,
    column: str,
    name: str = "DataFrame"
) -> None:
    """验证指定列是数值类型

    :param df: 要验证的DataFrame
    :param column: 列名
    :param name: DataFrame的名称，用于错误消息
    :raises ValueError: 如果列不是数值类型
    """
    if column not in df.columns:
        raise ValueError(f"{name} 中不存在列: {column}")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(
            f"{name} 的列 '{column}' 必须是数值类型, "
            f"当前类型: {df[column].dtype}"
        )


def validate_date_range(
    df: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    name: str = "DataFrame"
) -> None:
    """验证DataFrame的日期范围

    :param df: 要验证的DataFrame (必须有DatetimeIndex)
    :param start_date: 最小允许日期
    :param end_date: 最大允许日期
    :param name: DataFrame的名称，用于错误消息
    :raises ValueError: 如果日期范围无效
    """
    validate_datetime_index(df, name)
    
    if start_date is not None and df.index.min() < start_date:
        raise ValueError(
            f"{name} 包含早于 {start_date} 的数据, "
            f"最早日期: {df.index.min()}"
        )
    
    if end_date is not None and df.index.max() > end_date:
        raise ValueError(
            f"{name} 包含晚于 {end_date} 的数据, "
            f"最晚日期: {df.index.max()}"
        )


def validate_no_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    name: str = "DataFrame"
) -> None:
    """验证DataFrame中没有重复行

    :param df: 要验证的DataFrame
    :param subset: 用于检查重复的列的子集
    :param name: DataFrame的名称，用于错误消息
    :raises ValueError: 如果存在重复行
    """
    duplicates = df.duplicated(subset=subset)
    if duplicates.any():
        num_duplicates = duplicates.sum()
        logger.warning(f"{name} 包含 {num_duplicates} 行重复数据")
        raise ValueError(
            f"{name} 包含 {num_duplicates} 行重复数据. "
            f"请检查数据质量"
        )


def validate_weight_data(df: pd.DataFrame) -> None:
    """验证权重数据格式

    权重数据应包含 dt, symbol, weight 三列

    :param df: 权重数据DataFrame
    :raises ValueError: 如果数据格式无效
    """
    validate_dataframe_columns(
        df,
        required_columns=['dt', 'symbol', 'weight'],
        name="权重数据"
    )
    
    # 验证 dt 列可以转换为日期
    try:
        pd.to_datetime(df['dt'])
    except Exception as e:
        raise ValueError(f"'dt' 列无法转换为日期格式: {e}")
    
    # 验证 weight 列是数值类型
    validate_numeric_column(df, 'weight', "权重数据")
