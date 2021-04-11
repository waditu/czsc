# coding: utf-8
import os
from collections import OrderedDict
import numpy as np
import pandas as pd
from tqdm import tqdm
from pyecharts.charts import Page
from typing import List, Tuple
import seaborn as sns
import matplotlib.pyplot as plt
from ..utils.echarts_plot import box_plot

plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def prepare_factors(factors: pd.DataFrame, bar_numbers: [List, Tuple] = (1, 2, 5, 10, 20, 30, 60, 120, 240)):
    """预处理

    :param factors:
    :param bar_numbers:
    :return:
    """
    factors['base'] = 1
    price_column = 'close'
    for bar_number in bar_numbers:
        n_col_name = 'n' + str(bar_number) + 'b'
        factors[n_col_name] = (factors[price_column].shift(-bar_number) / factors[price_column] - 1) * 10000
    factors['dt'] = pd.to_datetime(factors['dt'])
    return factors


def expand_category(factors: pd.DataFrame, category_cols):
    for f in category_cols:
        if factors[f].dtype == 'O' or factors[f].dtype == 'bool':
            itm_list = factors[f].unique()
            for itm in itm_list:
                ecol = '%s@%s' % (f, itm)
                factors[ecol] = np.where(factors[f] == itm, 1, 0)
    return factors


def factors_to_bs(factors: pd.DataFrame, opens: List, exits: List, direction="long", cost=0.3):
    """从因子生成交易序列

    :param cost: 每一个交易对的固定交易成本
    :param factors:
    :param opens:
    :param exits:
    :param direction:
    :return:
    """
    name = opens[0].split("@")[0]
    last_op = "exit"
    ops = []
    for i, row in tqdm(factors.iterrows()):
        op = {"dt": row['dt'], "symbol": row['symbol'], "price": row['close'], "direction": direction}
        if last_op == 'exit' and f"{name}@{row[name]}" in opens:
            op.update({'op': "long_open", 'op_detail': f"{name}@{row[name]}"})
            last_op = 'open'
            ops.append(op)

        elif last_op == 'open' and f"{name}@{row[name]}" in exits:
            op.update({'op': "long_exit", 'op_detail': f"{name}@{row[name]}"})
            last_op = 'exit'
            ops.append(op)
    if ops:
        df = pd.DataFrame(ops)
    else:
        df = pd.DataFrame()

    # 构造成交易对形式输出
    if len(ops) % 2 != 0:
        ops.pop(-1)

    pairs = []
    for i in range(0, len(ops), 2):
        b, s = ops[i: i+2]
        pair = OrderedDict({
            "标的代码": b['symbol'],
            "开仓时间": b['dt'],
            "开仓价格": b['price'],
            "开仓因子": b['op_detail'],
            "平仓时间": s['dt'],
            "平仓价格": s['price'],
            "平仓因子": s['op_detail'],
            "持仓天数": (s['dt'] - b['dt']).days,
            "盈亏(%)": round((s['price'] - b['price']) / b['price'] * 100 - cost, 2),
        })

        if pairs:
            pair['净值(%)'] = round((pairs[-1]['净值(%)']) * (1 + pair['盈亏(%)'] / 100), 2)
        else:
            pair['净值(%)'] = round(100 * (1 + pair['盈亏(%)'] / 100), 2)
        pairs.append(pair)
    if pairs:
        df1 = pd.DataFrame(pairs)
    else:
        df1 = pd.DataFrame()

    return df, df1


def report_factor_performance(factors: pd.DataFrame, name: str):
    """评估单个因子的表现

    :param factors:
    :param name: 因子名称
    :return:
    """
    nb_cols = [x for x in factors.columns if x.startswith("n")]
    page = Page(layout=Page.DraggablePageLayout, page_title=f"{name} - 性能分析")
    box_data = {col: [factors[col].quantile(v) for v in [0, 0.25, 0.5, 0.75, 1]] for col in nb_cols}
    chart = box_plot(data=box_data, title=f"BASE", width=f'{40*len(nb_cols)}px', height='300px')
    page.add(chart)
    for k, df in factors.groupby(name):
        box_data = {col: [df[col].quantile(v) for v in [0, 0.25, 0.5, 0.75, 1]] for col in nb_cols}
        chart = box_plot(data=box_data, title=f"{name}@{k}", width=f'{40*len(nb_cols)}px', height='300px')
        page.add(chart)
    return page

