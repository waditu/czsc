# coding: utf-8
import os
import pickle
import json
import requests
import warnings
import pandas as pd
from datetime import datetime, timedelta

url = "https://dataapi.joinquant.com/apis"
home_path = os.path.expanduser("~")
file_token = os.path.join(home_path, "jq.token")

def set_token(jq_mob, jq_pwd):
    """

    :param jq_mob: str
        mob是申请JQData时所填写的手机号
    :param jq_pwd: str
        Password为聚宽官网登录密码，新申请用户默认为手机号后6位
    :return: None
    """
    with open(file_token, 'wb') as f:
        pickle.dump([jq_mob, jq_pwd], f)


def get_token():
    """获取调用凭证"""
    if not os.path.exists(file_token):
        raise ValueError(f"{file_token} 文件不存在，请先调用 set_token 进行设置")

    with open(file_token, 'rb') as f:
        jq_mob, jq_pwd = pickle.load(f)

    body = {
        "method": "get_current_token",
        "mob": jq_mob,  # mob是申请JQData时所填写的手机号
        "pwd": jq_pwd,  # Password为聚宽官网登录密码，新申请用户默认为手机号后6位
    }
    response = requests.post(url, data=json.dumps(body))
    token = response.text
    return token


def text2df(text):
    rows = [x.split(",") for x in text.strip().split('\n')]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def get_query_count() -> int:
    """获取查询剩余条数
    https://dataapi.joinquant.com/docs#get_query_count---%E8%8E%B7%E5%8F%96%E6%9F%A5%E8%AF%A2%E5%89%A9%E4%BD%99%E6%9D%A1%E6%95%B0

    :return: int
    """
    data = {
        "method": "get_query_count",
        "token": get_token(),
    }
    r = requests.post(url, data=json.dumps(data))
    return int(r.text)


