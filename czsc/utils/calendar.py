# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/10 17:53
describe: A股+期货的交易日历
"""
import pandas as pd
from pathlib import Path
from datetime import datetime


calendar = pd.read_feather(Path(__file__).parent / "china_calendar.feather")


def prepare_chain_calendar():
    import tushare as ts
    pro = ts.pro_api()
    df = pro.trade_cal(exchange='', start_date='20100101', end_date='20301231')
    df['cal_date'] = pd.to_datetime(df['cal_date'])
    df = df.sort_values('cal_date').reset_index(drop=True)[['cal_date', 'is_open']]
    df.to_feather(Path(__file__).parent / "china_calendar.feather")


def is_trading_date(date=datetime.now()):
    """判断是否是交易日"""
    date = pd.to_datetime(pd.to_datetime(date).date())
    is_open = calendar[calendar['cal_date'] == date].iloc[0]['is_open']
    return is_open == 1


def next_trading_date(date=datetime.now(), n=1):
    """获取未来第N个交易日"""
    date = pd.to_datetime(pd.to_datetime(date).date())
    df = calendar[calendar['cal_date'] > date]
    return df[df['is_open'] == 1].iloc[n - 1]['cal_date']


def prev_trading_date(date=datetime.now(), n=1):
    """获取过去第N个交易日"""
    date = pd.to_datetime(pd.to_datetime(date).date())
    df = calendar[calendar['cal_date'] < date]
    return df[df['is_open'] == 1].iloc[-n]['cal_date']


def get_trading_dates(sdt, edt=datetime.now()):
    """获取两个日期之间的所有交易日"""
    sdt = pd.to_datetime(sdt).date()
    edt = pd.to_datetime(edt).date()
    sdt, edt = pd.to_datetime(sdt), pd.to_datetime(edt)
    df = calendar[(calendar['cal_date'] >= sdt) & (calendar['cal_date'] <= edt)]
    return df[df['is_open'] == 1]['cal_date'].tolist()
