# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/25 18:52
"""

import pandas as pd
import traceback
import tushare as ts
from datetime import datetime, timedelta
from typing import List
from ..analyze import CzscTrader, RawBar, KlineGenerator, get_default_signals
from ..enum import Freq


# 数据频度 ：支持分钟(min)/日(D)/周(W)/月(M)K线，其中1min表示1分钟（类推1/5/15/30/60分钟）。
# 对于分钟数据有600积分用户可以试用（请求2次），正式权限请在QQ群私信群主或积分管理员。
freq_map = {Freq.F1: "1min", Freq.F5: '5min', Freq.F15: "15min", Freq.F30: '30min',
            Freq.F60: "60min", Freq.D: 'D', Freq.W: "W", Freq.M: "M"}
freq_cn_map = {"1分钟": Freq.F1, "5分钟": Freq.F5, "15分钟": Freq.F15, "30分钟": Freq.F30,
               "60分钟": Freq.F60, "日线": Freq.D}


dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y%m%d"


def format_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """Tushare K线数据转换

    :param kline: Tushare 数据接口返回的K线数据
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    records = kline.to_dict('records')
    dt_key = 'trade_time' if '分钟' in freq.value else 'trade_date'
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
    return bars[::-1]


def get_init_kg(ts_code: str,
                end_dt: [str, datetime] = None,
                max_count: int = 3000,
                generator: [KlineGenerator] = KlineGenerator,
                freqs=('1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'),
                asset: str = 'E',
                fq='qfq'):
    """获取 ts_code 的初始化 kline generator"""
    if end_dt:
        end_dt = pd.to_datetime(end_dt)
    else:
        end_dt = datetime.now()

    last_day = (end_dt - timedelta(days=1)).replace(hour=16, minute=0)

    kg = generator(max_count=max_count, freqs=freqs)

    for freq in freqs:
        if freq == Freq.F1.value:
            start_dt = end_dt - timedelta(days=21)
        elif freq == Freq.F5.value:
            start_dt = end_dt - timedelta(days=21*5)
        elif freq == Freq.F15.value:
            start_dt = end_dt - timedelta(days=21*15)
        elif freq == Freq.F30.value:
            start_dt = end_dt - timedelta(days=500)
        elif freq == Freq.F60.value:
            start_dt = end_dt - timedelta(days=1000)
        elif freq == Freq.D.value:
            start_dt = end_dt - timedelta(days=1500)
        else:
            raise ValueError(freq.value)

        bars = get_kline(ts_code=ts_code, asset=asset, start_date=start_dt, end_date=last_day,
                         freq=freq_cn_map[freq], fq=fq)
        kg.init_kline(freq, bars)
        print(f"{ts_code} - {freq} - bars_len: {len(bars)} - kg_last_dt: "
              f"{kg.get_kline(freq, 1)[-1].dt} - last_day: {last_day}")

    bars = get_kline(ts_code=ts_code, asset=asset, start_date=last_day, end_date=end_dt, freq=Freq.F1, fq=fq)
    data = [x for x in bars if x.dt > last_day]

    if data:
        print(f"{ts_code}: 更新 kg 至 {end_dt.strftime(dt_fmt)}，共有{len(data)}行数据需要update")
        for row in data:
            kg.update(row)
    return kg

class TsCzscTrader(CzscTrader):
    def __init__(self, ts_code, end_dt=None, max_count=2000, asset='E',
                 freqs=('1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线')):
        self.ts_code = ts_code
        self.asset = asset
        kg = get_init_kg(ts_code, end_dt, asset=asset, max_count=max_count, freqs=freqs)
        super(TsCzscTrader, self).__init__(kg, get_signals=get_default_signals, events=[])


if __name__ == '__main__':
    # 这里可以换成自己的股票池
    ts_codes = ['603259.SH', '603288.SH', '603501.SH', '603986.SH']
    k1 = get_kline(ts_code='000001.SH', asset='I', start_date='20210601', end_date='20210630', freq=Freq.F1)
    kd = get_kline(ts_code='000001.SH', asset='I', start_date='20210601', end_date='20210630', freq=Freq.D)
