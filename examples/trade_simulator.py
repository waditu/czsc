# coding:utf-8
"""
交易模拟器，用于研究单标的的买卖点变化过程

"""
import czsc
print(czsc.__version__)

import os
import time
import traceback
import pandas as pd
from copy import deepcopy
import tushare as ts
from datetime import datetime, timedelta
from czsc import SolidAnalyze, KlineAnalyze
from czsc import plot_kline


# 首次使用，需要在这里设置你的 tushare token，用于获取数据；在同一台机器上，tushare token 只需要设置一次
# 没有 token，到 https://tushare.pro/register?reg=7 注册获取
# ts.set_token("your tushare token")

freq_map = {"1min": "1分钟", '5min': "5分钟", "30min": "30分钟", "D": "日线"}


def is_trade_day(date):
    """判断date日期是不是交易日

    :param date: str or datetime.date, 如 20180315
    :return: Bool
    """
    FILE_CALENDAR = "calendar.csv"
    if os.path.exists(FILE_CALENDAR) and \
            time.time() - os.path.getmtime(FILE_CALENDAR) < 3600 * 24:
        trade_calendar = pd.read_csv(FILE_CALENDAR, encoding='utf-8', dtype={"cal_date": str})
    else:
        pro = ts.pro_api()
        trade_calendar = pro.trade_cal()  # tushare提供的交易日历
        trade_calendar.to_csv(FILE_CALENDAR, index=False, encoding='utf-8')

    trade_day = trade_calendar[trade_calendar["is_open"] == 1]
    trade_day_list = [str(x).replace("-", "") for x in list(trade_day['cal_date'])]
    if isinstance(date, datetime):
        date = str(date.date()).replace("-", "")
    if date.replace("-", "") in trade_day_list:
        return True
    else:
        return False


def _get_start_date(end_date, freq):
    end_date = datetime.strptime(end_date, '%Y%m%d')
    if freq == '1min':
        start_date = end_date - timedelta(days=70)
    elif freq == '5min':
        start_date = end_date - timedelta(days=150)
    elif freq == '30min':
        start_date = end_date - timedelta(days=1000)
    elif freq == 'D':
        start_date = end_date - timedelta(weeks=1000)
    elif freq == 'W':
        start_date = end_date - timedelta(weeks=1000)
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date


def get_kline(ts_code, end_date, start_date=None, freq='30min', asset='E'):
    """获取指定级别的前复权K线

    :param ts_code: str
        股票代码，如 600122.SH
    :param freq: str
        K线级别，可选值 [1min, 5min, 15min, 30min, 60min, D, M, Y]
    :param end_date: str
        日期，如 20190610
    :param start_date:
    :param asset: str
        交易资产类型，可选值 E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
    :return: pd.DataFrame
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    """
    if not start_date:
        start_date = _get_start_date(end_date, freq)
        start_date = start_date.date().__str__().replace("-", "")

    if freq.endswith('min'):
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
    if freq == 'D':
        df['dt'] = df['dt'].apply(lambda x: datetime.strptime(x, "%Y%m%d").strftime("%Y-%m-%d %H:%M:%S"))

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k.loc[:, col] = k[col].apply(round, args=(2,))
    return k


def get_klines(ts_code, end_date, freqs='1min,5min,30min,D', asset='E'):
    """获取不同级别K线"""
    klines = dict()
    freqs = freqs.split(",")
    for freq in freqs:
        df = get_kline(ts_code, end_date, freq=freq, asset=asset)
        klines[freq_map[freq]] = df
    return klines


def make_klines(k1):
    """从1分钟K线构造多级别K线

    :param k1: pd.DataFrame
        1分钟K线，输入的1分钟K线必须是交易日当天的全部1分钟K线，如果是实时行情，则是截止到交易时间的全部K线
    :return:
    """
    first_dt = k1.iloc[0]['dt']
    kd = pd.DataFrame([{
        'symbol': k1.iloc[0]['symbol'],
        'dt': first_dt.split(" ")[0] + " 00:00:00",
        'open': k1.iloc[0]['open'],
        'close': k1.iloc[-1]['close'],
        'high': max(k1.high),
        'low': min(k1.low),
        'vol': round(sum(k1.vol) / 100, 2)
    }])

    if first_dt.endswith("09:30:00"):
        k1 = k1.iloc[1:]

    cols = ['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']

    def _minute_kline(freq):
        p = {'5min': 5, '15min': 15, '30min': 30, '60min': 60}
        d = p[freq]
        k2 = []
        i = 0
        while i * d < len(k1):
            df = k1.iloc[i * d: (i + 1) * d]
            symbol = df.iloc[0]['symbol']
            dt = df.iloc[-1]['dt']
            open_ = df.iloc[0]['open']
            close_ = df.iloc[-1]['close']
            high_ = max(df.high)
            low_ = min(df.low)
            vol_ = sum(df.vol)

            k = {"symbol": symbol, "dt": dt, "open": open_, "close": close_,
                 "high": high_, "low": low_, "vol": vol_}
            k2.append(k)
            i += 1
        k2 = pd.DataFrame(k2)
        if len(k2) > 1:
            last_dt = datetime.strptime(k2.iloc[-2]['dt'], "%Y-%m-%d %H:%M:%S") \
                      + timedelta(minutes=d)
        else:
            last_dt = datetime.strptime(k1.iloc[0]['dt'], "%Y-%m-%d %H:%M:%S") \
                      + timedelta(minutes=d-1)
        k2.loc[len(k2)-1, "dt"] = last_dt.strftime("%Y-%m-%d %H:%M:%S")
        return k2[cols]

    klines = {"1分钟": k1, '5分钟': _minute_kline('5min'), '30分钟': _minute_kline('30min'), "日线": kd[cols]}
    return klines


