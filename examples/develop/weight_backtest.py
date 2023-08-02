# https://s0cqcxuy3p.feishu.cn/wiki/Pf1fw1woQi4iJikbKJmcYToznxb
import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")

import czsc
import pandas as pd
import numpy as np
import plotly.express as px
from czsc import CzscTrader
from loguru import logger
from pathlib import Path
from typing import Union, AnyStr, Callable
from czsc.utils.stats import daily_performance, evaluate_pairs

czsc.welcome()


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
    """持仓权重回测"""

    def __init__(self, dfw, digits=2, **kwargs) -> None:
        """持仓权重回测
        
        :param dfw: pd.DataFrame, columns = ['dt', 'symbol', 'weight', 'price'], 持仓权重数据，
            其中 
                dt      为结束时间，
                symbol  为合约代码，
                weight  为持仓权重，
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
        """
        self.kwargs = kwargs
        self.dfw = dfw.copy()
        self.digits = digits
        self.fee_rate = kwargs.get('fee_rate', 0.0002)
        self.dfw['weight'] = self.dfw['weight'].round(digits)
        self.symbols = list(self.dfw['symbol'].unique().tolist())
        self.res_path = Path(kwargs.get('res_path', "weight_backtest"))
        self.res_path.mkdir(exist_ok=True, parents=True)    
        logger.add(self.res_path.joinpath("weight_backtest.log"), rotation="1 week")
        logger.info(f"持仓权重回测参数：digits={digits}, fee_rate={self.fee_rate}，res_path={self.res_path}，kwargs={kwargs}")

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
        dfs['direction'] = 0
        dfs.loc[dfs['weight'] > 0, 'direction'] = 1
        dfs.loc[dfs['weight'] < 0, 'direction'] = -1
        dfs['volume'] = (dfs['weight'] * pow(10, self.digits)).astype(int) * dfs['direction']
        dfs['bar_id'] = list(range(1, len(dfs)+1))

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

        pairs, opens =[], []
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
        res = {}
        for symbol in self.symbols:
            daily = self.get_symbol_daily(symbol)
            pairs = self.get_symbol_pairs(symbol)
            res[symbol] = {"daily": daily, "pairs": pairs}

        pd.to_pickle(res, self.res_path.joinpath("res.pkl"))
        logger.info(f"回测结果已保存到 {self.res_path.joinpath('res.pkl')}")

        # 品种等权费后日收益率
        dret = pd.concat([v['daily'] for v in res.values()], ignore_index=True)
        dret = pd.pivot_table(dret, index='date', columns='symbol', values='return').fillna(0)
        dret['total'] = dret[list(res.keys())].mean(axis=1)
        logger.info(f"品种等权费后日收益率：{daily_performance(dret['total'])}")
        dret.to_excel(self.res_path.joinpath("daily_return.xlsx"), index=True)
        logger.info(f"品种等权费后日收益率已保存到 {self.res_path.joinpath('daily_return.xlsx')}")

        # 品种等权费后日收益率资金曲线绘制
        dret = dret.cumsum()
        fig = px.line(dret, y=dret.columns.to_list(), title="费后日收益率资金曲线")
        fig.for_each_trace(lambda trace: trace.update(visible=True if trace.name == 'total' else 'legendonly'))
        fig.write_html(self.res_path.joinpath("daily_return.html"))
        logger.info(f"费后日收益率资金曲线已保存到 {self.res_path.joinpath('daily_return.html')}")

        # 所有开平交易记录的表现
        dfp = pd.concat([v['pairs'] for v in res.values()], ignore_index=True)
        pairs_stats = evaluate_pairs(dfp)
        pairs_stats = {k: v for k, v in pairs_stats.items() if k in ['单笔收益', '持仓K线数', '交易胜率', '持仓天数']}
        logger.info(f"所有开平交易记录的表现：{pairs_stats}")
        czsc.save_json(pairs_stats, self.res_path.joinpath("pairs_stats.json"))
        logger.info(f"所有开平交易记录的表现已保存到 {self.res_path.joinpath('pairs_stats.json')}")

        return res


def test_ensemble():
    """从单个 trader 中获取持仓权重，然后回测"""
    trader = czsc.dill_load(r"D:\czsc_bi_datas\期货CTA投研\2019-01-01_2022-01-01_BE44E170\backtest_E497C9B5\traders\DLi9001.trader")

    def __ensemble_method(x):
        return (x['5分钟MACD多头T0'] + x['5分钟SMA#40多头T0']) / 2
    # dfw = get_ensemble_weight(trader, method='mean')
    dfw = get_ensemble_weight(trader, method=__ensemble_method)
    wb = WeightBacktest(dfw, digits=1, fee_rate=0.0002, res_path=r"C:\Users\zengb\Desktop\weight_example_vote")
    wb.backtest()


def test_ensemble_weight():
    """从持仓权重样例数据中回测"""
    dfw = pd.read_feather(r"C:\Users\zengb\Desktop\weight_example.feather")
    wb = WeightBacktest(dfw, digits=1, fee_rate=0.0002, res_path=r"C:\Users\zengb\Desktop\weight_example")
    res = wb.backtest()

