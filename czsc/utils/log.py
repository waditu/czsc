import pandas as pd
from loguru import logger


def log_strategy_info(strategy, df: pd.DataFrame):
    """打印策略数据的详细信息，包括每个品种的数据详情
    
    :param strategy: 策略名称
    :param df: 策略数据，包含 symbol, dt, weight 等列
    """
    logger.info("-" * 100)
    
    if df.empty:
        logger.warning(f"策略 {strategy} 数据为空！")
        return
    
    df = df.copy()
    df['dt'] = pd.to_datetime(df['dt'])
    df = df.sort_values(['symbol', 'dt']).reset_index(drop=True)
    # 基本信息
    total_records = len(df)
    unique_symbols = df['symbol'].unique()
    sdt = df['dt'].min()
    edt = df['dt'].max()
    
    logger.info(f"策略 {strategy} 数据详情：")
    logger.info(f"  总记录数: {total_records}")
    logger.info(f"  时间范围: {sdt} ~ {edt}; 总时间点数: {df['dt'].nunique()}")
    logger.info(f"  品种数量: {len(unique_symbols)}")
    
    # 每个品种的详细信息
    logger.info(f"  品种详情:")
    for symbol in sorted(unique_symbols):
        symbol_df = df[df['symbol'] == symbol]
        symbol_count = len(symbol_df)
        symbol_sdt = symbol_df['dt'].min()
        symbol_edt = symbol_df['dt'].max()
        
        # 权重统计
        if 'weight' in symbol_df.columns:
            weight_stats = symbol_df['weight'].describe()
            logger.info(f"    {symbol}: 记录数={symbol_count}, "
                       f"时间={symbol_sdt}~{symbol_edt}, "
                       f"权重范围=[{weight_stats['min']:.3f}, {weight_stats['max']:.3f}], "
                       f"平均权重={weight_stats['mean']:.3f}")
        else:
            logger.info(f"    {symbol}: 记录数={symbol_count}, "
                       f"时间={symbol_sdt}~{symbol_edt}")
    
    # 数据质量检查
    if 'weight' in df.columns:
        null_weights = df['weight'].isnull().sum()
        zero_weights = (df['weight'] == 0).sum()
        if null_weights > 0 or zero_weights > 0:
            logger.warning(f"  数据质量提醒: 空权重={null_weights}, 零权重={zero_weights}")
    logger.info("-" * 100)


