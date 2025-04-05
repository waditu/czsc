# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import pandas as pd
import loguru
import numpy as np
import streamlit as st

st.set_page_config(layout="wide")



def mark_volatility(df: pd.DataFrame, kind='ts', **kwargs):
    """【后验，有未来信息，不能用于实盘】标记时序/截面波动率最大/最小的N个时间段

    :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
    :param kind: 波动率类型，'ts' 表示时序波动率，'cs' 表示截面波动率
    :param kwargs: 

        - copy: 是否复制数据
        - verbose: 是否打印日志
        - logger: 日志记录器
        - window: 计算波动率的窗口
        - q1: 波动率最大的K线数量占比
        - q2: 波动率最小的K线数量占比

    :return: 带有标记的K线数据，新增列 'is_max_volatility', 'is_min_volatility'
    """
    window = kwargs.get("window", 20)
    q1 = kwargs.get("q1", 0.2)
    q2 = kwargs.get("q2", 0.2)
    assert 0.4 >= q1 >= 0.0, "q1 必须在 0.4 和 0.0 之间"
    assert 0.4 >= q2 >= 0.0, "q2 必须在 0.4 和 0.0 之间"
    assert kind in ['ts', 'cs'], "kind 必须是 'ts' 或 'cs'"

    if kwargs.get("copy", True):
        df = df.copy()
    
    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)
    
    # 计算波动率
    if kind == 'ts':
        # 时序波动率：每个股票单独计算时间序列上的波动率
        rows = []
        for symbol, dfg in df.groupby('symbol'):
            if verbose:
                logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

            dfg = dfg.sort_values('dt').copy().reset_index(drop=True)
            dfg['volatility'] = dfg['close'].pct_change().rolling(window=window).std().shift(-window)
            dfg['volatility_rank'] = dfg['volatility'].rank(method='min', ascending=False, pct=True)
            dfg['is_max_volatility'] = np.where(dfg['volatility_rank'] <= q1, 1, 0)
            dfg['is_min_volatility'] = np.where(dfg['volatility_rank'] > 1 - q2, 1, 0)
            rows.append(dfg)

        dfr = pd.concat(rows, ignore_index=True)
    
    elif kind == 'cs':
        if df['symbol'].nunique() < 2:
            raise ValueError(f"品种数量太少(仅 {df['symbol'].nunique()})，无法计算截面波动率")
        # 截面波动率：在每个时间点比较不同股票之间的波动率
        # 首先计算各个股票的波动率
        df = df.sort_values(['dt', 'symbol']).copy()
        df['volatility'] = df.groupby('symbol')['close'].pct_change().rolling(window=window).std().shift(-window)
        
        # 对每个时间点的不同股票进行排序
        df['volatility_rank'] = df.groupby('dt')['volatility'].rank(method='min', ascending=False, pct=True)
        df['is_max_volatility'] = np.where(df['volatility_rank'] <= q1, 1, 0)
        df['is_min_volatility'] = np.where(df['volatility_rank'] > 1 - q2, 1, 0)

        if df['is_max_volatility'].sum() == 0:
            df['is_max_volatility'] = np.where(df['volatility_rank'] == df['volatility_rank'].max(), 1, 0)

        if df['is_min_volatility'].sum() == 0:
            df['is_min_volatility'] = np.where(df['volatility_rank'] == df['volatility_rank'].min(), 1, 0)

        dfr = df

    else:
        raise ValueError(f"kind 必须是 'ts' 或 'cs'，当前值为 {kind}")

    if verbose:
        # 计算波动率最大和最小的占比
        max_volatility_pct = dfr['is_max_volatility'].sum() / len(dfr)
        min_volatility_pct = dfr['is_min_volatility'].sum() / len(dfr)
        logger.info(f"处理完成，波动率计算方式：{kind}，波动率最大时间覆盖率：{max_volatility_pct:.2%}, "
                   f"波动率最小时间覆盖率：{min_volatility_pct:.2%}")
    
    dfr.drop(columns=['volatility', 'volatility_rank'], inplace=True)
    return dfr


