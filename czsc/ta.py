# coding: utf-8
"""

常用技术分析指标：MA, MACD, BOLL
"""
import talib as ta

# def ma(kline, params=(5, 10, 20, 60, 120, 250)):
#     """计算指定周期的若干 MA 均线
#
#     :param kline: pd.DataFrame
#         K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
#     :param params: tuple
#     :return: pd.DataFrame
#         在原始数据中新增若干 MA 均线
#     """
#     for p in params:
#         col = "ma" + str(p)
#         kline.loc[:, col] = kline['close'].rolling(p).mean().apply(round, args=(2,))
#     return kline

def ma(kline, params=(5, 10, 20, 60, 120, 250)):
    """计算指定周期的若干 MA 均线

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :param params: tuple
    :return: pd.DataFrame
        在原始数据中新增若干 MA 均线
    """
    for p in params:
        col = "ma" + str(p)
        kline.loc[:, col] = ta.MA(kline['close'], timeperiod=p, matype=ta.MA_Type.SMA)
        # kline.loc[:, col] = kline[col].apply(round, args=(2,))
    return kline

# def macd(kline):
#     """计算 MACD 指标
#
#     :param kline: pd.DataFrame
#         K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
#     :return: pd.DataFrame
#         在原始数据中新增 diff,dea,macd 三列
#     """
#
#     short_, long_, m = 12, 26, 9
#     kline.loc[:, 'diff'] = kline['close'].ewm(adjust=False, alpha=2 / (short_ + 1), ignore_na=True).mean() - \
#                             kline['close'].ewm(adjust=False, alpha=2 / (long_ + 1), ignore_na=True).mean()
#     kline.loc[:, 'dea'] = kline['diff'].ewm(adjust=False, alpha=2 / (m + 1), ignore_na=True).mean()
#     kline.loc[:, 'macd'] = 2 * (kline['diff'] - kline['dea'])
#
#     for col in ['diff', 'dea', 'macd']:
#         kline.loc[:, col] = kline[col].apply(round, args=(2,))
#     return kline

def macd(kline):
    """计算 MACD 指标

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: pd.DataFrame
        在原始数据中新增 diff,dea,macd 三列
    """
    m1, m2, m3 = ta.MACD(kline.close.values, fastperiod=12, slowperiod=26, signalperiod=9)
    kline.loc[:, 'diff'] = m1
    kline.loc[:, 'dea'] = m2
    kline.loc[:, 'macd'] = m3
    # for col in ['diff', 'dea', 'macd']:
    #     kline.loc[:, col] = kline[col].apply(round, args=(2,))
    return kline

def boll(kline):
    """计算 BOLL 指标

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: pd.DataFrame
        在原始数据中新增 BOLL 指标结果
    """
    kline.loc[:, 'boll-mid'] = kline['close'].rolling(26).mean()
    kline.loc[:, 'boll-tmp2'] = kline['close'].rolling(20).std()
    kline.loc[:, 'boll-top'] = kline['boll-mid'] + 2 * kline['boll-tmp2']
    kline.loc[:, 'boll-bottom'] = kline['boll-mid'] - 2 * kline['boll-tmp2']

    # for col in ['boll-mid', 'boll-top', 'boll-bottom']:
    #     kline.loc[:, col] = kline[col].apply(round, args=(2,))
    return kline
