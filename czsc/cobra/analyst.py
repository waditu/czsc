# coding: utf-8
import pandas as pd
from tqdm import tqdm
from typing import List, Callable, Tuple


class FactorsResearcher:
    """因子研究员"""

    def __init__(self, factors, n_list=None):
        self.factors = factors
        self.factors_df = pd.DataFrame(factors)
        self.factors_df['base'] = 1
        self.performance = None
        if not n_list:
            self.n_list = (15, 30, 60, 120, 240, 480, 960)
        else:
            self.n_list = n_list
        self.__add_nbar()
        self.base = self.factor_performance(['base']).iloc[0].to_dict()

    def __add_nbar(self):
        """计算 nbar 相关特征"""
        df = self.factors_df
        n_list = self.n_list
        for bar_number in n_list:
            n_col_name = 'n' + str(bar_number) + 'b'
            df[n_col_name] = (df['close'].shift(-bar_number) / df['close'] - 1) * 10000
        self.factors_df = df

    def factor_performance(self, cols: List):
        """查看因子组合的表现"""
        df = self.factors_df
        df = df.dropna()
        n_list = self.n_list

        results = []
        for values, dfg in df.groupby(cols):
            res = {"factor_name": "&".join(cols)}
            if isinstance(values, tuple):
                for i, v in enumerate(values, 1):
                    res['factor_value{}'.format(i)] = v
            else:
                res['factor_value'] = values

            res["count"] = len(dfg)

            for n in n_list:
                nb_col = 'n{}b'.format(n)
                dn = dfg[nb_col]
                dn1 = dfg[dfg[nb_col] >= 0]
                dn2 = dfg[dfg[nb_col] < 0]
                res['n{}b均收益'.format(n)] = round(dn.mean(), 2)
                if dn2.empty:
                    res['n{}b盈亏比'.format(n)] = round(dn1[nb_col].mean(), 2)
                elif dn1.empty:
                    res['n{}b盈亏比'.format(n)] = round(dn2[nb_col].mean(), 2)
                else:
                    res['n{}b盈亏比'.format(n)] = round(abs(dn1[nb_col].mean() / (dn2[nb_col].mean() + 1)), 2)
                res['n{}b胜率'.format(n)] = round(len(dn1) / len(dn), 2)

            results.append(res)
        df_res = pd.DataFrame(results)
        df_res['pct'] = df_res['count'] / len(df)
        return df_res

    def single_factor_analyze(self, cols: [list, tuple]):
        """单因子分析"""
        data = []
        for col in tqdm(cols, desc="single_factor_analyze"):
            data.append(self.factor_performance([col]))
        df = pd.concat(data)
        return df

    def pair_factor_analyze(self, pairs:  List[Tuple[str, str]]):
        """两因子分析"""
        data = []
        for pair in tqdm(pairs, desc="pair_factor_analyze"):
            data.append(self.factor_performance(list(pair)))
        df = pd.concat(data)
        return df

    def triple_factor_analyze(self, triples:  List[Tuple[str, str, str]]):
        """三因子分析"""
        data = []
        for triple in tqdm(triples, desc="triple_factor_analyze"):
            data.append(self.factor_performance(list(triple)))
        df = pd.concat(data)
        return df

    def add_temp_factors(self, functions: List[Callable]) -> None:
        """新增因子，用于快速研究

        :param functions:
        :return: None
        """
        for factor in functions:
            name = factor.__doc__
            for row in tqdm(self.factors, desc="add {}".format(name)):
                row[name] = factor(row)