def get_concepts():
    """获取概念列表

    https://dataapi.joinquant.com/docs#get_concepts---%E8%8E%B7%E5%8F%96%E6%A6%82%E5%BF%B5%E5%88%97%E8%A1%A8

    :return: df
    """
    data = {
        "method": "get_concepts",
        "token": get_token(),
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    return df

def get_concept_stocks(symbol, date=None):
    """获取概念成份股

    https://dataapi.joinquant.com/docs#get_concept_stocks---%E8%8E%B7%E5%8F%96%E6%A6%82%E5%BF%B5%E6%88%90%E4%BB%BD%E8%82%A1

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
    if not date:
        date = str(datetime.now().date())

    if isinstance(date, datetime):
        date = str(date.date())

    data = {
        "method": "get_concept_stocks",
        "token": get_token(),
        "code": symbol,
        "date": date
    }
    r = requests.post(url, data=json.dumps(data))
    return r.text.split('\n')

def get_index_stocks(symbol, date=None):
    """获取指数成份股

    https://dataapi.joinquant.com/docs#get_index_stocks---%E8%8E%B7%E5%8F%96%E6%8C%87%E6%95%B0%E6%88%90%E4%BB%BD%E8%82%A1

    :param symbol: str
        如 000300.XSHG
    :param date: str or datetime
        日期，如 2020-08-08
    :return: list

    examples:
    -------
    >>> symbols1 = get_index_stocks("000300.XSHG", date="2020-07-08")
    >>> symbols2 = get_index_stocks("000300.XSHG", date=datetime.now())
    """
    if not date:
        date = str(datetime.now().date())

    if isinstance(date, datetime):
        date = str(date.date())

    data = {
        "method": "get_index_stocks",
        "token": get_token(),
        "code": symbol,
        "date": date
    }
    r = requests.post(url, data=json.dumps(data))
    return r.text.split('\n')

def get_all_securities(code, date=None) -> pd.DataFrame:
    """
    https://dataapi.joinquant.com/docs#get_all_securities---%E8%8E%B7%E5%8F%96%E6%89%80%E6%9C%89%E6%A0%87%E7%9A%84%E4%BF%A1%E6%81%AF
    获取平台支持的所有股票、基金、指数、期货信息

    参数：

    code: 证券类型,可选: stock, fund, index, futures, etf, lof, fja, fjb, QDII_fund,
                        open_fund, bond_fund, stock_fund, money_market_fund, mixture_fund, options
    date: 日期，用于获取某日期还在上市的证券信息，date为空时表示获取所有日期的标的信息

    :return:
    """
    if not date:
        date = str(datetime.now().date())

    if isinstance(date, datetime):
        date = str(date.date())

    data = {
        "method": "get_all_securities",
        "token": get_token(),
        "code": code,
        "date": date
    }
    r = requests.post(url, data=json.dumps(data))
    return text2df(r.text)

def get_kline(symbol,  end_date, freq, start_date=None, count=None):
    """获取K线数据

    :param symbol: str
        聚宽标的代码
    :param start_date: datetime
        截止日期
    :param end_date: datetime
        截止日期
    :param freq: str
        K线级别，可选值 ['1min', '5min', '30min', '60min', 'D', 'W', 'M']
    :param count: int
        K线数量，最大值为 5000
    :return: pd.DataFrame

    >>> start_date = datetime.strptime("20200701", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df1 = get_kline(symbol="000001.XSHG", start_date=start_date, end_date=end_date, freq="1min")
    >>> df2 = get_kline(symbol="000001.XSHG", end_date=end_date, freq="1min", count=1000)
    >>> df3 = get_kline(symbol="000001.XSHG", start_date='20200701', end_date='20200719', freq="1min")
    >>> df4 = get_kline(symbol="000001.XSHG", end_date='20200719', freq="1min", count=1000)
    """
    if count and count > 5000:
        warnings.warn(f"count={count}, 超过5000的最大值限制，仅返回最后5000条记录")

    # 1m, 5m, 15m, 30m, 60m, 120m, 1d, 1w, 1M
    freq_convert = {"1min": "1m", "5min": '5m', '15min': '15m',
                    "30min": "30m", "60min": '60m', "D": "1d", "W": '1w', "M": "1M"}
    end_date = pd.to_datetime(end_date)
    if start_date:
        start_date = pd.to_datetime(start_date)
        data = {
            "method": "get_price_period",
            "token": get_token(),
            "code": symbol,
            "unit": freq_convert[freq],
            "date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            # "fq_ref_date": end_date
        }
    elif count:
        data = {
            "method": "get_price",
            "token": get_token(),
            "code": symbol,
            "count": count,
            "unit": freq_convert[freq],
            "end_date": end_date.strftime("%Y-%m-%d"),
            # "fq_ref_date": end_date
        }
    else:
        raise ValueError("start_date 和 count 不能同时为空")

    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    df['symbol'] = symbol
    df.rename({'date': 'dt', 'volume': 'vol'}, axis=1, inplace=True)
    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    for col in ['open', 'close', 'high', 'low', 'vol']:
        df.loc[:, col] = df[col].apply(lambda x: round(float(x), 2))
    df.loc[:, "dt"] = pd.to_datetime(df['dt'])
    return df

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
    >>> df = download_kline("000001.XSHG", "1min", start_date, end_date, delta=timedelta(days=10), save=False)
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

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

def get_fundamental(table: str, symbol: str, date: str, columns: str = "") -> dict:
    """
    https://dataapi.joinquant.com/docs#get_fundamentals---%E8%8E%B7%E5%8F%96%E5%9F%BA%E6%9C%AC%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE

    财务数据列表：
    https://www.joinquant.com/help/api/help?name=Stock#%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE%E5%88%97%E8%A1%A8

    :param table:
    :param symbol:
    :param date: str
        查询日期2019-03-04或者年度2018或者季度2018q1 2018q2 2018q3 2018q4
    :param columns:
    :return: df

    example:
    ============
    >>>> x1 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020-11-12")
    >>>> x2 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020")
    >>>> x3 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020q3")
    """
    data = {
        "method": "get_fundamentals",
        "token": get_token(),
        "table": table,
        "columns": columns,
        "code": symbol,
        "date": date,
        "count": 1
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    try:
        return df.iloc[0].to_dict()
    except:
        return {}




