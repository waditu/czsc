# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/19 23:27
describe: 
"""
import numpy as np
import pandas as pd


def subtract_fee(df, fee=1):
    """依据单品种持仓信号扣除手续费"""
    assert 'dt' in df.columns, 'dt 列必须存在'
    assert 'pos' in df.columns, 'pos 列必须存在'
    assert all(x in [0, 1, -1] for x in df['pos'].unique()), "pos 列的值必须是 0, 1, -1 中的一个"

    if 'n1b' not in df.columns:
        assert 'price' in df.columns, '当n1b列不存在时，price 列必须存在'
        df['n1b'] = (df['price'].shift(-1) / df['price'] - 1) * 10000
    
    df['date'] = df['dt'].dt.date
    df['edge_pre_fee'] = df['pos'] * df['n1b']
    df['edge_post_fee'] = df['pos'] * df['n1b']

    # 扣费规则, 开仓扣费在第一个持仓K线上，平仓扣费在最后一个持仓K线上
    open_pos = (df['pos'].shift() != df['pos']) & (df['pos'] != 0)
    exit_pos = (df['pos'].shift(-1) != df['pos']) & (df['pos'] != 0)
    df.loc[open_pos, 'edge_post_fee'] = df.loc[open_pos, 'edge_post_fee'] - fee
    df.loc[exit_pos, 'edge_post_fee'] = df.loc[exit_pos, 'edge_post_fee'] - fee
    return df


def daily_performance(daily_returns):
    """计算日收益数据的年化收益率、夏普比率、最大回撤、卡玛比率

    所有计算都采用单利计算

    :param daily_returns: 日收益率数据，样例：
        [0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01]
    :return: dict
    """
    if isinstance(daily_returns, list):
        daily_returns = np.array(daily_returns)
    
    if len(daily_returns) == 0 or np.std(daily_returns) == 0 or all(x == 0 for x in daily_returns):
        return {"年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0}
    
    annual_returns = np.sum(daily_returns) / len(daily_returns) * 252
    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    cum_returns = np.cumsum(daily_returns)
    max_drawdown = np.max(np.maximum.accumulate(cum_returns) - cum_returns)
    kama = annual_returns / max_drawdown if max_drawdown != 0 else 10
    win_pct = len(daily_returns[daily_returns > 0]) / len(daily_returns)
    return {
        "年化": round(annual_returns, 4),
        "夏普": round(sharpe_ratio, 2),
        "回撤": round(max_drawdown, 4),
        "卡玛": round(kama, 2),
        "胜率": round(win_pct, 4),
    }


def net_value_stats(nv: pd.DataFrame, exclude_zero: bool = False, sub_cost=True) -> dict:
    """统计净值曲线的年化收益、夏普等

    :param nv: 净值数据，格式如下：

                           dt  edge  cost
        0 2017-01-03 09:30:00   0.0   0.0
        1 2017-01-03 10:00:00   0.0   0.0
        2 2017-01-03 10:30:00   0.0   0.0
        3 2017-01-03 11:00:00   0.0   0.0
        4 2017-01-03 13:00:00   0.0   0.0

        列说明：
        dt: 交易时间
        edge: 单利收益，单位：BP
        cost: 交易成本，单位：BP；可选列，如果没有成本列，则默认为0

    :param exclude_zero: 是否排除收益为0的情况，一般认为收益为0的情况是没有持仓的
    :param sub_cost: 是否扣除成本
    :return:
    """
    nv = nv.copy(deep=True)
    nv['dt'] = pd.to_datetime(nv['dt'])

    if sub_cost:
        assert 'cost' in nv.columns, "成本列cost不存在"
        nv['edge'] = nv['edge'] - nv['cost']
    else:
        if 'cost' not in nv.columns:
            nv['cost'] = 0

    if exclude_zero:
        nv = nv[(nv['edge'] != 0) | (nv['cost'] != 0)]

    # 按日期聚合
    nv['date'] = nv['dt'].apply(lambda x: x.date())
    df_nav = nv.groupby('date')['edge'].sum() / 10000
    df_nav = df_nav.cumsum()

    if all(x == 0 for x in nv['edge']):
        # 处理没有持仓记录的情况
        sharp = 0
        y_ret = 0
        calmar = 0
        mdd = 0
    else:
        # y_ret = yearly return
        N = 252
        y_ret = df_nav.iloc[-1] * (N / len(df_nav))
        if df_nav.diff().std() != 0:
            sharp = df_nav.diff().mean() / df_nav.diff().std() * pow(N, 0.5)
        else:
            sharp = 0
        df0 = df_nav.shift(1).ffill().fillna(0)
        mdd = (1 - (df0 + 1) / (df0 + 1).cummax()).max()
        calmar = y_ret / mdd if mdd != 0 else 1

    prefix = "有持仓时间" if exclude_zero else ""
    res = {"夏普": round(sharp, 2), "卡玛": round(calmar, 2), "年化": round(y_ret, 4), "最大回撤": round(mdd, 4)}
    res = {f"{prefix}{k}": v for k, v in res.items()}

    if not exclude_zero:
        res['持仓覆盖'] = round(len(nv[(nv['edge'] != 0) | (nv['cost'] != 0)]) / len(nv), 4) if len(nv) > 0 else 0
    return res
