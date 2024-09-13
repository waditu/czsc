# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/1/24 15:01
describe: 常用技术分析指标
"""
import numpy as np
import pandas as pd


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
            seq = close[0 : i + 1]
        else:
            seq = close[i - timeperiod + 1 : i + 1]
        res.append(seq.mean())
    return np.array(res, dtype=np.double).round(4)


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
            ema = (2 * close[i] + res[i - 1] * (timeperiod - 1)) / (timeperiod + 1)
            res.append(ema)
    return np.array(res, dtype=np.double).round(4)


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
    return diff.round(4), dea.round(4), macd.round(4)


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
            h_ = high[0 : i + 1]
            l_ = low[0 : i + 1]
        else:
            h_ = high[i - n + 1 : i + 1]
            l_ = low[i - n + 1 : i + 1]
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
            k_ = (2 / 3) * k[i - 1] + (1 / 3) * rsv[i]
            d_ = (2 / 3) * d[i - 1] + (1 / 3) * k_

        k.append(k_)
        d.append(d_)
        j.append(3 * k_ - 2 * d_)

    k = np.array(k, dtype=np.double)
    d = np.array(d, dtype=np.double)
    j = np.array(j, dtype=np.double)
    return k.round(4), d.round(4), j.round(4)


def RSQ(close: [np.array, list]) -> float:
    """拟合优度 R Square

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


def plus_di(high, low, close, timeperiod=14):
    """
    Calculate Plus Directional Indicator (PLUS_DI) manually.

    Parameters:
    high (pd.Series): High price series.
    low (pd.Series): Low price series.
    close (pd.Series): Closing price series.
    timeperiod (int): Number of periods to consider for the calculation.

    Returns:
    pd.Series: Plus Directional Indicator values.
    """
    # Calculate the +DM (Directional Movement)
    dm_plus = high - high.shift(1)
    dm_plus[dm_plus < 0] = 0  # Only positive differences are considered

    # Calculate the True Range (TR)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)

    # Smooth the +DM and TR with Wilder's smoothing method
    smooth_dm_plus = dm_plus.rolling(window=timeperiod).sum()
    smooth_tr = tr.rolling(window=timeperiod).sum()

    # Avoid division by zero
    smooth_tr[smooth_tr == 0] = np.nan

    # Calculate the Directional Indicator
    plus_di_ = 100 * (smooth_dm_plus / smooth_tr)

    return plus_di_


def minus_di(high, low, close, timeperiod=14):
    """
    Calculate Minus Directional Indicator (MINUS_DI) manually.

    Parameters:
    high (pd.Series): High price series.
    low (pd.Series): Low price series.
    close (pd.Series): Closing price series.
    timeperiod (int): Number of periods to consider for the calculation.

    Returns:
    pd.Series: Minus Directional Indicator values.
    """
    # Calculate the -DM (Directional Movement)
    dm_minus = (low.shift(1) - low).where((low.shift(1) - low) > (high - low.shift(1)), 0)

    # Smooth the -DM with Wilder's smoothing method
    smooth_dm_minus = dm_minus.rolling(window=timeperiod).sum()

    # Calculate the True Range (TR)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)

    # Smooth the TR with Wilder's smoothing method
    smooth_tr = tr.rolling(window=timeperiod).sum()

    # Avoid division by zero
    smooth_tr[smooth_tr == 0] = pd.NA

    # Calculate the Directional Indicator
    minus_di_ = 100 * (smooth_dm_minus / smooth_tr.fillna(method="ffill"))

    return minus_di_


def atr(high, low, close, timeperiod=14):
    """
    Calculate Average True Range (ATR).

    Parameters:
    high (pd.Series): High price series.
    low (pd.Series): Low price series.
    close (pd.Series): Closing price series.
    timeperiod (int): Number of periods to consider for the calculation.

    Returns:
    pd.Series: Average True Range values.
    """
    # Calculate True Range (TR)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (close.shift() - low).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate ATR
    atr_ = tr.rolling(window=timeperiod).mean()

    return atr_


def MFI(high, low, close, volume, timeperiod=14):
    """
    Calculate Money Flow Index (MFI).

    Parameters:
    high (np.array): Array of high prices.
    low (np.array): Array of low prices.
    close (np.array): Array of closing prices.
    volume (np.array): Array of trading volumes.
    timeperiod (int): Number of periods to consider for the calculation.

    Returns:
    np.array: Array of Money Flow Index values.
    """
    # Calculate Typical Price
    typical_price = (high + low + close) / 3

    # Calculate Raw Money Flow
    raw_money_flow = typical_price * volume

    # Calculate Positive and Negative Money Flow
    positive_money_flow = np.where(typical_price > typical_price.shift(1), raw_money_flow, 0)
    negative_money_flow = np.where(typical_price < typical_price.shift(1), raw_money_flow, 0)

    # Calculate Money Ratio
    money_ratio = (
        positive_money_flow.rolling(window=timeperiod).sum() / negative_money_flow.rolling(window=timeperiod).sum()
    )

    # Calculate Money Flow Index
    mfi = 100 - (100 / (1 + money_ratio))

    return mfi


def CCI(high, low, close, timeperiod=14):
    """
    Calculate Commodity Channel Index (CCI).

    Parameters:
    high (np.array): Array of high prices.
    low (np.array): Array of low prices.
    close (np.array): Array of closing prices.
    timeperiod (int): Number of periods to consider for the calculation.

    Returns:
    np.array: Array of Commodity Channel Index values.
    """
    # Typical Price
    typical_price = (high + low + close) / 3

    # Mean Deviation
    mean_typical_price = np.mean(typical_price, axis=0)
    mean_deviation = np.mean(np.abs(typical_price - mean_typical_price), axis=0)

    # Constant
    constant = 1 / (0.015 * timeperiod)

    # CCI Calculation
    cci = (typical_price - mean_typical_price) / (constant * mean_deviation)
    return cci


def LINEARREG_ANGLE(real, timeperiod=14):
    """
    Calculate the Linear Regression Angle for a given time period.

    https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_LINEARREG_ANGLE.c

    :param real: NumPy ndarray of input data points.
    :param timeperiod: The number of periods to use for the regression (default is 14).
    :return: NumPy ndarray of angles in degrees.
    """
    # Validate input parameters
    if not isinstance(real, np.ndarray) or not isinstance(timeperiod, int):
        raise ValueError("Invalid input parameters.")
    if timeperiod < 2 or timeperiod > 100000:
        raise ValueError("timeperiod must be between 2 and 100000.")
    if len(real) < timeperiod:
        raise ValueError("Input data must have at least timeperiod elements.")

    # Initialize output array
    angles = np.zeros(len(real))

    # Calculate the total sum and sum of squares for the given time period
    SumX = timeperiod * (timeperiod - 1) * 0.5
    SumXSqr = timeperiod * (timeperiod - 1) * (2 * timeperiod - 1) / 6
    Divisor = SumX * SumX - timeperiod * SumXSqr

    # Calculate the angle for each point in the input array
    for today in range(timeperiod - 1, len(real)):
        SumXY = 0
        SumY = 0
        for i in range(timeperiod):
            SumY += real[today - i]
            SumXY += i * real[today - i]
        m = (timeperiod * SumXY - SumX * SumY) / Divisor
        angles[today] = np.arctan(m) * (180.0 / np.pi)

    return angles