@st.cache_data(ttl=60*60*24)
def prepare_data(**kwargs):
    from czsc.connectors import research

    df1 = research.get_raw_bars('000905.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)
    df2 = research.get_raw_bars('000001.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)

    df = pd.concat([df1, df2], ignore_index=True)
    
    # dfs = mark_cta_periods(df.copy(), freq='日线', verbose=True)
    dfs = df.copy()
    print(dfs.head())
    dfs = dfs.sort_values('dt').copy().reset_index(drop=True) 

    return dfs


def show_volatility_classify(df: pd.DataFrame, kind='ts', **kwargs):
    """【后验，有未来信息，不能用于实盘】波动率分类回测

    :param df: 标准K线数据，
            必须包含 dt, symbol, open, close, high, low, vol, amount, weight, price 列; 
            如果 price 列不存在，则使用 close 列
    :param kwargs: 

        - fee_rate: 手续费率，WeightBacktest 的参数
        - digits: 小数位数，WeightBacktest 的参数
        - weight_type: 权重类型，'ts' 表示时序，'cs' 表示截面，WeightBacktest 的参数
        - kind: 波动率分类方式，'ts' 表示时序，'cs' 表示截面，mark_volatility 函数的参数
        - window: 计算波动率的窗口，mark_volatility 函数的参数
        - q1: 波动率最大的K线数量占比，默认 0.2，mark_volatility 函数的参数
        - q2: 波动率最小的K线数量占比，默认 0.2，mark_volatility 函数的参数

    :return: None

    ==============
    example
    ==============
    >>> show_volatility_classify(df, fee_rate=0.00, digits=1, weight_type='ts', 
    >>>                          volatility_kind='ts', window=20, q1=0.2, q2=0.2 )
    """
    from rs_czsc import WeightBacktest
    from czsc.utils.st_components import show_daily_return, show_cumulative_returns

    fee_rate = kwargs.get('fee_rate', 0.00)
    digits = kwargs.get('digits', 1)
    weight_type = kwargs.get('weight_type', 'ts')
    window = kwargs.get('window', 20)
    q1 = kwargs.get('q1', 0.2)
    q2 = kwargs.get('q2', 0.2)

    dfs = mark_volatility(df.copy(), kind=kind, verbose=False, q1=q1, q2=q2, window=window)

    if 'price' not in dfs.columns:
        dfs['price'] = dfs['close']

    p1 = dfs['is_max_volatility'].value_counts()[1] / len(dfs)
    p2 = dfs['is_min_volatility'].value_counts()[1] / len(dfs)
    st.markdown(f"波动率最大行情占比：:red[{p1:.2%}]；波动率最小行情占比：:blue[{p2:.2%}]")

    wb = WeightBacktest(dfs[['dt', 'symbol', 'weight', 'price']], fee_rate=fee_rate, digits=digits, 
                        weight_type=weight_type)

    df1 = dfs.copy()
    df1['weight'] = np.where(df1['is_max_volatility'], df1['weight'], 0)
    df1 = df1[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb1 = WeightBacktest(df1, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    df2 = dfs.copy()
    df2['weight'] = np.where(df2['is_min_volatility'], df2['weight'], 0)
    df2 = df2[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
    wb2 = WeightBacktest(df2, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    classify = ['原始策略', '波动率大', '波动率小']

    dailys = []
    for wb_, classify_ in zip([wb, wb1, wb2], classify):
        df_daily = wb_.daily_return.copy()
        df_daily = df_daily[['date', 'total']].copy().reset_index(drop=True)
        df_daily['classify'] = classify_
        dailys.append(df_daily)
    dailys = pd.concat(dailys, ignore_index=True)
    dailys['date'] = pd.to_datetime(dailys['date'])
    dailys = pd.pivot_table(dailys, index='date', columns='classify', values='total')
    show_daily_return(dailys, stat_hold_days=False)


def main():
    df = prepare_data()
    df['weight'] = df.groupby('symbol')['close'].rolling(window=5, min_periods=1).apply(lambda x: np.sign(x.iloc[-1] - x.mean())).reset_index(0, drop=True)
    df['price'] = df['close']
    show_volatility_classify(df, volatility_kind='ts', window=5, q1=0.3, q2=0.3)


if __name__ == '__main__':
    main()
