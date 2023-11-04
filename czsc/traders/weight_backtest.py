# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/08/02 22:20
describe: 按持仓权重回测
"""
import numpy as np
import pandas as pd
import plotly.express as px
from loguru import logger
from pathlib import Path
from typing import Union, AnyStr, Callable
from czsc.traders.base import CzscTrader
from czsc.utils.io import save_json
from czsc.utils.stats import daily_performance, evaluate_pairs


def long_short_equity(factors, returns, hold_period=2, rank=5, **kwargs):
    """根据截面因子值与收益率，回测分析多空对冲组合的收益率

    :param factors: 截面因子，因子值越大，越偏向于做多，因子值越小，越偏向于做空；数据格式如下：
                        SFIH9001  SFIF9001  SFIC9001
            dt
            2022-08-31  1.403915  1.252826  0.968868
            2022-09-01  1.376690  1.253377  0.972276
            2022-09-02  1.380867  1.253929  0.974999
            2022-09-05  1.370359  1.254482  0.977737
            2022-09-06  0.685180  0.633634  0.493986

    :param returns: 品种收益率矩阵，数据格式如下：
                        SFIH9001  SFIF9001  SFIC9001
            dt
            2021-01-04  0.007803  0.017228  0.004843
            2021-01-05  0.014068  0.008300  0.000598
            2021-01-06  0.024520  0.022766  0.004974
            2021-01-07 -0.006193 -0.003698  0.005951
            2021-01-08 -0.005651 -0.012263 -0.016441

    :param hold_period: 持仓周期，dt 时刻的数量，如果是 2，则表示每两个交易时刻调仓一次
    :param rank: 排序因子值前几名，或者排名因子值的前百分之几；
        如果是整数，则表示排名因子值前几名；如果是浮点数，则表示排名因子值的前百分之几。
        排名靠前，越偏向于做多；排名靠后，越偏向于做空。
    :param kwargs:
    :return:
    """
    # 单边费率
    fee = kwargs.get('fee', 2) / 10000
    factors, returns = factors.copy(), returns.copy()
    factors.index = pd.to_datetime(factors.index)
    returns.index = pd.to_datetime(returns.index)

    # index 对齐
    factors, returns = factors.align(returns, join='inner')
    assert len(factors) == len(returns), 'factors and cross_ret must have the same length'
    assert factors.index.equals(returns.index), 'factors and cross_ret must have the same index'
    assert factors.columns.sort_values().tolist() == returns.columns.sort_values().tolist(), 'factors and cross_ret must have the same columns'

    if isinstance(rank, float):
        assert 0 < rank < 1, 'rank must be between 0 and 1'
        rank = int(len(factors.columns) * rank)

    # 1. 计算截面品种的多空权重
    long = (factors.rank(1, ascending=True, method='first') <= rank).iloc[::hold_period].reindex(factors.index).ffill()
    short = (factors.rank(1, ascending=False, method='first') <= rank).iloc[::hold_period].reindex(factors.index).ffill()
    weight = long + 0 - short
    assert weight.sum(axis=1).unique().tolist() == [0], '每个时间截面的多空权重之和必须为0'

    # 2. 计算多空组合的收益率
    long_ret = returns[long].mean(1).cumsum()
    short_ret = (-returns[short]).mean(1).cumsum()
    ls_ret = ((returns * weight).sum(axis=1) / (rank * 2)).cumsum()
    ls_post_fee_ret = ((returns * weight).sum(axis=1) / (rank * 2) - weight.diff().abs().sum(axis=1) / (rank * 4) * fee * 2).cumsum()

    ret = pd.DataFrame({'多头': long_ret / 2, '空头': short_ret / 2, '多空': ls_ret, '多空费后': ls_post_fee_ret})
    df_nav = ret.resample('1D').last().dropna(axis=0, thresh=3)
    df_nav = df_nav.diff()

    # 2. 分品种收益统计
    ret_symbol = pd.concat([returns[long].sum(), -returns[short].sum()], axis=1)
    ret_symbol.columns = ['多头', '空头']
    ret_symbol['多空'] = ret_symbol['多头'] + ret_symbol['空头']
    ret_symbol = ret_symbol.sort_values(by='多空')

    results = {'日收益率': df_nav, '品种收益': ret_symbol, '持仓权重': weight}
    return results


def get_ensemble_weight(trader: CzscTrader, method: Union[AnyStr, Callable] = 'mean'):
    """获取 CzscTrader 中所有 positions 按照 method 方法集成之后的权重

    :param trader: CzscTrader
        缠论交易者
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
            assert dfp['dt'].equals(p_pos['dt'])
            dfp = dfp.merge(p_pos[['dt', 'pos']], on='dt', how='left')
        dfp.rename(columns={'pos': p.name}, inplace=True)

    pos_cols = [c for c in dfp.columns if c not in ['dt', 'weight', 'price']]
    if callable(method):
        dfp['weight'] = dfp[pos_cols].apply(lambda x: method(x.to_dict()), axis=1)
    else:
        method = method.lower()
        if method == "mean":
            dfp['weight'] = dfp[pos_cols].mean(axis=1)
        elif method == "max":
            dfp['weight'] = dfp[pos_cols].max(axis=1)
        elif method == "min":
            dfp['weight'] = dfp[pos_cols].min(axis=1)
        elif method == "vote":
            dfp['weight'] = dfp[pos_cols].apply(lambda x: np.sign(np.sum(x)), axis=1)
        else:
            raise ValueError(f"method {method} not supported")

    dfp['symbol'] = trader.symbol
    logger.info(f"trader weight decribe: {dfp['weight'].describe().round(4).to_dict()}")
    return dfp[['dt', 'symbol', 'weight', 'price']].copy()


