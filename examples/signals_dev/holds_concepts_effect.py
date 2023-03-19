# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/19 22:03
describe: 
"""
import pandas as pd
from tqdm import tqdm
from collections import Counter
from czsc.data import TsDataCache


def get_symbol_concepts():
    dc = TsDataCache(data_path=r"D:\ts_data", sdt='2014-01-01')
    ths_members = dc.get_all_ths_members(exchange="A", type_="N")
    ths_members = ths_members[ths_members['code'].str.contains('[SH|SZ]$')]

    # 过滤掉一些成分股数量特别多的概念
    not_concepts = ths_members.groupby('概念名称')['code'].count().sort_values(ascending=False).head(20).to_dict()

    ths_members = ths_members[~ths_members['概念名称'].isin(not_concepts)]
    ths_members = ths_members.groupby('code')['概念名称'].apply(list).reset_index()
    sc = ths_members.set_index('code')['概念名称'].to_dict()
    return sc


def holds_concepts_effect(holds: pd.DataFrame, concepts: dict, top_n=20, min_n=3, **kwargs):
    """股票持仓列表的板块效应

    原理概述：在选股时，如果股票的概念板块与组合中的其他股票的概念板块有重合，那么这个股票的表现会更好。

    :param holds: 组合股票池数据，样例：
                 成分日期    证券代码       n1b      持仓权重
            0  2020-01-02  000001.SZ  183.758194  0.001232
            1  2020-01-02  000002.SZ -156.633896  0.001232
            2  2020-01-02  000063.SZ  310.296204  0.001232
            3  2020-01-02  000066.SZ -131.824997  0.001232
            4  2020-01-02  000069.SZ  -38.561699  0.001232
    :param concepts: 股票的概念板块，样例：
            {
                '002507.SZ': ['电子商务', '超级品牌', '国企改革'],
                '002508.SZ': ['家用电器', '杭州亚运会', '恒大概念']
            }
    :param top_n: 选取前 n 个密集概念
    :param min_n: 单股票至少要有 n 个概念在 top_n 中
    :return: 过滤后的选股结果，每个时间点的 top_n 概念
    """
    if kwargs.get('copy', True):
        holds = holds.copy()

    holds['概念板块'] = holds['证券代码'].map(concepts).fillna('')
    holds['概念数量'] = holds['概念板块'].apply(len)
    holds = holds[holds['概念数量'] > 0]

    new_holds = []
    dt_key_concepts = {}
    for dt, dfg in tqdm(holds.groupby('成分日期'), desc='计算板块效应'):
        # 计算密集出现的概念
        key_concepts = [k for k, v in Counter([x for y in dfg['概念板块'] for x in y]).most_common(top_n)]
        dt_key_concepts[dt] = key_concepts

        # 计算在密集概念中出现次数超过min_n的股票
        dfg['强势概念'] = dfg['概念板块'].apply(lambda x: ','.join(set(x) & set(key_concepts)))
        sel = dfg[dfg['强势概念'].apply(lambda x: len(x.split(',')) >= min_n)]
        new_holds.append(sel)

    dfh = pd.concat(new_holds, ignore_index=True)
    dfk = pd.DataFrame([{"成分日期": k, '强势概念': v} for k, v in dt_key_concepts.items()])
    return dfh, dfk


def test_get_symbol_concepts():
    import matplotlib.pyplot as plt
    concepts = get_symbol_concepts()
    holds = pd.read_feather(r"D:\ts_data\holds_20180103_20230213.feather")
    dfh, dfk = holds_concepts_effect(holds, concepts, top_n=30, min_n=3)

    old = holds.groupby('成分日期')['n1b'].mean().cumsum().to_frame().dropna()
    new = dfh.groupby('成分日期')['n1b'].mean().cumsum().to_frame().dropna()
    print(f"旧的组合收益：{old.iloc[-1, 0]:.2f}，新的组合收益：{new.iloc[-1, 0]:.2f}，增长：{new.iloc[-1, 0] / old.iloc[-1, 0] - 1:.2%}")
    dfh.groupby('成分日期')['n1b'].mean().cumsum().plot()
    plt.show()
    holds.groupby('成分日期')['n1b'].mean().cumsum().plot()
    plt.show()


