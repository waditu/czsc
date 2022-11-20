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
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import metrics
from tqdm import tqdm
from typing import Union


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


def single_linear(y: Union[np.array, list], x: Union[np.array, list] = None) -> dict:
    """单变量线性拟合

    :param y: 目标序列
    :param x: 单变量值
    :return res: 拟合结果，样例如下
        {'slope': 1.565, 'intercept': 67.9783, 'r2': 0.9967}

        slope       标识斜率
        intercept   截距
        r2          拟合优度
    """
    if not x:
        x = list(range(len(y)))

    x_squred_sum = sum([x1 * x1 for x1 in x])
    xy_product_sum = sum([x[i] * y[i] for i in range(len(x))])
    num = len(x)
    x_sum = sum(x)
    y_sum = sum(y)
    delta = float(num * x_squred_sum - x_sum * x_sum)
    if delta == 0:
        return {'slope': 0, 'intercept': 0, 'r2': 0}

    y_intercept = (1 / delta) * (x_squred_sum * y_sum - x_sum * xy_product_sum)
    slope = (1 / delta) * (num * xy_product_sum - x_sum * y_sum)

    y_mean = np.mean(y)
    ss_tot = sum([(y1 - y_mean) * (y1 - y_mean) for y1 in y]) + 0.00001
    ss_err = sum([(y[i] - slope * x[i] - y_intercept) * (y[i] - slope * x[i] - y_intercept) for i in range(len(x))])
    rsq = 1 - ss_err / ss_tot

    res = {'slope': round(slope, 4), 'intercept': round(y_intercept, 4), 'r2': round(rsq, 4)}
    return res



