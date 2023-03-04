# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/28 15:46
describe: 
"""
import pandas as pd
import matplotlib.pyplot as plt


plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def plot_bins_return(dfv, bins_col='ma_score_bins10', file_png="bins.png"):
    """绘制 bins_col 的分层收益曲线

    :param dfv: 日频分层数据，数据样例如下，dt、n1b、bins_col 是必须的列
                  dt    ts_code       n1b  ma_score_bins10
        0 2020-01-02  884220.TI  -62.8252             10.0
        1 2020-01-02  881167.TI  380.7587             10.0
        2 2020-01-02  884250.TI   24.1664             10.0
        3 2020-01-02  884249.TI   13.6217             10.0
        4 2020-01-02  881174.TI  141.6936             10.0
    :param bins_col: 分层列名
    :param file_png: 绘图结果文件
    :return:
    """
    dfv['dt'] = pd.to_datetime(dfv['dt'])
    nv = dfv.groupby('dt')[['n1b']].mean()
    nv.rename({'n1b': 'base'}, axis=1, inplace=True)
    nv.reset_index(drop=False, inplace=True)

    # 绘制收益曲线
    plt.close()
    n = dfv[bins_col].nunique()
    fig = plt.figure(figsize=(13, 4*n))
    axes = fig.subplots(n, 1, sharex=True)

    for i, v in enumerate(sorted(dfv[bins_col].unique())):
        dfg = dfv[dfv[bins_col] == v]
        _nv = nv.copy(deep=True)
        n1b = dfg.groupby('dt')[['n1b']].mean().reset_index(drop=False)
        _nv = _nv.merge(n1b, on=['dt'], how='left')
        _nv = _nv.fillna(0)

        _nv['nv1'] = _nv['n1b'].cumsum()
        _nv['nv2'] = _nv['base'].cumsum()
        _nv['nv3'] = _nv['nv1'] - _nv['nv2']
        event = f'{bins_col}_{v}'

        mean_counts = round(dfg.groupby('dt')['n1b'].count().mean(), 2)

        ax = axes[i]
        ax.set_title(f"{event}，平均持仓数={mean_counts}")
        x = _nv['dt']
        ax.plot(x, _nv['nv3'], "r-", alpha=0.4)
        ax.plot(x, _nv['nv2'], "b-", alpha=0.4)
        ax.plot(x, _nv['nv1'], "g-", alpha=0.4)
        ax.legend(['超额收益', "基准收益", '组合收益'], loc='upper left')
        ax.set_ylabel("净值（单位: BP）")
        plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(file_png, bbox_inches='tight', dpi=100)
    plt.close()