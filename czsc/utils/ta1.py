# coding: utf-8
"""

常用技术分析指标：MA, MACD, BOLL

使用 ta-lib 可以大幅提升计算性能，10倍左右
"""
import numpy as np
import talib as ta

SMA = ta.SMA
EMA = ta.EMA
MACD = ta.MACD


def KDJ(close: np.array, high: np.array, low: np.array):
    """

    :param close: 收盘价序列
    :param high: 最高价序列
    :param low: 最低价序列
    :return:
    """
    n = 9
    hv = []
    lv = []
    for i in range(len(close)):
        if i < n:
            h_ = high[0: i+1]
            l_ = low[0: i+1]
        else:
            h_ = high[i - n + 1: i + 1]
            l_ = low[i - n + 1: i + 1]
        hv.append(max(h_))
        lv.append(min(l_))

    hv = np.around(hv, decimals=2)
    lv = np.around(lv, decimals=2)
    rsv = np.where(hv == lv, 0, (close - lv) / (hv - lv) * 100)

    k = []
    d = []
    j = []
    for i in range(len(rsv)):
        if i < n:
            k_ = rsv[i]
            d_ = k_
        else:
            k_ = (2 / 3) * k[i-1] + (1 / 3) * rsv[i]
            d_ = (2 / 3) * d[i-1] + (1 / 3) * k_

        k.append(k_)
        d.append(d_)
        j.append(3 * k_ - 2 * d_)

    k = np.array(k, dtype=np.double)
    d = np.array(d, dtype=np.double)
    j = np.array(j, dtype=np.double)
    return k, d, j

def RSQ(close: [np.array, list]) -> float:
    """拟合优度 R SQuare

    :param close: 收盘价序列
    :return:
    """
    x = list(range(len(close)))
    y = np.array(close)
    x_squred_sum = sum([x1 * x1 for x1 in x])
    xy_product_sum = sum([x[i] * y[i] for i in range(len(x))])
    num = len(x)
    x_sum = sum(x)
    y_sum = sum(y)
    delta = float(num * x_squred_sum - x_sum * x_sum)
    if delta == 0:
        return 0
    y_intercept = (1 / delta) * (x_squred_sum * y_sum - x_sum * xy_product_sum)
    slope = (1 / delta) * (num * xy_product_sum - x_sum * y_sum)

    y_mean = np.mean(y)
    ss_tot = sum([(y1 - y_mean) * (y1 - y_mean) for y1 in y]) + 0.00001
    ss_err = sum([(y[i] - slope * x[i] - y_intercept) * (y[i] - slope * x[i] - y_intercept) for i in range(len(x))])
    rsq = 1 - ss_err / ss_tot

    return round(rsq, 4)

