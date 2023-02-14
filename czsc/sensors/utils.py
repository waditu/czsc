# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 18:50
"""
import os
import traceback
import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import timedelta
from typing import Callable, List, AnyStr
from sklearn.preprocessing import KBinsDiscretizer

from ..data import TsDataCache, freq_cn2ts


def discretizer(df: pd.DataFrame, col: str, n_bins=20, encode='ordinal', strategy='quantile'):
    """使用 KBinsDiscretizer 对连续变量在时间截面上进行离散化

    :param df: 数据对象
    :param col: 连续变量列名
    :param n_bins: 参见 KBinsDiscretizer 文档
        https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html
    :param encode: 参见 KBinsDiscretizer 文档
    :param strategy: 参见 KBinsDiscretizer 文档
    :return:
    """
    assert col in df.columns, f'{col} not in {df.columns}'
    assert 'dt' in df.columns

    new_col = f'{col}_bins{n_bins}'
    results = []
    for dt, dfg in tqdm(df.groupby('dt'), desc=f"{col}_bins{n_bins}"):
        kb = KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=strategy)
        # 加1，使分组从1开始
        dfg[new_col] = kb.fit_transform(dfg[col].values.reshape(-1, 1)).ravel() + 1
        results.append(dfg)
    df = pd.concat(results, ignore_index=True)
    return df


def get_index_beta(dc: TsDataCache, sdt: str, edt: str, freq='D', file_xlsx=None, indices=None):
    """获取基准指数的Beta

    :param dc: 数据缓存对象
    :param sdt: 开始日期
    :param edt: 结束日期
    :param freq: K线周期，D 日线，W 周线，M 月线
    :param file_xlsx: 结果保存文件
    :param indices: 定义指数列表
    :return:
    """
    if not indices:
        indices = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']

    beta = {}
    p = []
    for ts_code in indices:
        df = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq=freq, asset="I", raw_bar=False)
        beta[ts_code] = df
        df = df.fillna(0)
        start_i, end_i, mdd = max_draw_down(df['n1b'].to_list())
        start_dt = df.iloc[start_i]['trade_date']
        end_dt = df.iloc[end_i]['trade_date']
        row = {
            '标的': ts_code,
            "开始日期": sdt,
            "结束日期": edt,
            "最大回撤": mdd,
            "回撤开始": start_dt,
            "回撤结束": end_dt,
            "交易次数": len(df),
            "交易胜率": round(len(df[df.n1b > 0]) / len(df), 4),
            "累计收益": round(df.n1b.sum(), 4),
        }
        cols = [x for x in df.columns if x[0] == 'n' and x[-1] == 'b']
        row.update({x: round(df[x].mean(), 4) for x in cols})
        p.append(row)

    dfp = pd.DataFrame(p)
    if file_xlsx:
        f = pd.ExcelWriter(file_xlsx)
        dfp.to_excel(f, index=False, sheet_name="指数表现")
        for name, df_ in beta.items():
            df_.to_excel(f, index=False, sheet_name=name)
        f.close()
    else:
        beta['dfp'] = dfp
        return beta


def max_draw_down(n1b: List):
    """最大回撤

    参考：https://blog.csdn.net/weixin_38997425/article/details/82915386

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 最大回撤起止位置和最大回撤
    """
    curve = np.cumsum(n1b)
    curve += 10000
    # 获取结束位置
    i = np.argmax((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve))
    if i == 0:
        return 0, 0, 0

    # 获取开始位置
    j = np.argmax(curve[:i])
    mdd = int((curve[j] - curve[i]) / curve[j] * 10000) / 10000
    return j, i, mdd


def turn_over_rate(df_holds: pd.DataFrame) -> [pd.DataFrame, float]:
    """计算持仓明细对应的组合换手率

    :param df_holds: 每个交易日的持仓明细，数据样例如下
                证券代码    成分日期    持仓权重
            0  000576.SZ  2020-01-02  0.0099
            1  000639.SZ  2020-01-02  0.0099
            2  000803.SZ  2020-01-02  0.0099
            3  000811.SZ  2020-01-02  0.0099
            4  000829.SZ  2020-01-02  0.0099
    :return: 组合换手率
    """
    trade_dates = sorted(df_holds['成分日期'].unique().tolist())
    daily_holds = {date: dfg for date, dfg in df_holds.groupby('成分日期')}

    turns = []
    for date_i, date in tqdm(enumerate(trade_dates), desc='turn_over_rate'):
        if date_i == 0:
            turns.append({'date': date, 'change': 1})
            continue

        dfg = daily_holds[date]
        dfg_last = daily_holds[trade_dates[date_i-1]]
        com_symbols = list(set(dfg['证券代码'].to_list()).intersection(dfg_last['证券代码'].to_list()))

        dfg_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg.iterrows()}
        dfg_last_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg_last.iterrows()}

        change = 0
        change += sum([abs(dfg_pos[symbol] - dfg_last_pos[symbol]) for symbol in com_symbols])
        change += sum([v for symbol, v in dfg_pos.items() if symbol not in com_symbols])
        change += sum([v for symbol, v in dfg_last_pos.items() if symbol not in com_symbols])
        turns.append({'date': date, 'change': change})

    df_turns = pd.DataFrame(turns)
    return df_turns, round(df_turns.change.sum() / 2, 4)


def compound_returns(n1b: List):
    """复利收益计算

    等价于： `np.cumprod(np.array(n1b) / 10000 + 1) *  10000 - 10000`

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 累计复利收益，逐个结算周期的复利收益
    """
    v = 10000
    detail = []
    for n in n1b:
        v = v * (1 + n / 10000)
        detail.append(v-10000)
    return v-10000, detail


class SignalsPerformance:
    """信号表现分析"""

    def __init__(self, dfs: pd.DataFrame, keys: List[AnyStr]):
        """

        :param dfs: 信号表
        :param keys: 信号列，支持一个或多个信号列组合分析
        """
        if 'year' not in dfs.columns:
            y = dfs['dt'].apply(lambda x: x.year)
            dfs['year'] = y.values

        self.dfs = dfs
        self.keys = keys
        self.b_cols = [x for x in dfs.columns if x[0] == 'b' and x[-1] == 'b']
        self.n_cols = [x for x in dfs.columns if x[0] == 'n' and x[-1] == 'b']

    def __return_performance(self, dfs: pd.DataFrame, mode: str = '1b') -> pd.DataFrame:
        """分析信号组合的分类能力，也就是信号出现前后的收益情况

        :param dfs: 信号数据表，
        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        mode = mode.lower()
        assert mode in ['0b', '0n', '1b', '1n']
        keys = self.keys
        len_dfs = len(dfs)
        cols = self.b_cols if mode.endswith('b') else self.n_cols

        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")

        def __static(_df, _name):
            _res = {"name": _name, "date_span": f"{sdt} ~ {edt}",
                    "count": len(_df), "cover": round(len(_df) / len_dfs, 4)}
            if mode.startswith('0'):
                _r = _df.groupby('dt')[cols].mean().mean().to_dict()
            else:
                _r = _df[cols].mean().to_dict()
            _res.update(_r)
            return _res

        results = [__static(dfs, "基准")]

        for values, dfg in dfs.groupby(by=keys if len(keys) > 1 else keys[0]):
            if isinstance(values, str):
                values = [values]
            assert len(keys) == len(values)

            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            results.append(__static(dfg, name))

        dfr = pd.DataFrame(results)
        dfr[cols] = dfr[cols].round(2)
        return dfr

    def analyze(self, mode='0b') -> pd.DataFrame:
        """分析信号出现前后的收益情况

        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        dfr = self.__return_performance(self.dfs, mode)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__return_performance(df_, mode)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def report(self, file_xlsx=None):
        res = {
            '向后看截面': self.analyze('0n'),
            '向后看时序': self.analyze('1n'),
        }
        if file_xlsx:
            writer = pd.ExcelWriter(file_xlsx)
            for sn, df_ in res.items():
                df_.to_excel(writer, sheet_name=sn, index=False)
            writer.close()
        return res
