# coding: utf-8
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta


pro = ts.pro_api()


def set_token(token):
    """在同一台机器上只需要调用 set_token 一次就可以

    :param token: str
        tushare.pro 的 token，如果没有，请到这里注册：https://tushare.pro/register?reg=7
    :return: None
    """
    ts.set_token(token)


def get_token():
    """获取调用凭证"""
    return ts.get_token()


def get_concepts():
    """获取概念列表

    https://dataapi.joinquant.com/docs#get_concepts---%E8%8E%B7%E5%8F%96%E6%A6%82%E5%BF%B5%E5%88%97%E8%A1%A8

    :return: df
    """
    return pro.concept(src='ts')

def get_concept_stocks(symbol, date=None):
    """获取概念成份股

    https://tushare.pro/document/2?doc_id=126

    :param symbol: str
        如 GN036
    :param date: str or datetime
        日期，如 2020-08-08
    :return: list

    examples:
    -------
    >>> symbols1 = get_concept_stocks("GN036", date="2020-07-08")
    >>> symbols2 = get_concept_stocks("GN036", date=datetime.now())
    """
    del date
    df = pro.concept_detail(id=symbol, fields='ts_code')
    return list(set([x + "-E" for x in df.ts_code]))

def get_index_stocks(symbol, date=None):
    """获取指数成份股

    https://dataapi.joinquant.com/docs#get_index_stocks---%E8%8E%B7%E5%8F%96%E6%8C%87%E6%95%B0%E6%88%90%E4%BB%BD%E8%82%A1

    :param symbol: str
        如 399300.SZ
    :param date: str or datetime
        日期，如 2020-08-08
    :return: list

    examples:
    -------
    >>> symbols1 = get_index_stocks("000300.XSHG", date="2020-07-08")
    >>> symbols2 = get_index_stocks("000300.XSHG", date=datetime.now())
    """
    if not date:
        date = datetime.now()

    if isinstance(date, str):
        date = pd.to_datetime(date)

    start_date = date - timedelta(days=250)
    end_date = date

    df = pro.index_weight(index_code=symbol, start_date=start_date.strftime("%Y%m%d"),
                          end_date=end_date.strftime("%Y%m%d"))
    return list(set([x + "-E" for x in df.con_code]))


def _get_start_date(end_date, freq):
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    if freq == '1min':
        start_date = end_date - timedelta(days=30)
    elif freq == '5min':
        start_date = end_date - timedelta(days=70)
    elif freq == '30min':
        start_date = end_date - timedelta(days=500)
    elif freq == 'D':
        start_date = end_date - timedelta(weeks=500)
    elif freq == 'W':
        start_date = end_date - timedelta(weeks=1000)
    elif freq == 'M':
        start_date = end_date - timedelta(weeks=2000)
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date

def get_kline(symbol,  end_date, freq, start_date=None, count=None):
    """获取K线数据

    :param symbol: str
        Tushare 标的代码 + Tushare asset 代码，如 000001.SH-I
    :param start_date: datetime
        截止日期
    :param end_date: datetime
        截止日期
    :param freq: str
        K线级别，可选值 ['1min', '5min', '30min', '60min', 'D', 'W', "M"]
    :param count: int
        K线数量，最大值为 5000
    :return: pd.DataFrame

    >>> start_date = datetime.strptime("20200701", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df1 = get_kline(symbol="000001.SH-I", start_date=start_date, end_date=end_date, freq="1min")
    >>> df2 = get_kline(symbol="000001.SH-I", end_date=end_date, freq="1min", count=1000)
    """
    ts_code, asset = symbol.split("-")
    if count:
        start_date = _get_start_date(end_date, freq)
        start_date = start_date.date().__str__().replace("-", "")

        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        end_date = end_date + timedelta(days=1)
        end_date = end_date.date().__str__().replace("-", "")

    if isinstance(end_date, datetime):
        end_date = end_date.date().__str__().replace("-", "")

    if isinstance(start_date, datetime):
        start_date = start_date.date().__str__().replace("-", "")

    df = ts.pro_bar(ts_code=ts_code, freq=freq, start_date=start_date, end_date=end_date,
                    adj='qfq', asset=asset)

    # 统一 k 线数据格式为 6 列，分别是 ["symbol", "dt", "open", "close", "high", "low", "vr"]
    if "min" in freq:
        df.rename(columns={'ts_code': "symbol", "trade_time": "dt"}, inplace=True)
    else:
        df.rename(columns={'ts_code': "symbol", "trade_date": "dt"}, inplace=True)

    df.drop_duplicates(subset='dt', keep='first', inplace=True)
    df.sort_values('dt', inplace=True)
    df['dt'] = df.dt.apply(str)
    if freq.endswith("min"):
        # 清理 9:30 的空数据
        df['not_start'] = df.dt.apply(lambda x: not x.endswith("09:30:00"))
        df = df[df['not_start']]
    if count:
        df = df.tail(count)

    df.reset_index(drop=True, inplace=True)
    df.loc[:, "dt"] = pd.to_datetime(df['dt'])

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k[col] = k[col].apply(round, args=(2,))

    return k


def download_kline(symbol, freq, start_date, end_date, delta, save=True):
    """下载K线数据

    :param save:
    :param symbol:
    :param end_date:
    :param freq:
    :param start_date:
    :param delta:
    :return:

    >>> start_date = datetime.strptime("20200101", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df = download_kline("000001.SH-I", "1min", start_date, end_date, delta=timedelta(days=10), save=False)
    """
    data = []
    end_dt = start_date + delta
    print("开始下载数据：{} - {} - {}".format(symbol, start_date, end_date))
    df_ = get_kline(symbol, start_date=start_date, end_date=end_dt, freq=freq)
    if not df_.empty:
        data.append(df_)

    while end_dt < end_date:
        df_ = get_kline(symbol, start_date=start_date, end_date=end_dt, freq=freq)
        if not df_.empty:
            data.append(df_)
        start_date = end_dt
        end_dt += delta
        print("当前下载进度：{} - {} - {}".format(symbol, start_date, end_dt))

    df = pd.concat(data, ignore_index=True)
    print("{} 去重前K线数量为 {}".format(symbol, len(df)))
    df.drop_duplicates(['dt'], inplace=True)
    df.sort_values('dt', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    print("{} 去重后K线数量为 {}".format(symbol, len(df)))

    if save:
        df.to_csv(f"{symbol}_{freq}_{start_date.date()}_{end_date.date()}.csv", index=False, encoding="utf-8")
    else:
        return df
