# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 18:50
"""
import pandas as pd
import numpy as np
from tqdm import tqdm
from collections import Counter
from typing import List, Tuple


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


def turn_over_rate(df_holds: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
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
    dft = pd.pivot_table(df_holds, index="成分日期", columns="证券代码", values="持仓权重", aggfunc="sum")
    dft = dft.fillna(0)
    df_turns = dft.diff().abs().sum(axis=1).reset_index()
    df_turns.columns = ["date", "change"]

    # 由于是 diff 计算，第一个时刻的仓位变化被忽视了，修改一下
    sdt = df_holds["成分日期"].min()
    df_turns.loc[(df_turns["date"] == sdt), "change"] = df_holds[df_holds["成分日期"] == sdt]["持仓权重"].sum()
    return df_turns, round(df_turns.change.sum() / 2, 4)


def holds_concepts_effect(holds: pd.DataFrame, concepts: dict, top_n=20, min_n=3, **kwargs):
    """股票持仓列表的板块效应

    原理概述：在选股时，如果股票的概念板块与组合中的其他股票的概念板块有重合，那么这个股票的表现会更好。

    函数计算逻辑:

    1. 如果kwargs中存在'copy'键且对应值为True，则将holds进行复制。
    2. 为holds添加'概念板块'列，该列的值是holds中'symbol'列对应的股票的概念板块列表，如果没有对应的概念板块则填充为空。
    3. 添加'概念数量'列，该列的值是每个股票的概念板块数量。
    4. 从holds中筛选出概念数量大于0的行，赋值给holds。
    5. 创建空列表new_holds和空字典dt_key_concepts。
    6. 对holds按照'dt'进行分组，遍历每个分组，计算板块效应。
    a. 计算密集出现的概念，选取出现次数最多的前top_n个概念，赋值给key_concepts列表。
    b. 将日期dt和对应的key_concepts存入dt_key_concepts字典。
    c. 计算在密集概念中出现次数超过min_n的股票，将符合条件的股票添加到new_holds列表中。
    7. 使用pd.concat将new_holds中的DataFrame进行合并，忽略索引，赋值给dfh。
    8. 创建DataFrame dfk，其中包含日期(dt)和对应的强势概念(key_concepts)。
    9. 返回dfh和dfk。

    :param holds: 组合股票池数据，样例：

            ===================  =========  ==========
            dt                   symbol         weight
            ===================  =========  ==========
            2023-05-09 00:00:00  601858.SH  0.00333333
            2023-05-09 00:00:00  300502.SZ  0.00333333
            2023-05-09 00:00:00  603258.SH  0.00333333
            2023-05-09 00:00:00  300499.SZ  0.00333333
            2023-05-09 00:00:00  300624.SZ  0.00333333
            ===================  =========  ==========

    :param concepts: 股票的概念板块，样例：
            {
                '002507.SZ': ['电子商务', '超级品牌', '国企改革'],
                '002508.SZ': ['家用电器', '杭州亚运会', '恒大概念']
            }
    :param top_n: 选取前 n 个密集概念
    :param min_n: 单股票至少要有 n 个概念在 top_n 中
    :return: 过滤后的选股结果，每个时间点的 top_n 概念
    """
    if kwargs.get("copy", True):
        holds = holds.copy()

    holds["概念板块"] = holds["symbol"].map(concepts).fillna("")
    holds["概念数量"] = holds["概念板块"].apply(len)
    holds = holds[holds["概念数量"] > 0]

    new_holds = []
    dt_key_concepts = {}
    for dt, dfg in tqdm(holds.groupby("dt"), desc="计算板块效应"):
        # 计算密集出现的概念
        key_concepts = [k for k, v in Counter([x for y in dfg["概念板块"] for x in y]).most_common(top_n)]
        dt_key_concepts[dt] = key_concepts

        # 计算在密集概念中出现次数超过min_n的股票
        dfg["强势概念"] = dfg["概念板块"].apply(lambda x: ",".join(set(x) & set(key_concepts)))
        sel = dfg[dfg["强势概念"].apply(lambda x: len(x.split(",")) >= min_n)]
        new_holds.append(sel)

    dfh = pd.concat(new_holds, ignore_index=True)
    dfk = pd.DataFrame([{"dt": k, "强势概念": v} for k, v in dt_key_concepts.items()])
    return dfh, dfk
