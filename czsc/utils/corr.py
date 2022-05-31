# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/1/29 15:01
describe: 相关系数计算、可视化

References:
1. https://zhuanlan.zhihu.com/p/362258222
2. https://blog.csdn.net/qq_45538220/article/details/107429201
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import metrics
from tqdm import tqdm

plt.rcParams['font.sans-serif'] = ['SimHei']    # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False      # 用来正常显示负号


def nmi_matrix(df: pd.DataFrame, heatmap=False) -> pd.DataFrame:
    """计算高维标准化互信息并以矩阵形式输出

    :param df: 数据
    :param heatmap: 是否绘制热力图
    :return:
    """
    cols = df.columns.to_list()

    m_dict = {}
    for i, col1 in tqdm(enumerate(cols), desc='nmi'):
        X = df[col1]
        for col2 in cols[i:]:
            Y = df[col2]
            nmi = metrics.normalized_mutual_info_score(X, Y)
            m_dict[f"{col1}_{col2}"] = nmi
            m_dict[f"{col2}_{col1}"] = nmi

    m = []
    for col1 in cols:
        A = []
        for col2 in cols:
            A.append(m_dict[f"{col1}_{col2}"])
        m.append(A)

    dfm = pd.DataFrame(m, index=cols, columns=cols)

    if heatmap:
        print('NMI(标准化互信息) = \n', dfm)
        plt.close()
        figure, ax = plt.subplots(figsize=(len(cols), len(cols)))
        sns.heatmap(dfm, square=True, annot=True, ax=ax)
        plt.show()
    return dfm






