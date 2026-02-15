"""
数据格式转换工具

提取的通用数据格式转换逻辑
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from loguru import logger


def to_standard_kline_format(
    df: pd.DataFrame,
    dt_col: str = 'dt',
    open_col: str = 'open',
    high_col: str = 'high',
    low_col: str = 'low',
    close_col: str = 'close',
    volume_col: str = 'vol'
) -> pd.DataFrame:
    """将DataFrame转换为标准K线格式

    标准K线格式包含: dt, open, close, high, low, vol

    :param df: 输入DataFrame
    :param dt_col: 日期时间列名
    :param open_col: 开盘价列名
    :param high_col: 最高价列名
    :param low_col: 最低价列名
    :param close_col: 收盘价列名
    :param volume_col: 成交量列名
    :return: 标准格式的DataFrame
    """
    result = pd.DataFrame()
    
    # 标准化列名
    column_mapping = {
        dt_col: 'dt',
        open_col: 'open',
        high_col: 'high',
        low_col: 'low',
        close_col: 'close',
        volume_col: 'vol'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            result[new_col] = df[old_col]
        else:
            logger.warning(f"列 '{old_col}' 不存在于输入DataFrame中")
    
    # 确保dt列是datetime类型
    if 'dt' in result.columns:
        result['dt'] = pd.to_datetime(result['dt'])
    
    return result


def pivot_weight_data(
    dfw: pd.DataFrame,
    fill_value: float = 0.0
) -> pd.DataFrame:
    """将权重数据转换为透视表格式

    :param dfw: 权重数据，包含 dt, symbol, weight 列
    :param fill_value: 填充缺失值
    :return: 透视后的DataFrame，index为dt，columns为symbol
    """
    df = dfw.copy()
    df['dt'] = pd.to_datetime(df['dt'])
    
    pivot_df = pd.pivot_table(
        df,
        index='dt',
        columns='symbol',
        values='weight',
        aggfunc='sum'
    )
    
    if fill_value is not None:
        pivot_df = pivot_df.fillna(fill_value)
    
    return pivot_df


def resample_to_period(
    df: pd.DataFrame,
    period: str,
    agg_dict: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """将数据重采样到指定周期

    :param df: 输入DataFrame，必须有DatetimeIndex
    :param period: 周期字符串，如 'D' (日), 'W' (周), 'M' (月)
    :param agg_dict: 聚合函数字典，键为列名，值为聚合函数
    :return: 重采样后的DataFrame
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame必须有DatetimeIndex才能进行重采样")
    
    if agg_dict is None:
        # 默认聚合方式
        agg_dict = {col: 'sum' for col in df.columns}
    
    return df.resample(period).agg(agg_dict)


def normalize_symbol(symbol: str) -> str:
    """标准化品种代码

    :param symbol: 品种代码
    :return: 标准化后的品种代码
    """
    # 移除空格
    symbol = symbol.strip()
    # 转换为大写
    symbol = symbol.upper()
    return symbol


def convert_dict_to_dataframe(
    data: List[Dict[str, Any]],
    sort_by: Optional[str] = None
) -> pd.DataFrame:
    """将字典列表转换为DataFrame

    :param data: 字典列表
    :param sort_by: 排序列名
    :return: DataFrame
    """
    df = pd.DataFrame(data)
    
    if sort_by and sort_by in df.columns:
        df = df.sort_values(by=sort_by)
    
    return df


def ensure_datetime_column(
    df: pd.DataFrame,
    column: str,
    inplace: bool = False
) -> pd.DataFrame:
    """确保指定列是datetime类型

    :param df: DataFrame
    :param column: 列名
    :param inplace: 是否在原DataFrame上修改
    :return: DataFrame
    """
    if not inplace:
        df = df.copy()
    
    if column in df.columns:
        df[column] = pd.to_datetime(df[column])
    
    return df


def flatten_multiindex_columns(
    df: pd.DataFrame,
    sep: str = '_'
) -> pd.DataFrame:
    """扁平化MultiIndex列

    :param df: 包含MultiIndex列的DataFrame
    :param sep: 连接符
    :return: 扁平化后的DataFrame
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [sep.join(map(str, col)).strip() for col in df.columns.values]
    
    return df
