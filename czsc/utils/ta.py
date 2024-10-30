# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/1/24 15:01
describe: 常用技术分析指标

参考链接：
1. https://github.com/twopirllc/pandas-ta

"""
import numpy as np
import pandas as pd
import pandas_ta


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


def WMA(close: np.array, timeperiod=5):
    """加权移动平均

    :param close: np.array
        收盘价序列
    :param timeperiod: int
        均线参数
    :return: np.array
    """
    res = []
    for i in range(len(close)):
        if i < timeperiod:
            res.append(np.nan)
            continue

        seq = close[i - timeperiod + 1 : i + 1]
        res.append(np.average(seq, weights=range(1, len(seq) + 1)))
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


def MACD(real: np.array, fastperiod=12, slowperiod=26, signalperiod=9):
    """MACD 异同移动平均线
    https://baike.baidu.com/item/MACD%E6%8C%87%E6%A0%87/6271283

    :param real: np.array
        价格序列
    :param fastperiod: int
        快周期，默认值 12
    :param slowperiod: int
        慢周期，默认值 26
    :param signalperiod: int
        信号周期，默认值 9
    :return: (np.array, np.array, np.array)
        diff, dea, macd
    """
    ema12 = EMA(real, timeperiod=fastperiod)
    ema26 = EMA(real, timeperiod=slowperiod)
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
    x_squared_sum = sum([x1 * x1 for x1 in x])
    xy_product_sum = sum([x[i] * y[i] for i in range(len(x))])
    num = len(x)
    x_sum = sum(x)
    y_sum = sum(y)
    delta = float(num * x_squared_sum - x_sum * x_sum)
    if delta == 0:
        return 0
    y_intercept = (1 / delta) * (x_squared_sum * y_sum - x_sum * xy_product_sum)
    slope = (1 / delta) * (num * xy_product_sum - x_sum * y_sum)

    y_mean = np.mean(y)
    ss_tot = sum([(y1 - y_mean) * (y1 - y_mean) for y1 in y]) + 0.00001
    ss_err = sum([(y[i] - slope * x[i] - y_intercept) * (y[i] - slope * x[i] - y_intercept) for i in range(len(x))])
    rsq = 1 - ss_err / ss_tot

    return round(rsq, 4)


def PLUS_DI(high, low, close, timeperiod=14):
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


def MINUS_DI(high, low, close, timeperiod=14):
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


def ATR(high, low, close, timeperiod=14):
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


def DOUBLE_SMA_LS(series: pd.Series, n=5, m=20, **kwargs):
    """双均线多空

    :param series: str, 数据源字段
    :param n: int, 短周期
    :param m: int, 长周期
    """
    assert n < m, "短周期必须小于长周期"
    return np.sign(series.rolling(window=n).mean() - series.rolling(window=m).mean()).fillna(0)


def BOLL_LS(series: pd.Series, n=5, s=0.1, **kwargs):
    """布林线多空

    series 大于 n 周期均线 + s * n周期标准差，做多；小于 n 周期均线 - s * n周期标准差，做空

    :param series: str, 数据源字段
    :param n: int, 短周期
    :param s: int, 波动率的倍数，默认为 0.1
    """
    sm = series.rolling(window=n).mean()
    sd = series.rolling(window=n).std()
    return np.where(series > sm + s * sd, 1, np.where(series < sm - s * sd, -1, 0))


def SMA_MIN_MAX_SCALE(series: pd.Series, timeperiod=5, window=5, **kwargs):
    """均线的最大最小值归一化

    :param series: str, 数据源字段
    :param timeperiod: int, 均线周期
    :param window: int, 窗口大小
    """
    sm = series.rolling(window=timeperiod).mean()
    sm_min = sm.rolling(window=window).min()
    sm_max = sm.rolling(window=window).max()
    res = (sm - sm_min) / (sm_max - sm_min)
    res = res.fillna(0) * 2 - 1
    return res


def RS_VOLATILITY(df: pd.DataFrame, timeperiod=30, **kwargs):
    """RS 波动率，值越大，波动越大

    :param df: str, 标准K线数据
    :param timeperiod: int, 周期
    """
    log_h_c = np.log(df["high"] / df["close"])
    log_h_o = np.log(df["high"] / df["open"])
    log_l_c = np.log(df["low"] / df["close"])
    log_l_o = np.log(df["low"] / df["open"])

    x = log_h_c * log_h_o + log_l_c * log_l_o
    res = np.sqrt(x.rolling(window=timeperiod).mean())
    return res


def PK_VOLATILITY(df: pd.DataFrame, timeperiod=30, **kwargs):
    """PK 波动率，值越大，波动越大

    :param df: str, 标准K线数据
    :param timeperiod: int, 周期
    """
    log_h_l = np.log(df["high"] / df["low"]).pow(2)
    log_hl_mean = log_h_l.rolling(window=timeperiod).sum() / (4 * timeperiod * np.log(2))
    res = np.sqrt(log_hl_mean)
    return res


def SNR(real: pd.Series, timeperiod=14, **kwargs):
    """信噪比（Signal Noise Ratio，SNR）"""
    return real.diff(timeperiod) / real.diff().abs().rolling(window=timeperiod).sum()


try:
    import talib as ta

    SMA = ta.SMA
    EMA = ta.EMA
    MACD = ta.MACD
    PPO = ta.PPO
    ATR = ta.ATR
    PLUS_DI = ta.PLUS_DI
    MINUS_DI = ta.MINUS_DI
    MFI = ta.MFI
    CCI = ta.CCI
    BOLL = ta.BBANDS
    RSI = ta.RSI
    ADX = ta.ADX
    ADXR = ta.ADXR
    AROON = ta.AROON
    AROONOSC = ta.AROONOSC
    ROCR = ta.ROCR
    ROCR100 = ta.ROCR100
    TRIX = ta.TRIX
    ULTOSC = ta.ULTOSC
    WILLR = ta.WILLR
    LINEARREG = ta.LINEARREG
    LINEARREG_ANGLE = ta.LINEARREG_ANGLE
    LINEARREG_INTERCEPT = ta.LINEARREG_INTERCEPT
    LINEARREG_SLOPE = ta.LINEARREG_SLOPE

    KAMA = ta.KAMA
    STOCH = ta.STOCH
    STOCHF = ta.STOCHF
    STOCHRSI = ta.STOCHRSI
    T3 = ta.T3
    TEMA = ta.TEMA
    TRIMA = ta.TRIMA
    WMA = ta.WMA
    BBANDS = ta.BBANDS
    DEMA = ta.DEMA
    HT_TRENDLINE = ta.HT_TRENDLINE

    BOP = ta.BOP
    CMO = ta.CMO
    DX = ta.DX
    BETA = ta.BETA


except ImportError:
    print(
        f"ta-lib 没有正确安装，将使用自定义分析函数。建议安装 ta-lib，可以大幅提升计算速度。"
        f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091"
    )


def CHOP(high, low, close, **kwargs):
    """Choppiness Index

    为了确定市场当前是否在波动或趋势中，可以使用波动指数。波动指数是由澳大利亚大宗商品交易员 Bill Dreiss 开发的波动率指标。
    波动指数不是为了预测未来的市场方向，而是用于量化当前市场的“波动”。波动的市场是指价格大幅上下波动的市场。
    波动指数的值在 100 和 0 之间波动。值越高，市场波动性越高。

    Sources:
        https://www.tradingview.com/scripts/choppinessindex/
        https://www.motivewave.com/studies/choppiness_index.htm

    Calculation:
        Default Inputs:
            length=14, scalar=100, drift=1

        HH = high.rolling(length).max()
        LL = low.rolling(length).min()
        ATR_SUM = SUM(ATR(drift), length)
        CHOP = scalar * (LOG10(ATR_SUM) - LOG10(HH - LL)) / LOG10(length)

    :param high: pd.Series, Series of 'high's
    :param low: pd.Series, Series of 'low's
    :param close: pd.Series, Series of 'close's
    :param kwargs: dict, Additional arguments

        - length (int): It's period. Default: 14
        - atr_length (int): Length for ATR. Default: 1
        - ln (bool): If True, uses ln otherwise log10. Default: False
        - scalar (float): How much to magnify. Default: 100
        - drift (int): The difference period. Default: 1
        - offset (int): How many periods to offset the result. Default: 0
        - fillna (value): pd.DataFrame.fillna(value)
        - fill_method (value): Type of fill method

    :return: pd.Series, New feature generated.
    """
    return pandas_ta.chop(high=high, low=low, close=close, **kwargs)


def SNR(real: pd.Series, timeperiod=14, **kwargs):
    """信噪比（Signal Noise Ratio，SNR）"""
    return real.diff(timeperiod).abs() / real.diff().abs().rolling(window=timeperiod).sum()


def rolling_polyfit(real: pd.Series, window=20, degree=1):
    """滚动多项式拟合系数

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    :param degree: int, 多项式次数
    """
    res = real.rolling(window=window).apply(lambda x: np.polyfit(range(len(x)), x, degree)[0], raw=True)
    return res


def rolling_auto_corr(real: pd.Series, window=20, lag=1):
    """滚动自相关系数

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    :param lag: int, 滞后期
    """
    res = real.rolling(window=window).apply(lambda x: x.autocorr(lag), raw=True)
    return res


def rolling_ptp(real: pd.Series, window=20):
    """滚动极差

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = real.rolling(window=window).apply(lambda x: np.max(x) - np.min(x), raw=True)
    return res


