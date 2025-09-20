# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/08/02 22:20
describe: 按持仓权重回测
"""
import numpy as np
import pandas as pd
from loguru import logger
from typing import Union, AnyStr, Callable

from czsc.traders.base import CzscTrader
from rs_czsc import WeightBacktest


__all__ = ['WeightBacktest', 'get_ensemble_weight', 'stoploss_by_direction']


def get_ensemble_weight(trader: CzscTrader, method: Union[AnyStr, Callable] = "mean"):
    """获取 CzscTrader 中所有 positions 按照 method 方法集成之后的权重

    函数计算逻辑：

    1. 获取 trader 持仓信息并转换为DataFrame:

        - 遍历交易者的每个持仓位置。
        - 将每个位置的持仓信息转换为DataFrame，并合并到一个整体的DataFrame中。
        - 将持仓列重命名为对应的位置名称。

    2. 根据给定的方法计算权重:

        - 如果方法是可调用对象，将持仓信息转换为字典，并传递给该方法进行计算。
        - 如果方法是预定义字符串（"mean"、"max"、"min"、"vote"），根据相应的计算方式计算权重。

    3. 返回包含日期、交易标的、权重和价格的DataFrame:

        - 将计算得到的权重与其他相关列一起组成一个新的DataFrame。
        - 将交易标的信息添加到新的DataFrame中。
        - 返回包含日期、交易标的、权重和价格的DataFrame副本。

    :param trader: CzscTrader
        缠论交易员对象
    :param method: str or callable

        集成方法，可选值包括：'mean', 'max', 'min', 'vote'
        也可以传入自定义的函数，函数的输入为 dict，key 为 position.name，value 为 position.pos, 样例输入：
            {'多头策略A': 1, '多头策略B': 1, '空头策略A': -1}

    :param kwargs:
    :return: pd.DataFrame
        columns = ['dt', 'symbol', 'weight', 'price']
    """
    logger.info(f"trader positions: {[p.name for p in trader.positions]}")

    dfp = pd.DataFrame()
    for p in trader.positions:
        p_pos = pd.DataFrame(p.holds)
        if dfp.empty:
            dfp = p_pos.copy()
        else:
            assert dfp["dt"].equals(p_pos["dt"])
            dfp = dfp.merge(p_pos[["dt", "pos"]], on="dt", how="left")
        dfp.rename(columns={"pos": p.name}, inplace=True)

    pos_cols = [c for c in dfp.columns if c not in ["dt", "weight", "price"]]
    if callable(method):
        dfp["weight"] = dfp[pos_cols].apply(lambda x: method(x.to_dict()), axis=1)
    else:
        method = method.lower()
        if method == "mean":
            dfp["weight"] = dfp[pos_cols].mean(axis=1)
        elif method == "max":
            dfp["weight"] = dfp[pos_cols].max(axis=1)
        elif method == "min":
            dfp["weight"] = dfp[pos_cols].min(axis=1)
        elif method == "vote":
            dfp["weight"] = dfp[pos_cols].apply(lambda x: np.sign(np.sum(x)), axis=1)
        else:
            raise ValueError(f"method {method} not supported")

    dfp["symbol"] = trader.symbol
    logger.info(f"trader weight decribe: {dfp['weight'].describe().round(4).to_dict()}")
    return dfp[["dt", "symbol", "weight", "price"]].copy()


def stoploss_by_direction(dfw, stoploss=0.03, **kwargs):
    """按持仓方向进行止损

    :param dfw: pd.DataFrame, columns = ['dt', 'symbol', 'weight', 'price'], 持仓权重数据，其中

        dt      为K线结束时间，必须是连续的交易时间序列，不允许有时间断层
        symbol  为合约代码，
        weight  为K线结束时间对应的持仓权重，品种之间的权重是独立的，不会互相影响
        price   为结束时间对应的交易价格，可以是当前K线的收盘价，或者下一根K线的开盘价，或者未来N根K线的TWAP、VWAP等

        数据样例如下：
        ===================  ========  ========  =======
        dt                   symbol      weight    price
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param stoploss: 止损比例
    :param kwargs: 其他参数
    :return: pd.DataFrame，
        columns = ['dt', 'symbol', 'weight', 'raw_weight', 'price', 'returns',
                   'hold_returns', 'min_hold_returns', 'order_id', 'is_stop']
    """
    dfw = dfw.copy()
    dfw["direction"] = np.sign(dfw["weight"])
    dfw["raw_weight"] = dfw["weight"].copy()
    assert stoploss > 0, "止损比例必须大于0"

    rows = []
    for _, dfg in dfw.groupby("symbol"):
        assert isinstance(dfg, pd.DataFrame)
        assert dfg["dt"].is_monotonic_increasing, "dt 必须是递增的时间序列"
        dfg = dfg.sort_values("dt", ascending=True)

        # 按交易方向设置订单号
        dfg["order_id"] = dfg.groupby((dfg["direction"] != dfg["direction"].shift()).cumsum()).ngroup()

        # 按持仓权重计算收益
        dfg["n1b"] = dfg["price"].shift(-1) / dfg["price"] - 1
        dfg["returns"] = dfg["n1b"] * dfg["weight"]
        dfg["hold_returns"] = dfg["returns"].groupby(dfg["order_id"]).cumsum()
        dfg["min_hold_returns"] = dfg.groupby("order_id")["hold_returns"].cummin()

        # 止损：同一个订单下，min_hold_returns < -stoploss时，后续weight置为0
        dfg["is_stop"] = (dfg["min_hold_returns"] < -stoploss) & (dfg["order_id"] == dfg["order_id"].shift(1))
        c1 = dfg["is_stop"].shift(1) & (dfg["order_id"] == dfg["order_id"].shift(1))
        dfg.loc[c1, "weight"] = 0
        dfg["weight"] = np.where(c1, 0, dfg["weight"])
        rows.append(dfg.copy())

    dfw1 = pd.concat(rows, ignore_index=True)
    return dfw1