class WeightBacktest:
    """持仓权重回测

    飞书文档：https://s0cqcxuy3p.feishu.cn/wiki/Pf1fw1woQi4iJikbKJmcYToznxb
    """
    version = "V231104"

    def __init__(self, dfw, digits=2, **kwargs) -> None:
        """持仓权重回测

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

        :param digits: int, 权重列保留小数位数
        :param kwargs:

            - fee_rate: float，单边交易成本，包括手续费与冲击成本, 默认为 0.0002
            - res_path: str，回测结果保存路径，默认为 "weight_backtest"

        """
        self.kwargs = kwargs
        self.dfw = dfw.copy()
        if self.dfw.isnull().sum().sum() > 0:
            raise ValueError("dfw 中存在空值, 请先处理")
        self.digits = digits
        self.fee_rate = kwargs.get('fee_rate', 0.0002)
        self.dfw['weight'] = self.dfw['weight'].astype('float').round(digits)
        self.symbols = list(self.dfw['symbol'].unique().tolist())
        self.results = self.backtest()

    def get_symbol_daily(self, symbol):
        """获取某个合约的每日收益率

        :param symbol: str，合约代码
        :return: pd.DataFrame，品种每日收益率，

            columns = ['date', 'symbol', 'edge', 'return', 'cost']
            其中
                date    为交易日，
                symbol  为合约代码，
                edge    为每日收益率，
                return  为每日收益率减去交易成本后的真实收益，
                cost    为交易成本

            数据样例如下：

                ==========  ========  ============  ============  =======
                date        symbol            edge        return     cost
                ==========  ========  ============  ============  =======
                2019-01-02  DLi9001    0.00230261    0.00195919   0.00085
                2019-01-03  DLi9001    0.00425589    0.00310589   0.00115
                2019-01-04  DLi9001   -0.0014209    -0.0024709    0.00105
                2019-01-07  DLi9001    0.000988305  -0.000111695  0.0011
                2019-01-08  DLi9001   -0.0004743    -0.0016243    0.00115
                ==========  ========  ============  ============  =======
        """
        dfs = self.dfw[self.dfw['symbol'] == symbol].copy()
        dfs['edge'] = dfs['weight'] * (dfs['price'].shift(-1) / dfs['price'] - 1)
        dfs['cost'] = abs(dfs['weight'].shift(1) - dfs['weight']) * self.fee_rate
        dfs['edge_post_fee'] = dfs['edge'] - dfs['cost']
        daily = dfs.groupby(dfs['dt'].dt.date).agg({'edge': 'sum', 'edge_post_fee': 'sum', 'cost': 'sum'}).reset_index()
        daily['symbol'] = symbol
        daily.rename(columns={'edge_post_fee': 'return', 'dt': 'date'}, inplace=True)
        daily = daily[['date', 'symbol', 'edge', 'return', 'cost']]
        return daily

    def get_symbol_pairs(self, symbol):
        """获取某个合约的开平交易记录"""
        dfs = self.dfw[self.dfw['symbol'] == symbol].copy()
        dfs['volume'] = (dfs['weight'] * pow(10, self.digits)).astype(int)
        dfs['bar_id'] = list(range(1, len(dfs) + 1))

        # 根据权重变化生成开平仓记录
        operates = []

        def __add_operate(dt, bar_id, volume, price, operate):
            for _ in range(abs(volume)):
                op = {'bar_id': bar_id, "dt": dt, "price": price, "operate": operate}
                operates.append(op)

        rows = dfs.to_dict(orient='records')

        # 处理第一个 row
        if rows[0]['volume'] > 0:
            __add_operate(rows[0]['dt'], rows[0]['bar_id'], rows[0]['volume'], rows[0]['price'], operate='开多')
        elif rows[0]['volume'] < 0:
            __add_operate(rows[0]['dt'], rows[0]['bar_id'], rows[0]['volume'], rows[0]['price'], operate='开空')

        # 处理后续 rows
        for row1, row2 in zip(rows[:-1], rows[1:]):
            if row1['volume'] >= 0 and row2['volume'] >= 0:
                # 多头仓位变化对应的操作
                if row2['volume'] > row1['volume']:
                    __add_operate(row2['dt'], row2['bar_id'], row2['volume'] - row1['volume'], row2['price'], operate='开多')
                elif row2['volume'] < row1['volume']:
                    __add_operate(row2['dt'], row2['bar_id'], row1['volume'] - row2['volume'], row2['price'], operate='平多')

            elif row1['volume'] <= 0 and row2['volume'] <= 0:
                # 空头仓位变化对应的操作
                if row2['volume'] > row1['volume']:
                    __add_operate(row2['dt'], row2['bar_id'], row1['volume'] - row2['volume'], row2['price'], operate='平空')
                elif row2['volume'] < row1['volume']:
                    __add_operate(row2['dt'], row2['bar_id'], row2['volume'] - row1['volume'], row2['price'], operate='开空')

            elif row1['volume'] >= 0 and row2['volume'] <= 0:
                # 多头转换成空头对应的操作
                __add_operate(row2['dt'], row2['bar_id'], row1['volume'], row2['price'], operate='平多')
                __add_operate(row2['dt'], row2['bar_id'], row2['volume'], row2['price'], operate='开空')

            elif row1['volume'] <= 0 and row2['volume'] >= 0:
                # 空头转换成多头对应的操作
                __add_operate(row2['dt'], row2['bar_id'], row1['volume'], row2['price'], operate='平空')
                __add_operate(row2['dt'], row2['bar_id'], row2['volume'], row2['price'], operate='开多')

        pairs, opens = [], []
        for op in operates:
            if op['operate'] in ['开多', '开空']:
                opens.append(op)
                continue

            assert op['operate'] in ['平多', '平空']
            open_op = opens.pop()
            if open_op['operate'] == '开多':
                p_ret = round((op['price'] - open_op['price']) / open_op['price'] * 10000, 2)
                p_dir = '多头'
            else:
                p_ret = round((open_op['price'] - op['price']) / open_op['price'] * 10000, 2)
                p_dir = '空头'
            pair = {"标的代码": symbol, "交易方向": p_dir,
                    "开仓时间": open_op['dt'], "平仓时间": op['dt'],
                    "开仓价格": open_op['price'], "平仓价格": op['price'],
                    "持仓K线数": op['bar_id'] - open_op['bar_id'] + 1,
                    "事件序列": f"{open_op['operate']} -> {op['operate']}",
                    "持仓天数": (op['dt'] - open_op['dt']).days,
                    "盈亏比例": p_ret}
            pairs.append(pair)
        df_pairs = pd.DataFrame(pairs)
        return df_pairs

    def backtest(self):
        """回测所有合约的收益率"""
        symbols = self.symbols
        res = {}
        for symbol in symbols:
            daily = self.get_symbol_daily(symbol)
            pairs = self.get_symbol_pairs(symbol)
            res[symbol] = {"daily": daily, "pairs": pairs}

        dret = pd.concat([v['daily'] for k, v in res.items() if k in symbols], ignore_index=True)
        dret = pd.pivot_table(dret, index='date', columns='symbol', values='return').fillna(0)
        dret['total'] = dret[list(res.keys())].mean(axis=1)
        res['品种等权日收益'] = dret

        stats = {"开始日期": dret.index.min().strftime("%Y%m%d"), "结束日期": dret.index.max().strftime("%Y%m%d")}
        stats.update(daily_performance(dret['total']))
        dfp = pd.concat([v['pairs'] for k, v in res.items() if k in symbols], ignore_index=True)
        pairs_stats = evaluate_pairs(dfp)
        pairs_stats = {k: v for k, v in pairs_stats.items() if k in ['单笔收益', '持仓K线数', '交易胜率', '持仓天数']}
        stats.update(pairs_stats)

        res['绩效评价'] = stats
        return res

    def report(self, res_path):
        """回测报告"""
        res_path = Path(res_path)
        res_path.mkdir(exist_ok=True, parents=True)
        logger.add(res_path.joinpath("weight_backtest.log"), rotation="1 week")
        logger.info(f"持仓权重回测参数：digits={self.digits}, fee_rate={self.fee_rate}，res_path={res_path}")

        res = self.results
        pd.to_pickle(res, res_path.joinpath("res.pkl"))
        logger.info(f"回测结果已保存到 {res_path.joinpath('res.pkl')}")

        # 品种等权费后日收益率
        dret = res['品种等权日收益'].copy()
        dret.to_excel(res_path.joinpath("daily_return.xlsx"), index=True)
        logger.info(f"品种等权费后日收益率已保存到 {res_path.joinpath('daily_return.xlsx')}")

        # 品种等权费后日收益率资金曲线绘制
        dret = dret.cumsum()
        fig = px.line(dret, y=dret.columns.to_list(), title="费后日收益率资金曲线")
        fig.for_each_trace(lambda trace: trace.update(visible=True if trace.name == 'total' else 'legendonly'))
        fig.write_html(res_path.joinpath("daily_return.html"))
        logger.info(f"费后日收益率资金曲线已保存到 {res_path.joinpath('daily_return.html')}")

        # 所有开平交易记录的表现
        stats = res['绩效评价'].copy()
        logger.info(f"绩效评价：{stats}")
        save_json(stats, res_path.joinpath("stats.json"))
        logger.info(f"绩效评价已保存到 {res_path.joinpath('stats.json')}")
