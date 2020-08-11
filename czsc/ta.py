# coding: utf-8
"""

常用技术分析指标：MA, MACD, BOLL
"""
import numpy as np
import numba

@numba.njit()
def SMA(close: np.array, timeperiod=5):
    """简单移动平均

    https://baike.baidu.com/item/%E7%A7%BB%E5%8A%A8%E5%B9%B3%E5%9D%87%E7%BA%BF/217887

    :param close: np.array
        收盘价序列
    :param timeperiod: int
        均线参数
    :return: np.array
    """
    res = []
    for i in range(len(close)):
        if i < timeperiod:
            seq = close[0: i+1]
        else:
            seq = close[i - timeperiod + 1: i + 1]
        res.append(seq.mean())
    return np.array(res, dtype=np.double)

@numba.njit()
def EMA(close: np.array, timeperiod=5):
    """
    https://baike.baidu.com/item/EMA/12646151

    :param close: np.array
        收盘价序列
    :param timeperiod: int
        均线参数
    :return: np.array
    """
    res = []
    for i in range(len(close)):
        if i < 1:
            res.append(close[i])
        else:
            ema = (2 * close[i] + res[i-1] * (timeperiod-1)) / (timeperiod+1)
            res.append(ema)
    return np.array(res, dtype=np.double)

@numba.njit()
def MACD(close: np.array, fastperiod=12, slowperiod=26, signalperiod=9):
    """MACD 异同移动平均线
    https://baike.baidu.com/item/MACD%E6%8C%87%E6%A0%87/6271283

    :param close: np.array
        收盘价序列
    :param fastperiod: int
        快周期，默认值 12
    :param slowperiod: int
        慢周期，默认值 26
    :param signalperiod: int
        信号周期，默认值 9
    :return: (np.array, np.array, np.array)
        diff, dea, macd
    """
    ema12 = EMA(close, timeperiod=fastperiod)
    ema26 = EMA(close, timeperiod=slowperiod)
    diff = ema12 - ema26
    dea = EMA(diff, timeperiod=signalperiod)
    macd = (diff - dea) * 2
    return diff, dea, macd


