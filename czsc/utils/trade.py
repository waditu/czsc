# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/21 16:04
describe: 交易相关的工具函数
"""
import pandas as pd
from typing import List, Union
from czsc.objects import RawBar


def risk_free_returns(start_date="20180101", end_date="20210101", year_returns=0.03):
    """创建无风险收益率序列

    创建一个 Pandas DataFrame，包含两列："date" 和 "returns"。"date" 列包含从 trade_dates 获取的所有交易日期，
    "returns" 列包含无风险收益率序列，计算方法是将年化收益率（year_returns）除以 252（一年的交易日数量，假设为每周 5 天）

    :param start_date: 起始日期
    :param end_date: 截止日期
    :param year_returns: 年化收益率
    :return: pd.DataFrame
    """
    from czsc.utils.calendar import get_trading_dates
    trade_dates = get_trading_dates(start_date, end_date)   # type: ignore
    df = pd.DataFrame({"date": trade_dates, "returns": year_returns / 252})
    return df


def cal_trade_price(bars: Union[List[RawBar], pd.DataFrame], decimals=3, **kwargs):
    """计算给定品种基础周期K线数据的交易价格

    函数执行逻辑：

    1. 首先，根据输入的 bars 参数类型（列表或 DataFrame），将其转换为 DataFrame 格式，并将其存储在变量 df 中。
    2. 计算下一根K线的开盘价和收盘价，分别存储在新列 next_open 和 next_close 中。同时，将这两个新列名添加到 price_cols 列表中。
    3. 计算 TWAP（时间加权平均价格）和 VWAP（成交量加权平均价格）。为此，函数使用了一个 for 循环，
       遍历 t_seq 参数（默认值为 (5, 10, 15, 20, 30, 60)）。在每次循环中：

        - 计算 TWAP：使用 rolling(t).mean().shift(-t) 方法计算时间窗口为 t 的滚动平均收盘价。
        - 计算 VWAP：首先计算滚动窗口内的成交量之和（sum_vol_t）和成交量乘以收盘价之和（sum_vcp_t），然后用后者除以前者，并向下移动 t 个单位。
        - 将 TWAP 和 VWAP 的列名添加到 price_cols 列表中。

    4. 遍历 price_cols 列表中的每个列，将其中的 NaN 值替换为对应行的收盘价。
    5. 从 DataFrame 中选择所需的列（包括基本的K线数据列和新计算的交易价格列），并使用 round(decimals) 方法保留指定的小数位数（默认为3）。
    6. 返回处理后的 DataFrame。

    :param bars: 基础周期K线数据，一般是1分钟周期的K线
    :param decimals: 保留小数位数，默认值3
    :return: 交易价格表
    """
    df = pd.DataFrame(bars) if isinstance(bars, list) else bars

    # 下根K线开盘、收盘
    df['next_open'] = df['open'].shift(-1)
    df['next_close'] = df['close'].shift(-1)
    price_cols = ['next_open', 'next_close']

    # TWAP / VWAP 价格
    df['vol_close_prod'] = df['vol'] * df['close']
    for t in kwargs.get('t_seq', (5, 10, 15, 20, 30, 60)):
        df[f"TWAP{t}"] = df['close'].rolling(t).mean().shift(-t)
        df[f"sum_vol_{t}"] = df['vol'].rolling(t).sum()
        df[f"sum_vcp_{t}"] = df['vol_close_prod'].rolling(t).sum()
        df[f"VWAP{t}"] = (df[f"sum_vcp_{t}"] / df[f"sum_vol_{t}"]).shift(-t)
        price_cols.extend([f"TWAP{t}", f"VWAP{t}"])
        df.drop(columns=[f"sum_vol_{t}", f"sum_vcp_{t}"], inplace=True)

    df.drop(columns=['vol_close_prod'], inplace=True)
    # 用当前K线的收盘价填充交易价中的 nan 值
    for price_col in price_cols:
        df.loc[df[price_col].isnull(), price_col] = df[df[price_col].isnull()]['close']

    df[price_cols] = df[price_cols].round(decimals)
    return df


def update_nbars(da, price_col='close', numbers=(1, 2, 5, 10, 20, 30), move=0) -> None:
    """在给定的 da 上计算并添加后面 n 根 bar 的累计收益列

    收益计量单位：BP；1倍涨幅 = 10000BP

    函数的逻辑如下：

    1. 首先，检查 price_col 是否在输入的 DataFrame（da）的列名中。如果不在，抛出 ValueError。
    2. 确保 move 是一个非负整数。
    3. 使用 for 循环遍历 numbers 列表中的每个整数 n, 对于每个整数 n，计算 n 根 bar 的累计收益。
    4. 返回 None，表示这个函数会直接修改输入的 DataFrame（da），而不返回新的 DataFrame。

    :param da: 数据，DataFrame结构
    :param price_col: 价格列
    :param numbers: 考察的bar的数目的列表
    :param move: 收益计算是否要整体移位，move必须是非负整数
        一般是当前bar的close计算收益，也可以考虑是下根bar的open。这个时候 move=1。
    :return nbars_cols: 后面n根bar的bp值列名
    """
    if price_col not in da.columns:
        raise ValueError(f"price_col {price_col} not in da.columns")

    assert move >= 0
    for n in numbers:
        da[f"n{n}b"] = (da[price_col].shift(-n - move) / da[price_col].shift(-move) - 1) * 10000.0


def update_bbars(da, price_col='close', numbers=(1, 2, 5, 10, 20, 30)) -> None:
    """在给定的 da 数据上计算并添加前面 n 根 bar 的累计收益列

    函数的逻辑如下：

    1. 首先，检查 price_col 是否在输入的 DataFrame（da）的列名中。如果不在，抛出 ValueError。
    2. 使用 for 循环遍历 numbers 列表中的每个整数 n，对于每个整数 n，计算 n 根 bar 的累计收益。
    3. 返回 None，表示这个函数会直接修改输入的 da，而不返回新的 DataFrame。

    :param da: K线数据，DataFrame结构
    :param price_col: 价格列
    :param numbers: 考察的bar的数目的列表
    :return: bbars_cols: 后面n根bar的bp值列名
    """
    if price_col not in da.columns:
        raise ValueError(f"price_col {price_col} not in da.columns")

    for n in numbers:
        # 收益计量单位：BP；1倍涨幅 = 10000BP
        da[f"b{n}b"] = (da[price_col] / da[price_col].shift(n) - 1) * 10000


def update_tbars(da: pd.DataFrame, event_col: str) -> None:
    """计算带 Event 方向信息的未来收益

    函数的逻辑如下：

    1. 从输入的 da的列名中提取所有以 'n' 开头，以 'b' 结尾的列名，这些列名表示未来 n 根 bar 的累计收益。将这些列名存储在 n_seq 列表中。
    2. 使用 for 循环遍历 n_seq 列表中的每个整数 n。
    3. 对于每个整数 n，计算带有 Event 方向信息的未来收益。
        计算方法是：将前面 n 根 bar 的累计收益（列名 f'n{n}b'）与事件信号列（event_col）的值相乘。
        将计算结果存储在一个新的列中，列名为 f't{n}b'。
    4. 返回 None，表示这个函数会直接修改输入的 da，而不返回新的 DataFrame。

    :param da: K线数据，DataFrame结构
    :param event_col: 事件信号列名，含有 0, 1, -1 三种值，0 表示无事件，1 表示看多事件，-1 表示看空事件
    :return: None
    """
    n_seq = [int(x.strip('nb')) for x in da.columns if x[0] == 'n' and x[-1] == 'b']
    for n in n_seq:
        da[f't{n}b'] = da[f'n{n}b'] * da[event_col]


def resample_to_daily(df: pd.DataFrame, sdt=None, edt=None, only_trade_date=True):
    """将非日线数据转换为日线数据，以便进行日线级别的分析

    函数执行逻辑：

    1. 首先，函数接收一个数据框`df`，以及可选的开始日期`sdt`，结束日期`edt`，和一个布尔值`only_trade_date`。
    2. 函数将`df`中的`dt`列转换为日期时间格式。如果没有提供`sdt`或`edt`，则使用`df`中的最小和最大日期作为开始和结束日期。
    3. 创建一个日期序列。如果`only_trade_date`为真，则只包含交易日期；否则，包含`sdt`和`edt`之间的所有日期。
    4. 使用`merge_asof`函数，找到每个日期在原始`df`中对应的最近一个日期。
    5. 创建一个映射，将每个日期映射到原始`df`中的对应行。
    6. 对于日期序列中的每个日期，复制映射中对应的数据行，并将日期设置为当前日期。
    7. 最后，将所有复制的数据行合并成一个新的数据框，并返回。

    :param df: 日线以上周期的数据，必须包含 dt 列
    :param sdt: 开始日期
    :param edt: 结束日期
    :param only_trade_date: 是否只保留交易日数据
    :return: pd.DataFrame
    """
    from czsc.utils.calendar import get_trading_dates

    df['dt'] = pd.to_datetime(df['dt'])
    sdt = df['dt'].min() if not sdt else pd.to_datetime(sdt)
    edt = df['dt'].max() if not edt else pd.to_datetime(edt)

    # 创建日期序列
    if only_trade_date:
        trade_dates = get_trading_dates(sdt=sdt, edt=edt)
    else:
        trade_dates = pd.date_range(sdt, edt, freq='D').tolist()
    trade_dates = pd.DataFrame({'date': trade_dates})
    trade_dates = trade_dates.sort_values('date', ascending=True).reset_index(drop=True)

    # 通过 merge_asof 找到每个日期对应原始 df 中最近一个日期
    vdt = pd.DataFrame({'dt': df['dt'].unique()})
    trade_dates = pd.merge_asof(trade_dates, vdt, left_on='date', right_on='dt')
    trade_dates = trade_dates.dropna(subset=['dt']).reset_index(drop=True)

    dt_map = {dt: dfg for dt, dfg in df.groupby('dt')}
    results = []
    for row in trade_dates.to_dict('records'):
        # 注意：这里必须进行 copy，否则默认浅拷贝导致数据异常
        df_ = dt_map[row['dt']].copy()
        df_['dt'] = row['date']
        results.append(df_)

    dfr = pd.concat(results, ignore_index=True)
    return dfr
