# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/10 17:53
describe: A股+期货的交易日历
"""
import pandas as pd
from pathlib import Path


def __prepare_cal():
    """使用tushare获取交易日历，保存到本地"""
    import pandas as pd
    import tushare as ts

    pro = ts.pro_api()
    exchanges = ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'CZCE', 'DCE', 'INE']
    res = []
    for exchange in exchanges:
        df = pro.trade_cal(exchange=exchange, start_date='20100101', end_date='20251231')
        res.append(df)
    df = pd.concat(res, ignore_index=True)
    df['is_open'] = df['is_open'].astype(int)
    dfc = pd.pivot_table(df, index='cal_date', columns='exchange', values='is_open').fillna(0).reset_index()
    dfc['cal_date'] = pd.to_datetime(dfc['cal_date'])
    dfc.to_feather('calendar.feather')

    # 验证：是不是所有交易所的交易日都一样
    dfc = dfc[dfc['cal_date'] >= '2021-01-01']
    dfc['sum'] = dfc[exchanges].sum(axis=1)
    assert dfc['sum'].value_counts()

    # 所有国内交易所的交易日历都是一样的
    df = pro.trade_cal(exchange="SSE", start_date='20100101', end_date='20251231')
    df['cal_date'] = pd.to_datetime(df['cal_date'])
    df.sort_values('cal_date', inplace=True, ascending=True)
    df = df.reset_index(drop=True)
    df[['cal_date', 'is_open']].to_feather('china_calendar.feather')


calendar = pd.read_feather(Path(__file__).parent / "china_calendar.feather")


def is_trading_date(date):
    """判断是否是交易日"""
    date = pd.to_datetime(date)
    is_open = calendar[calendar['cal_date'] == date].iloc[0]['is_open']
    return is_open == 1


def next_trading_date(date, n=1):
    """获取未来第N个交易日"""
    date = pd.to_datetime(date)
    df = calendar[calendar['cal_date'] >= date]
    return df[df['is_open'] == 1].iloc[n - 1]['cal_date']


def prev_trading_date(date, n=1):
    """获取过去第N个交易日"""
    date = pd.to_datetime(date)
    df = calendar[calendar['cal_date'] <= date]
    return df[df['is_open'] == 1].iloc[-n]['cal_date']
