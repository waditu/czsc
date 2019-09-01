# coding: utf-8

import os
import shutil
from collections import OrderedDict
from .analyze import preprocess


cache_path = os.path.join(os.path.expanduser('~'), ".chan")
if not os.path.exists(cache_path):
    os.mkdir(cache_path)


def clean_cache():
    shutil.rmtree(cache_path)
    os.mkdir(cache_path)


def ma(kline, params=(5, 10, 20, 60, 120, 250)):
    """计算指定周期的若干 MA 均线

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :param params: tuple
    :return: pd.DataFrame
        在原始数据中新增若干 MA 均线
    """
    for p in params:
        col = "ma"+str(p)
        kline[col] = kline['close'].rolling(p).mean()
        kline[col] = kline[col].apply(round, args=(2,))
    return kline


def macd(kline):
    """计算 MACD 指标

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: pd.DataFrame
        在原始数据中新增 diff,dea,macd 三列
    """

    short_, long_, m = 12, 26, 9
    kline['diff'] = kline['close'].ewm(adjust=False, alpha=2 / (short_ + 1), ignore_na=True).mean() - \
                    kline['close'].ewm(adjust=False, alpha=2 / (long_ + 1), ignore_na=True).mean()
    kline['dea'] = kline['diff'].ewm(adjust=False, alpha=2 / (m + 1), ignore_na=True).mean()
    kline['macd'] = 2 * (kline['diff'] - kline['dea'])

    kline['diff'] = kline['diff'].apply(round, args=(2,))
    kline['dea'] = kline['dea'].apply(round, args=(2,))
    kline['macd'] = kline['macd'].apply(round, args=(2,))
    return kline


def boll(kline):
    """计算 BOLL 指标

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: pd.DataFrame
        在原始数据中新增 BOLL 指标结果
    """
    kline['boll-mid'] = kline['close'].rolling(26).mean()
    kline['boll-tmp2'] = kline['close'].rolling(20).std()
    kline['boll-top'] = kline['boll-mid'] + 2*kline['boll-tmp2']
    kline['boll-bottom'] = kline['boll-mid'] - 2*kline['boll-tmp2']

    kline['boll-mid'] = kline['boll-mid'].apply(round, args=(2,))
    kline['boll-tmp2'] = kline['boll-tmp2'].apply(round, args=(2,))
    kline['boll-top'] = kline['boll-top'].apply(round, args=(2,))
    kline['boll-bottom'] = kline['boll-bottom'].apply(round, args=(2,))
    return kline


def kline_status(kline):
    """计算 kline 的当下状态

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: OrderedDict
    """
    kline = ma(kline)
    kline = macd(kline)

    # MACD 多空状态
    last_raw = kline.iloc[-1]
    if last_raw['diff'] < 0 and last_raw['dea'] < 0:
        macd_status = '空头行情'
    elif last_raw['diff'] > 0 and last_raw['dea'] > 0:
        macd_status = '多头行情'
    else:
        macd_status = '转折行情'

    # 最近三根K线状态
    pred = preprocess(kline)
    last_three = pred.iloc[-3:]

    # 笔状态：最近三根 K 线的走势状态
    if min(last_three['low']) == last_three.iloc[-1]['low']:
        bi_status = "向下笔延伸中"
    elif min(last_three['low']) == last_three.iloc[-2]['low']:
        bi_status = "底分型构造中"
    elif max(last_three['high']) == last_three.iloc[-1]['high']:
        bi_status = "向上笔延伸中"
    elif max(last_three['high']) == last_three.iloc[-2]['high']:
        bi_status = "顶分型构造中"
    else:
        raise ValueError("kline 数据出错")

    return OrderedDict(macd_status=macd_status, bi_status=bi_status)
