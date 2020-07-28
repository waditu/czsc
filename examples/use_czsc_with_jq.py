# coding: utf-8
import json
import requests
import pandas as pd
from datetime import datetime
from czsc import KlineAnalyze


# 聚宽数据 API
url = "https://dataapi.joinquant.com/apis"
mob = "******"  # mob是申请JQData时所填写的手机号
pwd = "******"  # Password为聚宽官网登录密码，新申请用户默认为手机号后6位


def get_token():
    """获取调用凭证"""
    body = {
        "method": "get_current_token",
        "mob": mob,  # mob是申请JQData时所填写的手机号
        "pwd": pwd,  # Password为聚宽官网登录密码，新申请用户默认为手机号后6位
    }
    response = requests.post(url, data=json.dumps(body))
    token = response.text
    return token


def text2df(text):
    rows = [x.split(",") for x in text.strip().split('\n')]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def get_kline(symbol, end_date, freq, count=3000):
    # 1m, 5m, 15m, 30m, 60m, 120m, 1d, 1w, 1M
    freq_convert = {"1min": "1m", "5min": '5m', '15min': '15m',
                    "30min": "30m", "60min": '60m', "D": "1d", "W": '1w'}
    if "-" not in end_date:
        end_date = datetime.strptime(end_date, "%Y%m%d").strftime("%Y-%m-%d")

    data = {
        "method": "get_price",
        "token": get_token(),
        "code": symbol,
        "count": count,
        "unit": freq_convert[freq],
        "end_date": end_date,
        "fq_ref_date": "2010-01-01"
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    df['symbol'] = symbol
    df.rename({'date': 'dt', 'volume': 'vol'}, axis=1, inplace=True)
    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    for col in ['open', 'close', 'high', 'low', 'vol']:
        df.loc[:, col] = df[col].apply(lambda x: round(float(x), 2))
    return df


def use_kline_analyze():
    kline = get_kline(symbol="000001.XSHG", end_date="20200616", freq="D", count=5000)

    # 输入K线即完成分析
    ka = KlineAnalyze(kline, name="日线", min_bi_k=5, max_raw_len=10000, verbose=False)

    # 查看结果
    print("分型识别结果：", ka.fx_list[-3:])
    print("笔识别结果：", ka.bi_list[-3:])
    print("线段识别结果：", ka.xd_list[-3:])

    # 用图片或者HTML可视化
    ka.to_image("test.png")
    ka.to_html("test.html")


if __name__ == '__main__':
    use_kline_analyze()

