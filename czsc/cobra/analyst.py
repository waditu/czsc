# coding: utf-8
import os
import pandas as pd
from tqdm import tqdm
from typing import List, Tuple
import seaborn as sns
import matplotlib.pyplot as plt

plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class FactorsResearcher:
    """因子研究员"""

    def __init__(self, factors, n_list=None):
        self.factors = factors
        self.factors_df = pd.DataFrame(factors)
        self.factors_df['base'] = 1
        if not n_list:
            self.n_list = (15, 30, 60, 120, 240, 480, 960)
        else:
            self.n_list = n_list
        self.__add_nbar()
        self.base = self.factor_performance(['base'], self.n_list).iloc[0].to_dict()
        self.symbol = self.base['symbol']

    def __add_nbar(self):
        """计算 nbar 相关特征"""
        df = self.factors_df
        n_list = self.n_list
        for bar_number in n_list:
            n_col_name = 'n' + str(bar_number) + 'b'
            df[n_col_name] = (df['close'].shift(-bar_number) / df['close'] - 1) * 10000
        self.factors_df = df

    def factor_performance(self, cols: List, n_list: [List, Tuple]):
        """查看因子组合的表现"""
        df = self.factors_df
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