def rolling_skew(real: pd.Series, window=20):
    """滚动偏度

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = real.rolling(window=window).skew()
    return res


def rolling_kurt(real: pd.Series, window=20):
    """滚动峰度

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = real.rolling(window=window).kurt()
    return res


def rolling_corr(x: pd.Series, y: pd.Series, window=20):
    """滚动相关系数

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).corr(y)
    return res


def rolling_cov(x: pd.Series, y: pd.Series, window=20):
    """滚动协方差

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).cov(y)
    return res


def rolling_beta(x: pd.Series, y: pd.Series, window=20):
    """滚动贝塔系数

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = rolling_cov(x, y, window) / rolling_cov(y, y, window)
    return res


def rolling_alpha(x: pd.Series, y: pd.Series, window=20):
    """滚动阿尔法系数

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).mean() - rolling_beta(x, y, window) * y.rolling(window=window).mean()
    return res


def rolling_rsq(x: pd.Series, window=20):
    """滚动拟合优度

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).apply(lambda x1: RSQ(x1), raw=True)
    return res


def rolling_argmax(x: pd.Series, window=20):
    """滚动最大值位置

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).apply(lambda x1: np.argmax(x1), raw=True)
    return res


def rolling_argmin(x: pd.Series, window=20):
    """滚动最小值位置

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).apply(lambda x1: np.argmin(x1), raw=True)
    return res


def rolling_ir(x: pd.Series, window=20):
    """滚动信息系数

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).mean() / x.rolling(window=window).std().replace(0, np.nan)
    return res


