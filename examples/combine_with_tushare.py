# coding: utf-8
"""
结合 tushare.pro 的数据使用 czsc 进行缠论技术分析

author: zengbin93
email: zeng_bin8888@163.com
date: 2020-02-02
========================================================================================================================
"""

import tushare as ts
from datetime import datetime, timedelta
from czsc import KlineAnalyze

# 首次使用，需要在这里设置你的 tushare token，用于获取数据；在同一台机器上，tushare token 只需要设置一次
# 没有 token，到 https://tushare.pro/register?reg=7 注册获取
# ts.set_token("your tushare token")


def _get_start_date(end_date, freq):
    end_date = datetime.strptime(end_date, '%Y%m%d')
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
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date


def get_kline(ts_code, end_date, freq='30min', asset='E'):
    """获取指定级别的前复权K线

    :param ts_code: str
        股票代码，如 600122.SH
    :param freq: str
        K线级别，可选值 [1min, 5min, 15min, 30min, 60min, D, M, Y]
    :param end_date: str
        日期，如 20190610
    :param asset: str
        交易资产类型，可选值 E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
    :return: pd.DataFrame
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    """
    start_date = _get_start_date(end_date, freq)
    start_date = start_date.date().__str__().replace("-", "")
    end_date = datetime.strptime(end_date, '%Y%m%d')
    end_date = end_date + timedelta(days=1)
    end_date = end_date.date().__str__().replace("-", "")

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
    df.reset_index(drop=True, inplace=True)

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k[col] = k[col].apply(round, args=(2,))
    return k


def get_klines(ts_code, end_date, freqs='1min,5min,30min,D', asset='E'):
    """获取不同级别K线"""
    freq_map = {"1min": "1分钟", "5min": "5分钟", "30min": "30分钟", "D": "日线"}
    klines = dict()
    freqs = freqs.split(",")
    for freq in freqs:
        df = get_kline(ts_code, end_date, freq=freq, asset=asset)
        klines[freq_map[freq]] = df
    return klines


def use_kline_analyze():
    print('=' * 100, '\n')
    print("KlineAnalyze 的使用方法：\n")
    kline = get_kline(ts_code="000009.SZ", end_date="20200210", freq='30min', asset="I")
    ka = KlineAnalyze(kline, name="本级别", min_bi_k=5, max_raw_len=10000, verbose=False)
    print("分型：", ka.fx_list, "\n")
    print("线段：", ka.xd_list, "\n")


if __name__ == '__main__':
    use_kline_analyze()

