# coding: utf-8

import os
import numba
import numpy as np
import pandas as pd
from datetime import datetime
import talib as ta

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, 'dt'] = pd.to_datetime(kline['dt'])
bars = kline.to_dict("records")
close = np.array([x['close'] for x in bars], dtype=np.double)
# bars = [{k: v for k, v in zip(kline.columns, row)} for row in kline.values]
bars_s = pd.Series(bars, index=[x['dt'] for x in bars])

# 测试用 Series 给 List 加索引的性能
start_dt = datetime.strptime('2020-07-01 10:31:00', "%Y-%m-%d %H:%M:%S")
end_dt = datetime.strptime('2020-07-01 14:31:00', "%Y-%m-%d %H:%M:%S")

# %timeit inside_k1 = [x for x in bars if end_dt >= x['dt'] >= start_dt]
# %timeit inside_k2 = bars_s[start_dt: end_dt]

def SMA_V1(close: np.array, p=5):
    res = []
    for i in range(len(close)):
        if i < p:
            seq = close[0: i+1]
        else:
            seq = close[i - 4: i + 1]
        res.append(seq.mean())
    return np.array(res, dtype=np.double)


@numba.njit()
def SMA_V2(close: np.array, p=5):
    res = []
    for i in range(len(close)):
        if i < p:
            seq = close[0: i+1]
        else:
            seq = close[i - 4: i + 1]
        res.append(seq.mean())
    return np.array(res, dtype=np.double)

def SMA_V3(close: np.array, p=5):
    return ta.SMA(close, timeperiod=p)


# %timeit ma5_v1 = SMA_V1(close, p=5)
# %timeit ma5_v2 = SMA_V2(close, p=5)
# %timeit ma5_v3 = SMA_V3(close, p=5)


def EMA_V1(close: np.array, p=5):
    res = []
    for i in range(len(close)):
        if i < 1:
            res.append(close[i])
        else:
            ema = (2 * close[i] + res[i-1] * (p-1)) / (p+1)
            res.append(ema)
    return np.array(res, dtype=np.double)


@numba.njit()
def EMA_V2(close: np.array, p=5):
    """
    https://baike.baidu.com/item/EMA/12646151

    :param close:
    :param p:
    :return:
    """
    res = []
    for i in range(len(close)):
        if i < 1:
            res.append(close[i])
        else:
            ema = (2 * close[i] + res[i-1] * (p-1)) / (p+1)
            res.append(ema)
    return np.array(res, dtype=np.double)


def EMA_V3(close: np.array, p=5):
    return ta.EMA(close, timeperiod=p)


# %timeit ema5_v1 = EMA_V1(close, p=5)
# %timeit ema5_v2 = EMA_V2(close, p=5)
# %timeit ema5_v3 = EMA_V3(close, p=5)


def MACD_V1(close: np.array):
    ema12 = EMA_V1(close, p=12)
    ema26 = EMA_V1(close, p=26)
    diff = ema12 - ema26
    dea = EMA_V1(diff, p=9)
    macd = (diff - dea) * 2
    return diff, dea, macd

@numba.njit()
def MACD_V2(close: np.array):
    ema12 = EMA_V2(close, p=12)
    ema26 = EMA_V2(close, p=26)
    diff = ema12 - ema26
    dea = EMA_V2(diff, p=9)
    macd = (diff - dea) * 2
    return diff, dea, macd

def MACD_V3(close: np.array):
    return ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

# %timeit x1 = MACD_V1(close)
# %timeit x2 = MACD_V2(close)
# %timeit x3 = MACD_V3(close)