def kline_simulator(ts_code, trade_dt, asset="E", count=5000):
    """K线模拟器（精确到分钟），每次模拟一天

    >>> ks = kline_simulator(ts_code="300803.SZ", trade_dt='20200310')
    >>> for k in ks.__iter__():
    >>>    print(k['5分钟'].tail(2))

    """
    if "-" in trade_dt:
        dt1 = datetime.strptime(trade_dt, '%Y-%m-%d')
    else:
        dt1 = datetime.strptime(trade_dt, '%Y%m%d')

    last_date = dt1 - timedelta(days=1)
    init_klines = get_klines(ts_code, last_date.strftime("%Y%m%d"), freqs='1min,5min,30min,D', asset=asset)

    k1 = get_kline(ts_code, end_date=dt1.strftime("%Y%m%d"), start_date=dt1.strftime("%Y%m%d"), freq='1min', asset=asset)
    if k1.iloc[0]['dt'].endswith("09:30:00"):
        k1 = k1.iloc[1:]

    for i in range(1, len(k1)+1):
        k1_ = deepcopy(k1.iloc[:i])
        klines = make_klines(k1_)
        # 合并成新K线
        new_klines = dict()
        for freq in init_klines.keys():
            new_klines[freq] = pd.concat([init_klines[freq], klines[freq]]).tail(count)
            # print(freq, new_klines[freq].tail(2), '\n')
        yield new_klines


def trade_simulator(ts_code, end_date, file_bs, start_date=None, days=3, asset="E", watch_interval=5):
    """单只标的类实盘模拟，研究买卖点变化过程

    :param file_bs:
    :param ts_code: str
        标的代码，如 300033.SZ
    :param end_date: str
        截止日期，如 20200312
    :param start_date: str
        开始日期
    :param days: int
        从截止日线向前推的天数
    :param asset: str
        tushare 中的资产类型编码
    :param watch_interval: int
        看盘间隔，单位：分钟；默认值为 5分钟看盘一次
    :return: None
    """
    end_date = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
    if not start_date:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
    results = []

    while start_date <= end_date:
        if (asset in ["E", "I"]) and (not is_trade_day(start_date.strftime('%Y%m%d'))):
            start_date += timedelta(days=1)
            continue

        ks = kline_simulator(ts_code, trade_dt=start_date.strftime('%Y%m%d'), asset=asset)
        for i, klines in enumerate(ks.__iter__(), 1):
            if i % watch_interval != 0:
                continue

            sa = SolidAnalyze(klines)
            for freq in ['1分钟', '5分钟', '30分钟']:
                for name in sa.bs_func.keys():
                    try:
                        detail = sa.check_bs(freq=freq, name=name, pf=False, tolerance=0.1)
                        if detail['操作提示'] == name:
                            print(detail)
                            detail['交易时间'] = detail['最新时间']
                            detail['交易价格'] = detail['最新价格']
                            results.append(detail)
                    except:
                        traceback.print_exc()
                        continue

        df = pd.DataFrame(results)
        df.sort_values('交易时间', inplace=True)
        df = df.drop_duplicates(['出现时间', '基准价格', '操作提示', '标的代码'])
        cols = ['标的代码', '操作提示', '交易时间', '交易价格', '交易级别', '出现时间', '基准价格', '其他信息']
        df = df[cols]
        df.to_excel(file_bs, index=False)
        start_date += timedelta(days=1)


def check_trade(ts_code, file_bs, freq, end_date="20200314", asset="E", file_html="bs.html"):
    """在图上画出买卖点"""
    bs = pd.read_excel(file_bs)
    bs.loc[:, 'f'] = bs.apply(lambda x: 1 if x['交易级别'] == freq_map[freq] else 0, axis=1)
    bs = bs[bs.f == 1]
    bs.loc[:, '操作提示'] = bs['操作提示'].apply(lambda x: x.replace(freq_map[freq], ""))
    bs = bs[["操作提示", "交易时间", "交易价格"]]
    print(bs)
    df = get_kline(ts_code, freq=freq, end_date=end_date, asset=asset)
    ka = KlineAnalyze(df)
    plot_kline(ka, bs, file_html, width="1400px", height="680px")


if __name__ == '__main__':
    ts_code = '300033.SZ'
    asset = "E"
    end_date = '20200321'
    freq = '30min'
    file_bs = "%s买卖点变化过程_%s.xlsx" % (ts_code, end_date)
    file_html = f"%s_%s_%s_bs.html" % (ts_code, freq, end_date)

    # step 1. 仿真交易
    # trade_simulator(ts_code, end_date=end_date, file_bs=file_bs, days=100, asset=asset, watch_interval=5)

    # step 2. 查看仿真交易过程的买卖点提示
    check_trade(ts_code, file_bs, freq=freq, asset=asset, end_date=end_date, file_html=file_html)
