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
    :return:
    """
    pickle.dump([jq_mob, jq_pwd], open(file_token, 'wb'))


def get_token():
    """获取调用凭证"""
    if not os.path.exists(file_token):
        raise ValueError(f"{file_token} 文件不存在，请先调用 set_token 进行设置")

    jq_mob, jq_pwd = pickle.load(open(file_token, 'rb'))
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


def get_kline(symbol,  end_date: datetime, freq: str, start_date: datetime = None, count=None):
    """获取K线数据

    :param symbol: str
        聚宽标的代码
    :param start_date: datetime
        截止日期
    :param end_date: datetime
        截止日期
    :param freq: str
        K线级别，可选值 ['1min', '5min', '30min', '60min', 'D', 'W']
    :param count: int
        K线数量，最大值为 5000
    :return: pd.DataFrame

    >>> start_date = datetime.strptime("20200701", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df1 = get_kline(symbol="000001.XSHG", start_date=start_date, end_date=end_date, freq="1min")
    >>> df2 = get_kline(symbol="000001.XSHG", end_date=end_date, freq="1min", count=1000)
    """
    if count and count > 5000:
        warnings.warn(f"count={count}, 超过5000的最大值限制，仅返回最后5000条记录")

    # 1m, 5m, 15m, 30m, 60m, 120m, 1d, 1w, 1M
    freq_convert = {"1min": "1m", "5min": '5m', '15min': '15m',
                    "30min": "30m", "60min": '60m', "D": "1d", "W": '1w'}
    if start_date:
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


def download_kline(symbol, freq: str, start_date: datetime, end_date: datetime, delta: timedelta, save=True):
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
