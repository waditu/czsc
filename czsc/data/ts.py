# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/25 18:52
"""
import os
import time
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from typing import List
from tqdm import tqdm

from ..analyze import RawBar
from ..enum import Freq
from ..utils.cache import home_path


# 数据频度 ：支持分钟(min)/日(D)/周(W)/月(M)K线，其中1min表示1分钟（类推1/5/15/30/60分钟）。
# 对于分钟数据有600积分用户可以试用（请求2次），正式权限请在QQ群私信群主或积分管理员。
freq_map = {Freq.F1: "1min", Freq.F5: '5min', Freq.F15: "15min", Freq.F30: '30min',
            Freq.F60: "60min", Freq.D: 'D', Freq.W: "W", Freq.M: "M"}
freq_cn_map = {"1分钟": Freq.F1, "5分钟": Freq.F5, "15分钟": Freq.F15, "30分钟": Freq.F30,
               "60分钟": Freq.F60, "日线": Freq.D}
exchanges = {
    "SSE": "上交所",
    "SZSE": "深交所",
    "CFFEX": "中金所",
    "SHFE": "上期所",
    "CZCE": "郑商所",
    "DCE": "大商所",
    "INE": "能源",
    "IB": "银行间",
    "XHKG": "港交所"
}

dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y%m%d"

try:
    pro = ts.pro_api()
except:
    print("Tushare Pro 初始化失败")

def get_trade_cal():
    file_cal = os.path.join(home_path, "trade_cal.csv")
    for k, v in exchanges.items():
        df = pro.trade_cal(exchange=k, start_date='19700101', end_date='20211231')


def format_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """Tushare K线数据转换

    :param kline: Tushare 数据接口返回的K线数据
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = 'trade_time' if '分钟' in freq.value else 'trade_date'
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict('records')

    for i, record in enumerate(records):
        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['ts_code'], dt=pd.to_datetime(record[dt_key]),
                     id=i, freq=freq, open=record['open'], close=record['close'],
                     high=record['high'], low=record['low'], vol=record['vol'])
        bars.append(bar)
    return bars


def get_kline(ts_code: str,
              start_date: [datetime, str],
              end_date: [datetime, str],
              asset: str = 'E',
              freq: Freq = Freq.F1,
              fq: str = "qfq") -> List[RawBar]:
    """
    通用行情接口: https://tushare.pro/document/2?doc_id=109

    :param ts_code:
    :param asset:
    :param freq:
    :param start_date:
    :param end_date:
    :param fq:
    :return:
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    if "分钟" in freq.value:
        start_date = start_date.strftime(dt_fmt)
        end_date = end_date.strftime(dt_fmt)
    else:
        start_date = start_date.strftime(date_fmt)
        end_date = end_date.strftime(date_fmt)

    df = ts.pro_bar(ts_code=ts_code, adj=fq, asset=asset, freq=freq_map[freq],
                    start_date=start_date, end_date=end_date)
    bars = format_kline(df, freq)
    if bars and bars[-1].dt < pd.to_datetime(end_date) and len(bars) == 8000:
        print(f"获取K线数量达到8000根，数据获取到 {bars[-1].dt}，目标 end_date 为 {end_date}")
    return bars


def get_ths_daily(ts_code='885760.TI',
                  start_date: [datetime, str] = '20100101',
                  end_date: [datetime, str] = '20210727') -> List[RawBar]:
    """获取同花顺概念板块日线行情

    :param ts_code: 同花顺概念板块代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return:
    """
    start_date = pd.to_datetime(start_date).strftime(date_fmt)
    end_date = pd.to_datetime(end_date).strftime(date_fmt)
    kline = pro.ths_daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                          fields='ts_code,trade_date,open,close,high,low,vol')
    kline = kline.sort_values('trade_date')
    rows = kline.to_dict('records')

    bars = []
    for i, row in enumerate(rows):
        bar = RawBar(symbol=row['ts_code'], freq=Freq.D, id=i,
                     dt=pd.to_datetime(row['trade_date']), open=row['open'],
                     close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
        bars.append(bar)
    return bars

def get_ths_members(exchange="A"):
    """获取同花顺概念板块成分股"""
    concepts = pro.ths_index(exchange=exchange)
    concepts = concepts.to_dict('records')

    res = []
    for concept in tqdm(concepts):
        df = pro.ths_member(ts_code=concept['ts_code'],
                               fields="ts_code,code,name,weight,in_date,out_date,is_new")
        df['概念名称'] = concept['name']
        df['概念代码'] = concept['ts_code']
        res.append(df)
        time.sleep(0.3)

    res_df = pd.concat(res, ignore_index=True)
    return res_df