def rolling_zscore(x: pd.Series, window=20):
    """滚动标准化

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = (x - x.rolling(window=window).mean()) / x.rolling(window=window).std().replace(0, np.nan)
    return res


def rolling_rank(x: pd.Series, window=20):
    """滚动排名

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).rank(pct=True, ascending=True, method="first")
    return res


def rolling_max(x: pd.Series, window=20):
    """滚动最大值

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).max()
    return res


def rolling_min(x: pd.Series, window=20):
    """滚动最小值

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).min()
    return res


def rolling_mdd(x: pd.Series, window=20):
    """滚动最大回撤

    :param x: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = x.rolling(window=window).apply(lambda x1: 1 - (x1 / np.maximum.accumulate(x1)).min(), raw=True)
    return res


def rolling_rank_sub(x: pd.Series, y: pd.Series, window=20):
    """滚动排名差

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = rolling_rank(x, window) - rolling_rank(y, window)
    return res


def rolling_rank_div(x: pd.Series, y: pd.Series, window=20):
    """滚动排名比

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = rolling_rank(x, window) / rolling_rank(y, window)
    return res


def rolling_rank_mul(x: pd.Series, y: pd.Series, window=20):
    """滚动排名乘

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = rolling_rank(x, window) * rolling_rank(y, window)
    return res


def rolling_rank_sum(x: pd.Series, y: pd.Series, window=20):
    """滚动排名和

    :param x: pd.Series, 数据源
    :param y: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = rolling_rank(x, window) + rolling_rank(y, window)
    return res


def rolling_vwap(close: pd.Series, volume: pd.Series, window=20):
    """滚动成交量加权平均价格

    :param close: pd.Series, 收盘价
    :param volume: pd.Series, 成交量
    :param window: int, 窗口大小
    """
    res = (close * volume).rolling(window=window).sum() / volume.rolling(window=window).sum().replace(0, np.nan)
    return res


def rolling_obv(close: pd.Series, volume: pd.Series, window=200):
    """滚动能量潮

    :param close: pd.Series, 收盘价
    :param volume: pd.Series, 成交量
    :param window: int, 窗口大小
    """
    res = np.where(close.diff() > 0, volume, np.where(close.diff() < 0, -volume, 0))
    res = res.rolling(window=window).sum()
    return res


def rolling_pvt(close: pd.Series, volume: pd.Series, window=20):
    """滚动价格成交量趋势

    :param close: pd.Series, 收盘价
    :param volume: pd.Series, 成交量
    :param window: int, 窗口大小
    """
    res = ((close.diff() / close.shift(1)) * volume).rolling(window=window).sum()
    return res


def rolling_pvi(close: pd.Series, volume: pd.Series, window=20):
    """滚动正量指标

    :param close: pd.Series, 收盘价
    :param volume: pd.Series, 成交量
    :param window: int, 窗口大小
    """
    res = np.where(close.diff() > 0, volume, 0).rolling(window=window).sum()
    return res


def rolling_std(real: pd.Series, window=20):
    """滚动标准差

    :param real: pd.Series, 数据源
    :param window: int, 窗口大小
    """
    res = real.rolling(window=window).std()
    return res


def ultimate_smoother(price, period: int = 7):
    """Ultimate Smoother

    https://www.95sca.cn/archives/111068

    终极平滑器（Ultimate Smoother）是由交易系统和算法交易策略开发者John Ehlers设计的
    一种技术分析指标，它是一种趋势追踪指标，用于识别股票价格的趋势。

    :param price: np.array, 价格序列
    :param period: int, 周期
    :return:
    """
    # 初始化变量
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * 180 / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4

    # 准备输出结果的序列
    us = np.zeros(len(price))

    # 计算 Ultimate Smoother
    for i in range(len(price)):
        if i < 4:
            us[i] = price[i]
        else:
            us[i] = (
                (1 - c1) * price[i]
                + (2 * c1 - c2) * price[i - 1]
                - (c1 + c3) * price[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return us


def sigmoid(x):
    """Sigmoid 函数"""
    return 1 / (1 + np.exp(-x))


def log_return(x):
    """对数收益率"""
    return np.log(x / x.shift(1))