class FactorsResearcher:
    """因子研究员"""

    def __init__(self, factors, n_list=None):
        if isinstance(factors, pd.DataFrame):
            self.factors = factors
        else:
            self.factors = pd.DataFrame(factors)
        self.factors['base'] = prepare_factors(self.factors, self.n_list)
        if not n_list:
            self.n_list = (15, 30, 60, 120, 240, 480, 960)
        else:
            self.n_list = n_list
        self.factors = prepare_factors(self.factors, self.n_list)
        self.base = self.factor_performance(['base'], self.n_list).iloc[0].to_dict()
        self.symbol = self.base['symbol']

    def factor_performance(self, cols: List, n_list: [List, Tuple]):
        """查看因子组合的表现"""
        df = self.factors
        df = df.dropna()
        n_list = list(n_list)

        results = []
        for values, dfg in df.groupby(cols):
            res = {"symbol": self.factors[0]['symbol'], "factor_name": "#".join(cols)}
            if isinstance(values, tuple):
                res['factor_value'] = "#".join(values)
            else:
                res['factor_value'] = values

            res["count"] = len(dfg)

            for n in n_list:
                nb_col = 'n{}b'.format(n)
                dn = dfg[nb_col]
                dn1 = dfg[dfg[nb_col] >= 0]
                # dn2 = dfg[dfg[nb_col] < 0]
                res['n{}b均收益'.format(n)] = round(dn.mean(), 2)
                # if dn2.empty:
                #     res['n{}b盈亏比'.format(n)] = round(dn1[nb_col].mean(), 2)
                # elif dn1.empty:
                #     res['n{}b盈亏比'.format(n)] = round(dn2[nb_col].mean(), 2)
                # else:
                #     res['n{}b盈亏比'.format(n)] = round(abs(dn1[nb_col].mean() / (dn2[nb_col].mean() + 1)), 2)
                res['n{}b胜率'.format(n)] = round(len(dn1) / len(dn), 2)

            results.append(res)
        df_res = pd.DataFrame(results)
        df_res['pct'] = df_res['count'] / len(df)
        df_res['pct'] = df_res['pct'].round(4)
        return df_res

    def plot_performance(self, cols: List, show: bool = True, res_path: str = None, dpi: int = 100):
        """绘制nbars表现图"""
        base = self.base
        n_bars = [x for x in base.keys() if "均收益" in x]
        base_v = [base[x] for x in n_bars]
        df = self.factor_performance(cols, self.n_list)
        plt.close()
        ncols = 4
        nrows = len(df) // ncols if len(df) % ncols == 0 else len(df) // ncols + 1
        fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize=(6*ncols, len(df)*4 // ncols))
        for i, v in enumerate(df.factor_value.unique()):
            f = df[df['factor_value'] == v].iloc[0].to_dict()
            factor_ = [f[x] for x in n_bars]
            data = {"n_bars": [int(x.strip("nb均收益")) for x in n_bars], 'base': base_v, v: factor_}

            ax = axes[i // ncols][i % ncols]
            sns.lineplot(x="n_bars", y='base', data=data, ax=ax)
            sns.lineplot(x="n_bars", y=v, data=data, ax=ax)
            ax.legend(["base", 'factor'])
            names = f['factor_name'].split("#")
            values = [x.split("~")[0] for x in f['factor_value'].split("#")]
            v = ["{}({})".format(x1, x2) for x1, x2 in zip(names, values)]
            ax.set_title(v, loc='center')
            ax.text(x=10, y=5, s="数量：{}({}%)".format(f['count'], round(f['pct']*100, 2)), fontsize=14)

        if show:
            plt.show()
        else:
            file_png = os.path.join(res_path, "{}_{}.png".format(self.symbol, "&".join(cols)))
            plt.savefig(file_png, bbox_inches='tight', dpi=dpi)

    def single_factor_analyze(self, cols: [list, tuple], n_list: [List, Tuple]):
        """单因子分析"""
        data = []
        for col in tqdm(cols, desc="single_factor_analyze"):
            data.append(self.factor_performance([col], n_list))
        df = pd.concat(data)
        return df

    def pair_factor_analyze(self, pairs:  List[Tuple[str, str]], n_list: [List, Tuple]):
        """两因子分析"""
        data = []
        for pair in tqdm(pairs, desc="pair_factor_analyze"):
            data.append(self.factor_performance(list(pair), n_list))
        df = pd.concat(data)
        return df

    def triple_factor_analyze(self, triples: List[Tuple[str, str, str]], n_list: [List, Tuple]):
        """三因子分析"""
        data = []
        for triple in tqdm(triples, desc="triple_factor_analyze"):
            data.append(self.factor_performance(list(triple), n_list))
        df = pd.concat(data)
        return df
