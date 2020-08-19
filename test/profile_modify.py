# coding: utf-8

import os
import numba
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import talib as ta

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, 'dt'] = pd.to_datetime(kline['dt'])
bars = kline.to_dict("records")
# bars_dt = [x['dt'] for x in bars]

# 测试 MA、EMA、MACD 计算性能
# ----------------------------------------------------------------------------------------------------------------------
close = np.array([x['close'] for x in bars], dtype=np.double)

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


# 测试长list截取
# ----------------------------------------------------------------------------------------------------------------------

bars = []
for i in range(500):
    bars.append({"dt": datetime.now() - timedelta(minutes=i), "value": i})

start_dt = bars[-500]['dt']
end_dt = bars[-200]['dt']

def split_v1():
    return [x for x in bars if end_dt >= x['dt'] >= start_dt]

def split_v2():
    bars_dt = {x['dt']: i for i, x in enumerate(bars)}
    start_i = bars_dt[start_dt]
    end_i = bars_dt[end_dt]
    return bars[start_i: end_i+1]

def split_v3():
    a = np.array(bars)
    dts = np.array([x['dt'] for x in bars])
    x1 = dts > start_dt
    x2 = x1 < end_dt

# %timeit x1 = split_v1()
# %timeit x2 = split_v2()


